"""
BaseVisualizer - Interface für alle Visualisierungen

KI-Agent: Diese Klasse erweitern für neue Effekte!
"""

from abc import ABC, abstractmethod
import numpy as np
from PIL import ImageFont
from typing import Dict, Any, Tuple
from ..types import AudioFeatures, VisualConfig
from ..logger import get_logger

logger = get_logger("audio_visualizer.visuals")


class BaseVisualizer(ABC):
    """
    Interface für alle Visualisierungen.
    KI-Agent: Diese Klasse erweitern für neue Effekte!
    """

    def __init__(self, config: VisualConfig, features: AudioFeatures):
        self.config = config
        self.features = features
        self.width, self.height = config.resolution
        self.frame_count = int(features.duration * features.fps)

        # Assets laden
        self.font = self._load_font()
        self.colors = self._parse_colors(config.colors)

    def _load_font(self, size: int = 40) -> ImageFont.FreeTypeFont:
        """Lädt System-Font oder Default. Unterstützt Windows, macOS und Linux."""
        font_paths = [
            # Projekt-Font
            "assets/fonts/Roboto-Bold.ttf",
            # Windows-Fonts
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            # macOS-Fonts
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial Bold.ttf",
            # Linux-Fonts
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        ]

        for path in font_paths:
            try:
                font = ImageFont.truetype(path, size)
                logger.debug(f"Font geladen: {path}")
                return font
            except Exception:
                continue

        logger.warning("Kein System-Font gefunden, verwende Default")
        return ImageFont.load_default()

    def _parse_colors(
        self, color_config: Dict[str, str]
    ) -> Dict[str, Tuple[int, int, int, int]]:
        """Konvertiert Hex zu RGBA-Tupeln."""
        colors = {}
        for key, hex_val in color_config.items():
            hex_val = hex_val.lstrip("#")
            if len(hex_val) == 6:
                colors[key] = tuple(int(hex_val[i : i + 2], 16) for i in (0, 2, 4)) + (
                    255,
                )
            elif len(hex_val) == 3:
                colors[key] = tuple(int(hex_val[i] * 2, 16) for i in range(3)) + (255,)
        return colors

    @abstractmethod
    def setup(self) -> None:
        """Einmalige Initialisierung vor dem Rendering."""
        pass

    @abstractmethod
    def render_frame(self, frame_idx: int) -> np.ndarray:
        """
        Rendert EINEN Frame als RGB-Array (H, W, 3).

        Parameter: frame_idx (0 bis frame_count-1)
        Returns: numpy array shape (height, width, 3), dtype uint8
        """
        pass

    def get_feature_at_frame(self, frame_idx: int) -> Dict[str, Any]:
        """Hilfsmethode: Features für aktuellen Frame extrahieren."""
        # Schutz gegen leere Arrays
        rms_len = len(self.features.rms)
        chroma_len = (
            self.features.chroma.shape[1] if self.features.chroma.ndim > 1 else 0
        )

        # Verhindere negative Indizes bei leeren Arrays
        if rms_len == 0:
            return {
                "rms": 0.0,
                "onset": 0.0,
                "spectral_centroid": 0.0,
                "spectral_rolloff": 0.0,
                "zero_crossing_rate": 0.0,
                "chroma": np.zeros(12),
                "progress": 0.0,
            }

        idx = min(max(0, frame_idx), rms_len - 1)
        chroma_idx = min(max(0, idx), chroma_len - 1) if chroma_len > 0 else 0

        return {
            "rms": self.features.rms[idx],
            "onset": self.features.onset[idx],
            "spectral_centroid": self.features.spectral_centroid[idx],
            "spectral_rolloff": self.features.spectral_rolloff[idx],
            "zero_crossing_rate": self.features.zero_crossing_rate[idx],
            "chroma": (
                self.features.chroma[:, chroma_idx] if chroma_len > 0 else np.zeros(12)
            ),
            "progress": frame_idx / self.frame_count if self.frame_count > 0 else 0.0,
        }
