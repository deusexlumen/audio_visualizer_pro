"""
BaseVisualizer - Interface für alle Visualisierungen

KI-Agent: Diese Klasse erweitern für neue Effekte!
"""

from abc import ABC, abstractmethod
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, Tuple
from ..types import AudioFeatures, VisualConfig


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
                return ImageFont.truetype(path, size)
            except:
                continue
        
        return ImageFont.load_default()
    
    def _parse_colors(self, color_config: Dict[str, str]) -> Dict[str, Tuple[int, int, int, int]]:
        """Konvertiert Hex zu RGBA-Tupeln."""
        colors = {}
        for key, hex_val in color_config.items():
            hex_val = hex_val.lstrip('#')
            if len(hex_val) == 6:
                colors[key] = tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4)) + (255,)
            elif len(hex_val) == 3:
                colors[key] = tuple(int(hex_val[i]*2, 16) for i in range(3)) + (255,)
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
        idx = min(frame_idx, len(self.features.rms) - 1)
        chroma_idx = min(idx, self.features.chroma.shape[1] - 1)
        return {
            'rms': self.features.rms[idx],
            'onset': self.features.onset[idx],
            'spectral_centroid': self.features.spectral_centroid[idx],
            'spectral_rolloff': self.features.spectral_rolloff[idx],
            'zero_crossing_rate': self.features.zero_crossing_rate[idx],
            'chroma': self.features.chroma[:, chroma_idx],
            'progress': frame_idx / self.frame_count
        }
