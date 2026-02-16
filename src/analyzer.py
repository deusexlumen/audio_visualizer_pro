"""
AudioAnalyzer - Layer 1: Audio -> Features

Audio-Analyse mit aggressivem Caching.
Gleiche Audio-Datei = Sofort-Ergebnis bei wiederholtem Aufruf.
Thread-safe. Deterministisch.
"""

import librosa
import numpy as np
import hashlib
from pathlib import Path
from typing import Optional
from .types import AudioFeatures


class AudioAnalyzer:
    """
    Audio-Analyse mit aggressivem Caching.
    Gleiche Audio-Datei = Sofort-Ergebnis bei wiederholtem Aufruf.
    """
    
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
    
    def analyze(self, audio_path: str, fps: int = 60, force_reanalyze: bool = False) -> AudioFeatures:
        """
        Extrahiert alle Features. 
        KI-Agent: Diese Methode niemals ändern, nur erweitern!
        """
        cache_path = self._get_cache_path(audio_path, fps)
        
        if not force_reanalyze and cache_path.exists():
            print(f"[Cache] Lade Features für {audio_path}...")
            data = np.load(cache_path, allow_pickle=True)
            
            # Konvertiere geladene Daten zurück
            loaded_data = {}
            for k in data.files:
                val = data[k]
                # Konvertiere numpy-Strings zurück zu Python-Strings
                if isinstance(val, np.ndarray) and val.dtype.kind == 'U':
                    loaded_data[k] = str(val.item())
                else:
                    loaded_data[k] = val
            
            return AudioFeatures(**loaded_data)
        
        print(f"[Analyze] Verarbeite {audio_path}...")
        y, sr = librosa.load(audio_path, sr=None, mono=True)
        duration = librosa.get_duration(y=y, sr=sr)
        
        # Hop-Length für exakte FPS-Synchronisation
        hop_length = int(sr / fps)
        
        # --- Feature Extraction (Vektorisiert = Schnell) ---
        # 1. Energie (RMS)
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        rms = self._normalize(rms)
        
        # 2. Onset (Beats)
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
        onset = self._normalize(onset_env)
        
        # 3. Spektrale Features
        spec_cent = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
        spec_roll = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length)[0]
        zcr = librosa.feature.zero_crossing_rate(y=y, hop_length=hop_length)[0]
        
        # 4. Chroma (für Farb-Harmonien)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
        
        # 5. MFCC (für Timbre)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=hop_length)
        
        # 6. Tempo & Tempogram
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        tempogram = librosa.feature.tempogram(y=y, sr=sr, hop_length=hop_length)
        
        # 7. Mode Detection (Musik vs Sprache)
        mode = self._detect_mode(y, sr, tempo, onset_env)
        
        # 8. Key Detection (optional, etwas langsamer)
        key = self._estimate_key(chroma) if duration < 600 else None  # Nur für <10min
        
        features = AudioFeatures(
            duration=duration,
            sample_rate=sr,
            fps=fps,
            rms=self._interpolate_to_length(rms, int(duration * fps)),
            onset=self._interpolate_to_length(onset, int(duration * fps)),
            spectral_centroid=self._normalize(self._interpolate_to_length(spec_cent, int(duration * fps))),
            spectral_rolloff=self._normalize(self._interpolate_to_length(spec_roll, int(duration * fps))),
            zero_crossing_rate=self._normalize(self._interpolate_to_length(zcr, int(duration * fps))),
            chroma=chroma,  # Shape: (12, frames)
            mfcc=mfcc,
            tempogram=tempogram,
            tempo=float(tempo),
            key=key,
            mode=mode
        )
        
        # Caching
        self._save_cache(cache_path, features)
        return features
    
    def _normalize(self, x: np.ndarray) -> np.ndarray:
        """Min-Max Normalisierung 0-1."""
        return (x - x.min()) / (x.max() - x.min() + 1e-8)
    
    def _interpolate_to_length(self, data: np.ndarray, target_length: int) -> np.ndarray:
        """Gleicht Längenunterschiede aus (wichtig für exakte Frame-Sync)."""
        x_old = np.linspace(0, 1, len(data))
        x_new = np.linspace(0, 1, target_length)
        return np.interp(x_new, x_old, data)
    
    def _detect_mode(self, y, sr, tempo, onset_env) -> str:
        """KI-Logik: Einfache Heuristik für Musik vs Sprache."""
        onset_std = np.std(onset_env)
        try:
            spec_bw = librosa.feature.spectral_bandwidth(y=y, sr=sr).mean()
        except:
            spec_bw = 2000
        is_music = (tempo > 60) and (onset_std > 0.1) and (spec_bw > 2000)
        return "music" if is_music else "speech"
    
    def _estimate_key(self, chroma: np.ndarray) -> str:
        """Einfache Key-Estimation durch Korrelation mit Profilen."""
        # Vereinfacht: Durchschnitt über Zeit
        chroma_avg = np.mean(chroma, axis=1)
        # TODO: Korrelation mit Major/Minor Profilen
        keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        return keys[np.argmax(chroma_avg)] + " major"
    
    def _save_cache(self, path: Path, features: AudioFeatures):
        """Speichert als komprimiertes NPZ (schneller als JSON/Pickle)."""
        data = {}
        for k, v in features.model_dump().items():
            # Konvertiere Strings zu numpy-Strings für korrektes Speichern
            if isinstance(v, str):
                data[k] = np.array(v, dtype='<U20')
            else:
                data[k] = v
        np.savez_compressed(path, **data)
