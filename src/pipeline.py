"""
Pipeline - Der Haupt-Orchestrator

Steuert den kompletten Render-Flow von Audio-Analyse bis zum finalen Video.
"""

import numpy as np
from pathlib import Path
from typing import Optional, Callable
import tempfile
import subprocess

from .analyzer import AudioAnalyzer
from .visuals.registry import VisualizerRegistry
from .types import ProjectConfig, AudioFeatures
from .renderers.pil_renderer import PILRenderer
from .postprocess import PostProcessor
from .logger import get_logger
from .utils import verify_ffmpeg_or_raise, validate_audio_file
from .settings import get_settings
from .parallel_renderer import ParallelRenderer, get_optimal_workers
from .export_profiles import ExportProfile

logger = get_logger("audio_visualizer.pipeline")


class RenderPipeline:
    """
    Haupt-Controller. Der KI-Agent startet hier.
    """
    
    def __init__(self, config: ProjectConfig, parallel: bool = False, num_workers: Optional[int] = None, export_profile: Optional[ExportProfile] = None):
        """
        Args:
            config: Projekt-Konfiguration
            parallel: Ob paralleles Rendering genutzt werden soll
            num_workers: Anzahl Worker (None = auto)
            export_profile: Optional Export-Profil für Plattform-optimierte Einstellungen
        """
        self.config = config
        self.analyzer = AudioAnalyzer()
        self.post_processor = PostProcessor(config.postprocess)
        self.parallel = parallel
        self.num_workers = num_workers or get_optimal_workers()
        self.export_profile = export_profile
        
    def run(
        self, 
        preview_mode: bool = False, 
        preview_duration: float = 5.0,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ):
        """
        Führt die komplette Pipeline aus.
        
        Args:
            preview_mode: Rendert nur erste N Sekunden für schnelles Testen
            preview_duration: Dauer der Vorschau in Sekunden
            progress_callback: Optionaler Callback(progress: float, message: str)
                             progress ist 0.0-1.0, message ist Status-Text
        """
        # System-Checks
        verify_ffmpeg_or_raise()
        
        # Audio-Validierung
        audio_info = validate_audio_file(self.config.audio_file)
        audio_path = Path(audio_info["path"])
        
        # Schritt 1: Analyse (oder Cache laden)
        features = self.analyzer.analyze(
            str(audio_path), 
            fps=self.config.visual.fps
        )
        
        logger.info(f"Audio: {features.duration:.1f}s @ {features.tempo:.0f} BPM")
        logger.info(f"Mode: {features.mode}, Key: {features.key}")
        
        # Schritt 2: Visualizer initialisieren
        VisualizerRegistry.autoload()  # Lade alle Plugins
        visualizer_class = VisualizerRegistry.get(self.config.visual.type)
        visualizer = visualizer_class(self.config.visual, features)
        visualizer.setup()
        
        # Schritt 3: Rendering
        if preview_mode:
            logger.info(f"PREVIEW MODE: Nur erste {preview_duration} Sekunden")
            # Für Preview: Dauer begrenzen (frame_count ist ein Property basierend auf duration)
            features.duration = min(preview_duration, features.duration)
        
        self._render_video(visualizer, features, audio_path, progress_callback)
        
        if progress_callback:
            progress_callback(1.0, "Fertig!")
        logger.info(f"Fertig! Output: {self.config.output_file}")
    
    def _render_video(
        self, 
        visualizer, 
        features: AudioFeatures, 
        audio_path: Path,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ):
        """Intern: Frame-Generierung + FFmpeg-Encoding."""
        settings = get_settings()
        
        # Temporäre Datei für Video (ohne Audio)
        temp_video = tempfile.NamedTemporaryFile(
            suffix='.mp4', 
            delete=False,
            dir=str(settings.temp_dir)
        )
        temp_video.close()
        
        try:
            # FFmpeg-Writer über subprocess
            fps = features.fps
            width, height = self.config.visual.resolution
            
            # FFmpeg-Parameter wählen (Export-Profil hat Priorität)
            if self.export_profile:
                preset = self.export_profile.ffmpeg_preset
                crf = self.export_profile.ffmpeg_crf
            else:
                preset = settings.ffmpeg_preset
                crf = settings.ffmpeg_crf
            
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
                '-preset', preset,
                '-crf', str(crf),
                '-movflags', '+faststart',
                temp_video.name
            ]
            
            logger.info(f"Starte Rendering ({features.frame_count} Frames @ {fps}fps)...")
            if self.parallel:
                logger.info(f"[EXPERIMENTAL] Paralleles Rendering mit {self.num_workers} Workern")
            if progress_callback:
                progress_callback(0.0, f"Starte Rendering ({features.frame_count} Frames)...")
            
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
                    progress = (i + 1) / features.frame_count
                    progress_pct = progress * 100
                    logger.info(f"Rendering: {progress_pct:.1f}% ({i+1}/{features.frame_count})")
                    if progress_callback:
                        progress_callback(progress, f"Rendering... {progress_pct:.1f}%")
            
            logger.info("Rendering abgeschlossen")
            
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
        settings = get_settings()
        
        # Audio-Bitrate wählen (Export-Profil hat Priorität)
        if self.export_profile:
            audio_bitrate = self.export_profile.ffmpeg_audio_bitrate
        else:
            audio_bitrate = settings.ffmpeg_audio_bitrate
        
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', str(audio_path),
            '-c:v', 'copy',      # Video unverändert
            '-c:a', 'aac',       # AAC Audio Codec
            '-b:a', audio_bitrate,
            '-shortest',         # Kürzeste Länge bestimmt
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg Fehler beim Audio-Muxing: {result.stderr}")


class PreviewPipeline(RenderPipeline):
    """Schnelle Vorschau mit niedrigerer Auflösung."""
    
    def __init__(self, config: ProjectConfig, parallel: bool = False, num_workers: Optional[int] = None):
        super().__init__(config, parallel=parallel, num_workers=num_workers)
    
    def run(
        self, 
        preview_mode: bool = True, 
        preview_duration: float = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ):
        settings = get_settings()
        
        # Verwende Settings wenn keine Dauer angegeben
        if preview_duration is None:
            preview_duration = settings.default_preview_duration
        
        # Überschreibe Config mit Preview-Settings
        original_resolution = self.config.visual.resolution
        original_fps = self.config.visual.fps
        
        self.config.visual.resolution = settings.preview_resolution
        self.config.visual.fps = settings.preview_fps
        
        try:
            super().run(
                preview_mode=True, 
                preview_duration=preview_duration,
                progress_callback=progress_callback
            )
        finally:
            # Stelle Original-Werte wieder her
            self.config.visual.resolution = original_resolution
            self.config.visual.fps = original_fps
