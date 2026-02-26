"""
Live-Preview für die GUI.

Zeigt einzelne Frames direkt in Streamlit an, ohne FFmpeg.
Nützlich für schnelles Testen von Einstellungen.
"""

import numpy as np
from PIL import Image
import io
import base64
from typing import Optional, Callable

from .visuals.registry import VisualizerRegistry
from .types import AudioFeatures, VisualConfig
from .analyzer import AudioAnalyzer
from .logger import get_logger

logger = get_logger("audio_visualizer.live_preview")


class LivePreview:
    """
    Live-Preview Generator für GUI-Integration.
    
    Rendert einzelne Frames für schnelle Vorschau ohne FFmpeg.
    """
    
    def __init__(self, visualizer_type: str, resolution: tuple = (640, 360)):
        """
        Args:
            visualizer_type: Name des Visualizers
            resolution: Vorschau-Auflösung (niedrig für Performance)
        """
        self.visualizer_type = visualizer_type
        self.resolution = resolution
        self.visualizer = None
        self.features = None
        
        # Lade Visualizer
        VisualizerRegistry.autoload()
        self.visualizer_class = VisualizerRegistry.get(visualizer_type)
        
    def analyze_audio(self, audio_path: str) -> AudioFeatures:
        """Analysiert Audio für Preview."""
        logger.info(f"Analysiere Audio für Preview: {audio_path}")
        analyzer = AudioAnalyzer()
        self.features = analyzer.analyze(audio_path, fps=30)
        return self.features
    
    def setup_visualizer(self, colors: Optional[dict] = None):
        """Initialisiert den Visualizer."""
        if self.features is None:
            raise ValueError("Audio muss zuerst analysiert werden")
        
        config = VisualConfig(
            type=self.visualizer_type,
            resolution=self.resolution,
            fps=30,
            colors=colors or {"primary": "#FF0055", "secondary": "#00CCFF", "background": "#0A0A0A"}
        )
        
        self.visualizer = self.visualizer_class(config, self.features)
        self.visualizer.setup()
        logger.info(f"Visualizer '{self.visualizer_type}' initialisiert")
    
    def render_frame(self, frame_idx: int) -> np.ndarray:
        """Rendert einen einzelnen Frame."""
        if self.visualizer is None:
            raise ValueError("Visualizer nicht initialisiert")
        
        return self.visualizer.render_frame(frame_idx)
    
    def render_preview_frames(self, num_frames: int = 30, start_frame: int = 0) -> list:
        """
        Rendert mehrere Frames für Preview.
        
        Args:
            num_frames: Anzahl der zu rendernden Frames
            start_frame: Start-Frame
        
        Returns:
            Liste von numpy Arrays
        """
        frames = []
        for i in range(num_frames):
            frame_idx = start_frame + i
            if frame_idx >= self.features.frame_count:
                break
            
            frame = self.render_frame(frame_idx)
            frames.append(frame)
            
            if i % 10 == 0:
                logger.debug(f"Preview-Frame {i+1}/{num_frames} gerendert")
        
        return frames
    
    def frame_to_image(self, frame: np.ndarray) -> Image.Image:
        """Konvertiert Frame zu PIL Image."""
        return Image.fromarray(frame)
    
    def frame_to_base64(self, frame: np.ndarray) -> str:
        """Konvertiert Frame zu Base64-String für HTML."""
        img = self.frame_to_image(frame)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_str = base64.b64encode(buffer.read()).decode()
        return f"data:image/png;base64,{img_str}"
    
    def get_thumbnail(self, frame_idx: int = 0, size: tuple = (320, 180)) -> Image.Image:
        """Erstellt ein Thumbnail-Bild."""
        frame = self.render_frame(frame_idx)
        img = self.frame_to_image(frame)
        img.thumbnail(size)
        return img


def generate_preview_gif(
    audio_path: str,
    visualizer_type: str,
    output_path: str,
    duration: float = 2.0,
    fps: int = 10,
    resolution: tuple = (320, 180)
):
    """
    Generiert eine animierte GIF-Vorschau.
    
    Args:
        audio_path: Pfad zur Audio-Datei
        visualizer_type: Visualizer-Name
        output_path: Ausgabepfad für GIF
        duration: Dauer der Vorschau in Sekunden
        fps: Frames pro Sekunde
        resolution: Auflösung
    """
    from PIL import Image
    
    logger.info(f"Generiere GIF-Vorschau: {output_path}")
    
    preview = LivePreview(visualizer_type, resolution)
    preview.analyze_audio(audio_path)
    preview.setup_visualizer()
    
    # Berechne Frames
    num_frames = int(duration * fps)
    frame_indices = np.linspace(0, preview.features.frame_count - 1, num_frames, dtype=int)
    
    frames = []
    for idx in frame_indices:
        frame = preview.render_frame(idx)
        img = Image.fromarray(frame)
        frames.append(img)
    
    # Speichere GIF
    if frames:
        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=int(1000 / fps),
            loop=0
        )
        logger.info(f"GIF gespeichert: {output_path}")
    
    return output_path


def compare_visualizers(
    audio_path: str,
    visualizers: list,
    frame_idx: int = 0,
    resolution: tuple = (320, 180)
) -> dict:
    """
    Vergleicht mehrere Visualizer an einem Frame.
    
    Args:
        audio_path: Pfad zur Audio-Datei
        visualizers: Liste der zu vergleichenden Visualizer
        frame_idx: Frame-Index
        resolution: Auflösung
    
    Returns:
        Dict mit {visualizer_name: frame_array}
    """
    analyzer = AudioAnalyzer()
    features = analyzer.analyze(audio_path, fps=30)
    
    VisualizerRegistry.autoload()
    
    results = {}
    for vis_name in visualizers:
        try:
            vis_class = VisualizerRegistry.get(vis_name)
            config = VisualConfig(
                type=vis_name,
                resolution=resolution,
                fps=30,
                colors={"primary": "#FF0055", "secondary": "#00CCFF", "background": "#0A0A0A"}
            )
            visualizer = vis_class(config, features)
            visualizer.setup()
            
            frame = visualizer.render_frame(frame_idx)
            results[vis_name] = frame
            
        except Exception as e:
            logger.error(f"Fehler bei Visualizer '{vis_name}': {e}")
            results[vis_name] = None
    
    return results
