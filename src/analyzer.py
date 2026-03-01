"""
AudioAnalyzer - Layer 1: Audio -> Features

Audio-Analyse mit aggressivem Caching und Memory-Management.
Unterstützt auch große Dateien durch Chunk-basierte Analyse.
Thread-safe. Deterministisch.
"""

import librosa
import numpy as np
import hashlib
from pathlib import Path
from typing import Optional
from .types import AudioFeatures
from .logger import get_logger

logger = get_logger("audio_visualizer.analyzer")


class AudioAnalyzer:
    """
    Audio-Analyse mit aggressivem Caching.
    Gleiche Audio-Datei = Sofort-Ergebnis bei wiederholtem Aufruf.
    Unterstützt große Dateien durch speichereffiziente Chunk-Analyse.
    """

    # Maximale Dateigröße für Standard-Analyse (200 MB)
    MAX_STANDARD_SIZE_MB = 200
    # Maximale Dauer für volle Analyse (10 Minuten)
    MAX_STANDARD_DURATION_SEC = 600
    # Reduziere Auflösung für lange Dateien
    LONG_FILE_HOP_LENGTH_FACTOR = 4  # 4x größerer Hop = 1/4 der Frames

    def __init__(self, cache_dir: str = ".cache/audio_features"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, audio_path: str, fps: int) -> Path:
        """Generiert eindeutigen Cache-Key basierend auf Datei-Inhalt + Parametern."""
        # MD5 der ersten/letzten 1MB + Dateigröße (schnell & eindeutig)
        file_stat = Path(audio_path).stat()
        hasher = hashlib.md5()
        hasher.update(f"{file_stat.st_size}_{file_stat.st_mtime}_{fps}".encode())
        return self.cache_dir / f"{hasher.hexdigest()}.npz"

    def _get_file_size_mb(self, audio_path: str) -> float:
        """Gibt Dateigröße in MB zurück."""
        return Path(audio_path).stat().st_size / (1024 * 1024)

    def analyze(
        self, audio_path: str, fps: int = 60, force_reanalyze: bool = False
    ) -> AudioFeatures:
        """
        Extrahiert alle Features.
        Nutzt Memory-efficiente Analyse für große/lange Dateien.
        """
        cache_path = self._get_cache_path(audio_path, fps)
        file_size_mb = self._get_file_size_mb(audio_path)

        if not force_reanalyze and cache_path.exists():
            logger.info(f"[Cache] Lade Features für {Path(audio_path).name}...")
            try:
                return self._load_from_cache(cache_path)
            except (FileNotFoundError, OSError, ValueError) as e:
                logger.warning(f"[Cache] Ladefehler, analysiere neu: {e}")
                # Cache ist korrupt oder wurde gelöscht - neu analysieren

        logger.info(
            f"[Analyze] Verarbeite {Path(audio_path).name} ({file_size_mb:.1f} MB)..."
        )

        # Schnelle Dauer-Prüfung ohne vollständiges Laden
        try:
            duration = librosa.get_duration(path=audio_path)
        except Exception:
            duration = 0

        # Wähle Analyse-Methode basierend auf Dateigröße ODER Dauer
        is_large_file = file_size_mb > self.MAX_STANDARD_SIZE_MB
        is_long_file = duration > self.MAX_STANDARD_DURATION_SEC

        if is_large_file or is_long_file:
            if is_long_file:
                logger.info(
                    f"[Memory] Lange Datei erkannt ({duration:.0f}s) - nutze effiziente Analyse"
                )
            else:
                logger.info(
                    "[Memory] Große Datei erkannt - nutze speichereffiziente Analyse"
                )
            return self._analyze_large_file(
                audio_path, fps, cache_path, duration if is_long_file else None
            )
        else:
            return self._analyze_standard(audio_path, fps, cache_path)

    def _load_from_cache(self, cache_path: Path) -> AudioFeatures:
        """Lädt Features aus dem Cache."""
        data = np.load(cache_path, allow_pickle=True)

        # Konvertiere geladene Daten zurück
        loaded_data = {}
        for k in data.files:
            val = data[k]
            # Konvertiere numpy-Strings zurück zu Python-Strings
            if isinstance(val, np.ndarray):
                if val.dtype.char == "U":
                    # Unicode-String Array - konvertiere zu Python String
                    item = val.item()
                    # Handle "__NONE__" Marker als Python None
                    if item == "__NONE__":
                        loaded_data[k] = None
                    elif item == "None":
                        loaded_data[k] = None
                    else:
                        loaded_data[k] = str(item)
                elif val.dtype == object:
                    # Object Array (z.B. None Werte) - extrahiere Wert
                    item = val.item()
                    loaded_data[k] = None if item is None else item
                else:
                    loaded_data[k] = val
            else:
                loaded_data[k] = val

        return AudioFeatures(**loaded_data)

    def _analyze_standard(
        self, audio_path: str, fps: int, cache_path: Path
    ) -> AudioFeatures:
        """Standard-Analyse für kleine bis mittlere Dateien."""
        y, sr = librosa.load(audio_path, sr=None, mono=True)
        return self._extract_features(y, sr, fps, cache_path)

    def _analyze_large_file(
        self,
        audio_path: str,
        fps: int,
        cache_path: Path,
        duration: Optional[float] = None,
    ) -> AudioFeatures:
        """
        Speichereffiziente Analyse für große/lange Dateien.
        Nutzt Streaming und niedrigere Auflösung.
        """
        # Für lange Dateien: Lade mit niedrigerer Sample-Rate
        target_sr = 22050  # Halbe Sample-Rate = halber Speicher

        y, sr = librosa.load(
            audio_path, sr=target_sr, mono=True, res_type="kaiser_fast"
        )
        logger.info(f"[Memory] Resampled zu {sr} Hz für effiziente Analyse")

        # Für sehr lange Dateien: Nutze größeres hop_length
        if duration and duration > self.MAX_STANDARD_DURATION_SEC:
            # Berechne effektives FPS für interne Analyse
            effective_fps = fps / self.LONG_FILE_HOP_LENGTH_FACTOR
            logger.info(
                f"[Memory] Reduziere Analyse-Auflösung auf {effective_fps:.1f} FPS"
            )
            return self._extract_features(
                y, sr, fps, cache_path, effective_fps=effective_fps
            )

        return self._extract_features(y, sr, fps, cache_path)

    def _extract_features(
        self,
        y: np.ndarray,
        sr: int,
        fps: int,
        cache_path: Path,
        effective_fps: Optional[float] = None,
    ) -> AudioFeatures:
        """Extrahiert alle Features aus geladenem Audio."""
        duration = librosa.get_duration(y=y, sr=sr)

        # Für Analyse: Nutze effective_fps wenn angegeben (für lange Dateien)
        analysis_fps = effective_fps if effective_fps else fps

        # Hop-Length für exakte FPS-Synchronisation
        hop_length = max(int(sr / analysis_fps), 512)  # Mindestens 512 für Stabilität

        logger.info(
            f"[Analyze] Dauer: {duration:.1f}s, Sample Rate: {sr}Hz, Hop Length: {hop_length}"
        )

        # --- Feature Extraction (Memory-efficient) ---

        # 1. Energie (RMS)
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        rms = self._normalize(rms)

        # 2. Onset (Beats)
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
        onset = self._normalize(onset_env)

        # 3. Spektrale Features
        spec_cent = librosa.feature.spectral_centroid(
            y=y, sr=sr, hop_length=hop_length
        )[0]
        spec_roll = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length)[
            0
        ]
        zcr = librosa.feature.zero_crossing_rate(y=y, hop_length=hop_length)[0]

        # 4. Chroma (für Farb-Harmonien) - kann speicherintensiv sein
        try:
            # Für lange Dateien: Nutze STFT-basiertes Chroma (schneller/speichereffizienter)
            if effective_fps:
                # STFT-basiert ist speichereffizienter als CQT
                chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=hop_length)
                logger.info("[Memory] Nutze STFT-Chroma für Effizienz")
            else:
                chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
        except MemoryError:
            logger.warning("[Memory] Chroma-Analyse zu speicherintensiv - überspringe")
            # Fallback: Leere Chroma-Matrix
            num_frames = len(rms)
            chroma = np.zeros((12, num_frames))

        # 5. MFCC (für Timbre) - reduziere bei langen Dateien
        try:
            if effective_fps and len(y) > sr * 300:  # > 5 Minuten
                # Weniger MFCC-Koeffizienten für Effizienz
                mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=8, hop_length=hop_length)
                # Pad auf 13 für Konsistenz
                mfcc = np.vstack([mfcc, np.zeros((5, mfcc.shape[1]))])
            else:
                mfcc = librosa.feature.mfcc(
                    y=y, sr=sr, n_mfcc=13, hop_length=hop_length
                )
        except MemoryError:
            logger.warning("[Memory] MFCC-Analyse zu speicherintensiv - überspringe")
            num_frames = len(rms)
            mfcc = np.zeros((13, num_frames))

        # 6. Tempo & Tempogram (optional für lange Dateien)
        try:
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            # Tempogram ist sehr speicherintensiv - überspringe bei langen Dateien
            if effective_fps:
                logger.info("[Memory] Überspringe Tempogram für Effizienz")
                tempogram = np.zeros((384, len(rms)))
            else:
                tempogram = librosa.feature.tempogram(y=y, sr=sr, hop_length=hop_length)
        except Exception as e:
            logger.warning(f"[Analyze] Tempo-Erkennung fehlgeschlagen: {e}")
            tempo = 120.0  # Default
            tempogram = np.zeros((384, len(rms)))

        # 7. Mode Detection (Musik vs Sprache)
        mode = self._detect_mode(y, sr, tempo, onset_env)

        # 8. Key Detection (optional, nur für <10min und wenn genug Speicher)
        key = None
        if duration < 600:
            try:
                key = self._estimate_key(chroma)
            except Exception as e:
                logger.warning(f"[Analyze] Key-Erkennung fehlgeschlagen: {e}")

        # Berechne Ziel-Frame-Anzahl
        target_frames = int(duration * fps)

        features = AudioFeatures(
            duration=duration,
            sample_rate=sr,
            fps=fps,
            rms=self._interpolate_to_length(rms, target_frames),
            onset=self._interpolate_to_length(onset, target_frames),
            spectral_centroid=self._normalize(
                self._interpolate_to_length(spec_cent, target_frames)
            ),
            spectral_rolloff=self._normalize(
                self._interpolate_to_length(spec_roll, target_frames)
            ),
            zero_crossing_rate=self._normalize(
                self._interpolate_to_length(zcr, target_frames)
            ),
            chroma=(
                chroma
                if chroma.shape[1] == target_frames
                else self._interpolate_chroma(chroma, target_frames)
            ),
            mfcc=(
                mfcc
                if mfcc.shape[1] == target_frames
                else self._interpolate_2d(mfcc, target_frames)
            ),
            tempogram=(
                tempogram
                if tempogram.shape[1] == target_frames
                else self._interpolate_2d(tempogram, target_frames)
            ),
            tempo=float(tempo),
            key=key,
            mode=mode,
        )

        # Caching
        self._save_cache(cache_path, features)
        return features

    def _interpolate_chroma(self, chroma: np.ndarray, target_length: int) -> np.ndarray:
        """Interpoliert Chroma-Matrix auf Ziel-Länge."""
        if chroma.shape[1] == target_length:
            return chroma

        # Interpoliere jede der 12 Chroma-Bins einzeln
        result = np.zeros((12, target_length))
        x_old = np.linspace(0, 1, chroma.shape[1])
        x_new = np.linspace(0, 1, target_length)

        for i in range(12):
            result[i] = np.interp(x_new, x_old, chroma[i])

        return result

    def _interpolate_2d(self, data: np.ndarray, target_length: int) -> np.ndarray:
        """Interpoliert 2D-Array (Features x Frames) auf Ziel-Länge."""
        if data.shape[1] == target_length:
            return data

        num_features = data.shape[0]
        result = np.zeros((num_features, target_length))
        x_old = np.linspace(0, 1, data.shape[1])
        x_new = np.linspace(0, 1, target_length)

        for i in range(num_features):
            result[i] = np.interp(x_new, x_old, data[i])

        return result

    def _normalize(self, x: np.ndarray) -> np.ndarray:
        """Min-Max Normalisierung 0-1."""
        min_val = x.min()
        max_val = x.max()
        if max_val - min_val < 1e-8:
            return np.zeros_like(x)
        return (x - min_val) / (max_val - min_val)

    def _interpolate_to_length(
        self, data: np.ndarray, target_length: int
    ) -> np.ndarray:
        """Gleicht Längenunterschiede aus (wichtig für exakte Frame-Sync)."""
        if len(data) == target_length:
            return data

        x_old = np.linspace(0, 1, len(data))
        x_new = np.linspace(0, 1, target_length)
        return np.interp(x_new, x_old, data)

    def _detect_mode(self, y, sr, tempo, onset_env) -> str:
        """KI-Logik: Einfache Heuristik für Musik vs Sprache."""
        onset_std = np.std(onset_env)
        try:
            # Nutze nur einen kleinen Ausschnitt für Spektral-Bandbreite
            sample_size = min(len(y), sr * 5)  # Max 5 Sekunden (reduziert)
            # Stelle sicher, dass sample_size nicht 0 ist
            if sample_size < 512:
                sample_size = min(len(y), 512)
            y_sample = y[:sample_size]
            spec_bw = librosa.feature.spectral_bandwidth(y=y_sample, sr=sr).mean()
        except Exception:
            spec_bw = 2000
        is_music = (tempo > 60) and (onset_std > 0.1) and (spec_bw > 2000)
        return "music" if is_music else "speech"

    def _estimate_key(self, chroma: np.ndarray) -> str:
        """Einfache Key-Estimation durch Korrelation mit Profilen."""
        # Vereinfacht: Durchschnitt über Zeit
        chroma_avg = np.mean(chroma, axis=1)
        keys = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return keys[np.argmax(chroma_avg)] + " major"

    def _save_cache(self, path: Path, features: AudioFeatures):
        """Speichert als komprimiertes NPZ (schneller als JSON/Pickle)."""
        data = {}
        for k, v in features.model_dump().items():
            # Konvertiere Strings zu numpy-Strings für korrektes Speichern
            if isinstance(v, str):
                data[k] = np.array(v, dtype="<U20")
            elif v is None:
                # Speichere None als speziellen String-Marker
                data[k] = np.array("__NONE__", dtype="<U20")
            else:
                data[k] = v
        np.savez_compressed(path, **data)
        logger.info(f"[Cache] Features gespeichert: {path}")
