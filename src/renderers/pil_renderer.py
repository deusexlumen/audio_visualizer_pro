"""
PILRenderer - Schnelle 2D-Rendering-Engine mit PIL

Standard-Renderer für schnelle und qualitativ hochwertige 2D-Visualisierungen.
Nutzt PIL (Pillow) für effiziente Bildgenerierung.
"""

import numpy as np
from PIL import Image
from typing import Iterator, Optional
from ..types import AudioFeatures, VisualConfig
from ..visuals.base import BaseVisualizer


class PILRenderer:
    """
    PIL-basierter Renderer für 2D-Visualisierungen.
    
    Optimiert für:
    - Schnelle Frame-Generierung
    - Niedrigen Speicherverbrauch
    - Einfache Integration mit FFmpeg
    """
    
    def __init__(self, visualizer: BaseVisualizer, features: AudioFeatures):
        self.visualizer = visualizer
        self.features = features
        self.frame_count = int(features.duration * features.fps)
        
    def render_frame(self, frame_idx: int) -> np.ndarray:
        """Rendert einen einzelnen Frame."""
        return self.visualizer.render_frame(frame_idx)
    
    def render_sequence(self, start_frame: int = 0, end_frame: Optional[int] = None) -> Iterator[np.ndarray]:
        """
        Rendert eine Sequenz von Frames.
        
        Yields:
            np.ndarray: RGB-Frame der Form (H, W, 3)
        """
        if end_frame is None:
            end_frame = self.frame_count
        
        for i in range(start_frame, end_frame):
            yield self.render_frame(i)
    
    def render_preview(self, duration: float = 5.0) -> Iterator[np.ndarray]:
        """
        Rendert eine Vorschau (erste N Sekunden).
        
        Args:
            duration: Dauer der Vorschau in Sekunden
        """
        preview_frames = int(duration * self.features.fps)
        for i in range(min(preview_frames, self.frame_count)):
            yield self.render_frame(i)
