"""
Pipeline - Der Haupt-Orchestrator

Steuert den kompletten Render-Flow von Audio-Analyse bis zum finalen Video.
"""

import numpy as np
from pathlib import Path
from typing import Optional
import tempfile
import subprocess

from .analyzer import AudioAnalyzer
from .visuals.registry import VisualizerRegistry
from .types import ProjectConfig, AudioFeatures
from .renderers.pil_renderer import PILRenderer
from .postprocess import PostProcessor


class RenderPipeline:
    """
    Haupt-Controller. Der KI-Agent startet hier.
    """
    
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.analyzer = AudioAnalyzer()
        self.post_processor = PostProcessor(config.postprocess)
        
    def run(self, preview_mode: bool = False, preview_duration: float = 5.0):
        """
        Führt die komplette Pipeline aus.
        
        Args:
            preview_mode: Rendert nur erste N Sekunden für schnelles Testen
            preview_duration: Dauer der Vorschau in Sekunden
        """
        audio_path = Path(self.config.audio_file)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio nicht gefunden: {audio_path}")
        
        # Schritt 1: Analyse (oder Cache laden)
        features = self.analyzer.analyze(
            str(audio_path), 
            fps=self.config.visual.fps
        )
        
        print(f"[Pipeline] Audio: {features.duration:.1f}s @ {features.tempo:.0f} BPM")
        print(f"[Pipeline] Mode: {features.mode}, Key: {features.key}")
        
        # Schritt 2: Visualizer initialisieren
        VisualizerRegistry.autoload()  # Lade alle Plugins
        visualizer_class = VisualizerRegistry.get(self.config.visual.type)
        visualizer = visualizer_class(self.config.visual, features)
        visualizer.setup()
        
        # Schritt 3: Rendering
        if preview_mode:
            print(f"[Pipeline] PREVIEW MODE: Nur erste {preview_duration} Sekunden")
            features.frame_count = int(preview_duration * features.fps)
        
        self._render_video(visualizer, features, audio_path)
        
        print(f"[Pipeline] Fertig! Output: {self.config.output_file}")
    
    def _render_video(self, visualizer, features: AudioFeatures, audio_path: Path):
        """Intern: Frame-Generierung + FFmpeg-Encoding."""
        
        # Temporäre Datei für Video (ohne Audio)
        temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        temp_video.close()
        
        try:
            # FFmpeg-Writer über subprocess
            fps = features.fps
            width, height = self.config.visual.resolution
            
            # FFmpeg-Befehl für Video-Encoding
            ffmpeg_cmd = [
                'ffmpeg', '-y',
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-s', f'{width}x{height}',
                '-pix_fmt', 'rgb24',
                '-r', str(fps),
                '-i', '-',  # Input von stdin
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-preset', 'medium',
                '-crf', '23',
                '-movflags', '+faststart',
                temp_video.name
            ]
            
            print(f"[Pipeline] Starte Rendering ({features.frame_count} Frames @ {fps}fps)...")
            
            # Starte FFmpeg-Prozess
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Frame-Loop mit Fortschrittsanzeige
            for i in range(features.frame_count):
                frame = visualizer.render_frame(i)
                
                # Post-Processing anwenden
                frame = self.post_processor.apply(frame)
                
                # Konvertiere zu bytes und schreibe zu FFmpeg
                process.stdin.write(frame.tobytes())
                
                # Fortschritt alle 30 Frames
                if i % 30 == 0 or i == features.frame_count - 1:
                    progress = (i + 1) / features.frame_count * 100
                    print(f"\r[Pipeline] Rendering: {progress:.1f}% ({i+1}/{features.frame_count})", end='', flush=True)
            
            print()  # Neue Zeile nach Fortschritt
            
            # Schließe stdin und warte auf FFmpeg
            process.stdin.close()
            process.wait()
            
            if process.returncode != 0:
                stderr = process.stderr.read().decode() if process.stderr else "Unbekannter Fehler"
                raise RuntimeError(f"FFmpeg Fehler beim Video-Encoding: {stderr}")
            
            # Audio hinzufügen (Muxing)
            self._mux_audio(temp_video.name, audio_path, self.config.output_file)
            
        finally:
            if Path(temp_video.name).exists():
                Path(temp_video.name).unlink()
    
    def _mux_audio(self, video_path: str, audio_path: Path, output_path: str):
        """Kombiniert Video mit Original-Audio."""
        
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', str(audio_path),
            '-c:v', 'copy',      # Video unverändert
            '-c:a', 'aac',       # AAC Audio Codec
            '-b:a', '320k',      # Hohe Audio-Qualität
            '-shortest',         # Kürzeste Länge bestimmt
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg Fehler beim Audio-Muxing: {result.stderr}")


class PreviewPipeline(RenderPipeline):
    """Schnelle Vorschau mit niedrigerer Auflösung."""
    
    def run(self, preview_mode: bool = True, preview_duration: float = 5.0):
        # Überschreibe Config mit 480p für Speed
        original_resolution = self.config.visual.resolution
        original_fps = self.config.visual.fps
        
        self.config.visual.resolution = (854, 480)
        self.config.visual.fps = 30
        
        try:
            super().run(preview_mode=True, preview_duration=preview_duration)
        finally:
            # Stelle Original-Werte wieder her
            self.config.visual.resolution = original_resolution
            self.config.visual.fps = original_fps
