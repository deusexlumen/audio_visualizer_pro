"""
Real-Time Audio Visualizer - Live-Audio vom Mikrofon

Features:
- Live-Audio-Input vom Mikrofon
- Echtzeit-FFT für Frequenz-Analyse
- Streamlit-Integration für Live-Preview
"""

import numpy as np
import threading
import queue
import time
from dataclasses import dataclass
from typing import Callable, Optional, List, Dict, Any
from collections import deque

import streamlit as st

from .logger import get_logger
from .types import AudioFeatures
from .visuals.registry import VisualizerRegistry

logger = get_logger("audio_visualizer.realtime")

# Optionaler Import von sounddevice
try:
    import sounddevice as sd

    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    logger.warning("sounddevice nicht installiert - Real-Time Features deaktiviert")


@dataclass
class RealtimeConfig:
    """Konfiguration für Real-Time Audio."""

    sample_rate: int = 44100
    block_size: int = 1024
    channels: int = 1
    device: Optional[int] = None

    # Visualisierung
    fps: int = 30
    smoothing: float = 0.8  # Exponential smoothing

    # FFT
    fft_size: int = 2048
    freq_bands: int = 64  # Anzahl der Frequenz-Bänder für Visualisierung


class RealtimeAudioCapture:
    """
    Erfasst Audio in Echtzeit vom Mikrofon.

    Usage:
        capture = RealtimeAudioCapture()
        capture.start(callback)
        # ... später
        capture.stop()
    """

    def __init__(self, config: Optional[RealtimeConfig] = None):
        self.config = config or RealtimeConfig()
        self._running = False
        self._callback: Optional[Callable] = None
        self._stream = None
        self._thread: Optional[threading.Thread] = None
        self._audio_queue: queue.Queue = queue.Queue(maxsize=10)

        if not SOUNDDEVICE_AVAILABLE:
            raise RuntimeError(
                "sounddevice nicht installiert. Installiere: pip install sounddevice"
            )

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback für sounddevice."""
        if status:
            logger.warning(f"Audio Status: {status}")

        # Audio-Daten in Queue (non-blocking)
        try:
            self._audio_queue.put_nowait(indata.copy())
        except queue.Full:
            # Alte Daten verwerfen wenn Queue voll
            try:
                self._audio_queue.get_nowait()
                self._audio_queue.put_nowait(indata.copy())
            except queue.Empty:
                pass

        # Callback aufrufen
        if self._callback:
            self._callback(indata.copy())

    def start(self, callback: Optional[Callable] = None):
        """Startet die Audio-Erfassung."""
        if self._running:
            return

        self._callback = callback
        self._running = True

        try:
            self._stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                blocksize=self.config.block_size,
                channels=self.config.channels,
                device=self.config.device,
                callback=self._audio_callback,
            )
            self._stream.start()
            logger.info(f"Real-Time Audio gestartet: {self.config.sample_rate}Hz")

        except Exception as e:
            self._running = False
            logger.error(f"Audio Start fehlgeschlagen: {e}")
            raise

    def stop(self):
        """Stoppt die Audio-Erfassung."""
        self._running = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        logger.info("Real-Time Audio gestoppt")

    def get_audio_block(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """Holt einen Audio-Block aus der Queue."""
        try:
            return self._audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def is_running(self) -> bool:
        """Prüft ob die Erfassung läuft."""
        return self._running and self._stream is not None

    @staticmethod
    def list_devices() -> List[Dict]:
        """Listet verfügbare Audio-Devices auf."""
        if not SOUNDDEVICE_AVAILABLE:
            return []

        devices = []
        for i, device in enumerate(sd.query_devices()):
            if device["max_input_channels"] > 0:
                devices.append(
                    {
                        "index": i,
                        "name": device["name"],
                        "channels": device["max_input_channels"],
                        "sample_rate": device["default_samplerate"],
                    }
                )
        return devices


class RealtimeFeatureExtractor:
    """
    Extrahiert Audio-Features in Echtzeit für Visualisierung.

    Features:
    - RMS (Lautstärke)
    - FFT (Frequenz-Spektrum)
    - Spectral Centroid
    - Beat-Detection (einfach)
    """

    def __init__(self, config: Optional[RealtimeConfig] = None):
        self.config = config or RealtimeConfig()

        # History für Smoothing
        self._rms_history = deque(maxlen=10)
        self._spectrum_history = deque(maxlen=5)

        # FFT Setup
        self._fft_window = np.hanning(self.config.fft_size)

        # Beat Detection
        self._beat_threshold = 0.5
        self._last_beat_time = 0
        self._beat_cooldown = 0.2  # Sekunden

        # Onset Detection
        self._onset_envelope = 0

    def process(self, audio_block: np.ndarray) -> Dict[str, Any]:
        """
        Verarbeitet einen Audio-Block und extrahiert Features.

        Returns:
            Dict mit: rms, spectrum, centroid, onset, beat
        """
        # Flatten falls stereo
        if audio_block.ndim > 1:
            audio = audio_block.mean(axis=1)
        else:
            audio = audio_block.flatten()

        # RMS (Lautstärke)
        rms = np.sqrt(np.mean(audio**2))
        self._rms_history.append(rms)
        rms_smooth = np.mean(self._rms_history) if self._rms_history else rms

        # Zero-padding für FFT falls nötig
        if len(audio) < self.config.fft_size:
            audio_padded = np.zeros(self.config.fft_size)
            audio_padded[: len(audio)] = audio
        else:
            audio_padded = audio[: self.config.fft_size]

        # FFT
        windowed = audio_padded * self._fft_window[: len(audio_padded)]
        fft = np.fft.rfft(windowed, n=self.config.fft_size)
        magnitude = np.abs(fft)

        # Frequenz-Bänder (logarithmisch)
        freqs = np.fft.rfftfreq(self.config.fft_size, 1 / self.config.sample_rate)
        bands = self._compute_freq_bands(magnitude, freqs)

        # Spectral Centroid
        centroid = self._compute_centroid(magnitude, freqs)

        # Onset Detection (einfache Spectral Flux)
        spectrum_norm = magnitude / (np.max(magnitude) + 1e-8)
        self._spectrum_history.append(spectrum_norm)

        onset = 0.0
        if len(self._spectrum_history) >= 2:
            diff = spectrum_norm - self._spectrum_history[-2]
            onset = np.maximum(diff, 0).sum()

            # Exponential smoothing
            self._onset_envelope = (0.8 * self._onset_envelope) + (0.2 * onset)
            onset = self._onset_envelope

        # Beat Detection
        beat = self._detect_beat(rms_smooth, onset)

        return {
            "rms": float(np.clip(rms_smooth * 5, 0, 1)),  # Normalisiert 0-1
            "spectrum": bands,
            "centroid": float(centroid / (self.config.sample_rate / 2)),  # Normalisiert
            "onset": float(np.clip(onset, 0, 1)),
            "beat": beat,
            "raw_audio": audio_padded,
        }

    def _compute_freq_bands(
        self, magnitude: np.ndarray, freqs: np.ndarray
    ) -> np.ndarray:
        """Berechnet logarithmische Frequenz-Bänder."""
        # Logarithmische Band-Grenzen (20Hz - Nyquist)
        f_min = 20
        f_max = self.config.sample_rate / 2

        band_edges = np.logspace(
            np.log10(f_min), np.log10(f_max), self.config.freq_bands + 1
        )

        bands = np.zeros(self.config.freq_bands)

        for i in range(self.config.freq_bands):
            mask = (freqs >= band_edges[i]) & (freqs < band_edges[i + 1])
            if mask.any():
                bands[i] = np.mean(magnitude[mask])

        # Normalisieren
        max_val = np.max(bands)
        if max_val > 0:
            bands = bands / max_val

        return bands

    def _compute_centroid(self, magnitude: np.ndarray, freqs: np.ndarray) -> float:
        """Berechnet Spectral Centroid."""
        if magnitude.sum() == 0:
            return 0
        return np.sum(freqs * magnitude) / np.sum(magnitude)

    def _detect_beat(self, rms: float, onset: float) -> bool:
        """Einfache Beat-Detection."""
        current_time = time.time()

        # Kombiniere RMS und Onset
        energy = 0.6 * rms + 0.4 * onset

        # Threshold-basiert mit Cooldown
        if (
            energy > self._beat_threshold
            and current_time - self._last_beat_time > self._beat_cooldown
        ):
            self._last_beat_time = current_time
            return True

        return False


class RealtimeVisualizer:
    """
    Kombiniert Audio-Capture und Feature-Extraktion für Live-Visualisierung.

    Usage:
        rt_viz = RealtimeVisualizer(visualizer_type="spectrum_bars")
        rt_viz.start()

        while running:
            frame = rt_viz.get_frame()
            display(frame)

        rt_viz.stop()
    """

    def __init__(
        self,
        visualizer_type: str = "spectrum_bars",
        config: Optional[RealtimeConfig] = None,
    ):
        self.config = config or RealtimeConfig()
        self.visualizer_type = visualizer_type

        self._capture: Optional[RealtimeAudioCapture] = None
        self._extractor = RealtimeFeatureExtractor(self.config)
        self._visualizer = None

        # Frame-Rate Limiting
        self._last_frame_time = 0
        self._frame_interval = 1.0 / self.config.fps

        # Latest Features
        self._latest_features: Optional[Dict] = None
        self._features_lock = threading.Lock()

        # Dummy Features für Visualizer
        self._dummy_audio_features = self._create_dummy_features()

    def _create_dummy_features(self) -> AudioFeatures:
        """Erstellt Dummy AudioFeatures für den Visualizer."""
        return AudioFeatures(
            duration=1.0,
            sample_rate=self.config.sample_rate,
            fps=self.config.fps,
            rms=np.zeros(self.config.fps),
            onset=np.zeros(self.config.fps),
            spectral_centroid=np.zeros(self.config.fps),
            spectral_rolloff=np.zeros(self.config.fps),
            zero_crossing_rate=np.zeros(self.config.fps),
            chroma=np.zeros((12, self.config.fps)),
            mfcc=np.zeros((13, self.config.fps)),
            tempogram=np.zeros((384, self.config.fps)),
            tempo=120.0,
            key="C major",
            mode="music",
        )

    def _on_audio(self, audio_block: np.ndarray):
        """Callback für neue Audio-Daten."""
        features = self._extractor.process(audio_block)

        with self._features_lock:
            self._latest_features = features

    def start(self):
        """Startet den Real-Time Visualizer."""
        # Initialisiere Visualizer
        viz_class = VisualizerRegistry.get(self.visualizer_type)

        from .types import VisualConfig

        viz_config = VisualConfig(
            type=self.visualizer_type, resolution=(640, 480), fps=self.config.fps
        )

        self._visualizer = viz_class(viz_config, self._dummy_audio_features)
        self._visualizer.setup()

        # Starte Audio-Capture
        self._capture = RealtimeAudioCapture(self.config)
        self._capture.start(self._on_audio)

        logger.info(f"Real-Time Visualizer gestartet: {self.visualizer_type}")

    def stop(self):
        """Stoppt den Real-Time Visualizer."""
        if self._capture:
            self._capture.stop()
            self._capture = None

        logger.info("Real-Time Visualizer gestoppt")

    def is_running(self) -> bool:
        """Prüft ob der Visualizer läuft."""
        return self._capture is not None and self._capture.is_running()

    def get_features(self) -> Optional[Dict]:
        """Holt die aktuellen Audio-Features (thread-safe)."""
        with self._features_lock:
            return self._latest_features.copy() if self._latest_features else None

    def get_frame(self) -> Optional[np.ndarray]:
        """
        Rendert einen Frame basierend auf aktuellen Audio-Daten.

        Returns:
            RGB Frame als numpy array
        """
        # Frame-Rate Limiting
        current_time = time.time()
        if current_time - self._last_frame_time < self._frame_interval:
            return None
        self._last_frame_time = current_time

        # Hole aktuelle Features
        features = self.get_features()
        if not features:
            return None

        # Update Visualizer mit aktuellen Features
        # Wir müssen die Features in das Format konvertieren, das der Visualizer erwartet
        self._update_visualizer_features(features)

        # Rendere Frame
        try:
            frame = self._visualizer.render_frame(0)  # Frame-Index egal bei Real-Time
            return frame
        except Exception as e:
            logger.error(f"Frame-Rendering fehlgeschlagen: {e}")
            return None

    def _update_visualizer_features(self, features: Dict):
        """Updated die Features des Visualizers."""
        # Erstelle temporäre Arrays für den Visualizer
        fps = self.config.fps

        # Aktualisiere RMS (Lautstärke)
        rms_array = np.ones(fps) * features["rms"]
        self._visualizer.features.rms = rms_array

        # Aktualisiere Onset (Beats)
        onset_array = np.zeros(fps)
        if features["beat"]:
            onset_array[0] = 1.0  # Trigger beat
        self._visualizer.features.onset = onset_array

        # Aktualisiere Spectral Centroid
        centroid_array = np.ones(fps) * features["centroid"]
        self._visualizer.features.spectral_centroid = centroid_array

        # Für Spectrum Bars Visualizer: direkte Spectrum-Daten
        if hasattr(self._visualizer, "_last_spectrum"):
            self._visualizer._last_spectrum = features["spectrum"]


# Streamlit UI für Real-Time
def render_realtime_page():
    """Streamlit-Seite für Real-Time Visualisierung."""
    st.markdown(
        """
    <div style="text-align: center; padding: 20px 0;">
        <h2 class="gradient-text">🎤 Real-Time Visualizer</h2>
        <p style="color: rgba(255,255,255,0.6);">Visualisiere dein Mikrofon in Echtzeit</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    if not SOUNDDEVICE_AVAILABLE:
        st.error("""
        ❌ sounddevice nicht installiert.
        
        Installiere mit:
        ```
        pip install sounddevice
        ```
        """)
        return

    # Initialisiere Session State
    if "realtime_viz" not in st.session_state:
        st.session_state.realtime_viz = None
    if "realtime_running" not in st.session_state:
        st.session_state.realtime_running = False

    # Einstellungen
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🎨 Visualizer")
        registry = VisualizerRegistry()
        registry.autoload()

        viz_options = registry.list_available()
        selected_viz = st.selectbox(
            "Visualizer wählen",
            options=viz_options,
            index=(
                viz_options.index("spectrum_bars")
                if "spectrum_bars" in viz_options
                else 0
            ),
        )

    with col2:
        st.markdown("### 🎤 Audio-Einstellungen")

        # Liste Audio-Devices
        devices = RealtimeAudioCapture.list_devices()
        if devices:
            device_names = [f"{d['name']} ({d['channels']}ch)" for d in devices]
            selected_device = st.selectbox("Mikrofon", options=device_names)
            device_idx = device_names.index(selected_device)
        else:
            st.warning("Keine Audio-Devices gefunden")
            device_idx = None

    # Start/Stop
    col1, col2 = st.columns(2)

    with col1:
        if not st.session_state.realtime_running:
            if st.button("▶️ Start", type="primary", use_container_width=True):
                try:
                    config = RealtimeConfig(device=device_idx)
                    rt_viz = RealtimeVisualizer(selected_viz, config)
                    rt_viz.start()

                    st.session_state.realtime_viz = rt_viz
                    st.session_state.realtime_running = True
                    st.rerun()

                except Exception as e:
                    st.error(f"Start fehlgeschlagen: {e}")

    with col2:
        if st.session_state.realtime_running:
            if st.button("⏹️ Stop", type="secondary", use_container_width=True):
                if st.session_state.realtime_viz:
                    st.session_state.realtime_viz.stop()
                st.session_state.realtime_running = False
                st.rerun()

    # Visualisierung
    if st.session_state.realtime_running and st.session_state.realtime_viz:
        st.markdown("### 📊 Live-Visualisierung")

        # Placeholder für Live-Frame
        frame_placeholder = st.empty()

        # Audio-Info
        features_placeholder = st.empty()

        # Stop-Button
        if st.button("⏹️ Stop Streaming"):
            st.session_state.realtime_viz.stop()
            st.session_state.realtime_running = False
            st.rerun()

        # Live-Loop (Streamlit-Version)
        # Hinweis: In echter Anwendung würde man st.experimental_rerun() nutzen
        # oder eine andere Strategie für kontinuierliches Rendering
        import time

        start_time = time.time()
        while st.session_state.realtime_running and time.time() - start_time < 30:
            rt_viz = st.session_state.realtime_viz

            # Hole Frame
            frame = rt_viz.get_frame()
            if frame is not None:
                frame_placeholder.image(frame, use_container_width=True)

            # Zeige Features
            features = rt_viz.get_features()
            if features:
                with features_placeholder.container():
                    cols = st.columns(4)
                    cols[0].metric("RMS", f"{features['rms']:.2f}")
                    cols[1].metric("Onset", f"{features['onset']:.2f}")
                    cols[2].metric("Centroid", f"{features['centroid']:.2f}")
                    cols[3].metric("Beat", "🔴" if features["beat"] else "⚫")

            time.sleep(0.033)  # ~30 FPS
    else:
        st.info("Drücke **Start** um die Live-Visualisierung zu beginnen")
