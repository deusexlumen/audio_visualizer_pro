"""
Type Definitions für das Audio Visualizer Pro System.
Pydantic Models für alle Konfigurationen und Audio-Features.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, List, Dict, Optional, Tuple
import numpy as np


class AudioFeatures(BaseModel):
    """Schema für alle Audio-Features. Einheitlich für alle Renderer."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    duration: float
    sample_rate: int
    fps: int = 60
    
    @property
    def frame_count(self) -> int:
        """Berechnet die Anzahl der Frames basierend auf Dauer und FPS."""
        return int(self.duration * self.fps)
    
    # Zeitliche Features (Frame-basiert, Länge = duration * fps)
    rms: np.ndarray = Field(..., description="Loudness 0.0-1.0")
    onset: np.ndarray = Field(..., description="Beat detection 0.0-1.0")
    spectral_centroid: np.ndarray = Field(..., description="Brightness")
    spectral_rolloff: np.ndarray = Field(..., description="Bandwidth")
    zero_crossing_rate: np.ndarray = Field(..., description="Noisiness vs Tonal")
    
    # Tonaale Features (für Chroma-Color-Mapping)
    chroma: np.ndarray = Field(..., description="Shape: (12, frames) - C,C#,D...")
    mfcc: np.ndarray = Field(..., description="Timbre fingerprint")
    tempogram: np.ndarray = Field(..., description="Rhythmic structure")
    
    # Metadaten
    tempo: float
    key: Optional[str] = None  # "C major", "A minor" etc.
    mode: Literal["music", "speech", "hybrid"]


class VisualConfig(BaseModel):
    """Jeder Visualizer hat diese Konfiguration."""
    type: str  # "pulsing_core", "spectrum_bars" etc.
    params: Dict = Field(default_factory=dict)
    colors: Dict[str, str] = Field(default_factory=dict)  # Hex-Codes
    resolution: Tuple[int, int] = (1920, 1080)
    fps: int = 60


class ProjectConfig(BaseModel):
    """Gesamtkonfiguration einer Render-Job."""
    audio_file: str
    output_file: str
    visual: VisualConfig
    postprocess: Dict = Field(default_factory=dict)
