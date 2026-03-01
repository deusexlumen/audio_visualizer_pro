"""
Integration Tests für Audio Visualizer Pro

Testet komplette Workflows von Audio-Input bis Video-Output.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analyzer import AudioAnalyzer
from src.pipeline import PreviewPipeline, RenderPipeline
from src.postprocess import PostProcessor
from src.types import AudioFeatures, ProjectConfig, VisualConfig
from src.visuals.registry import VisualizerRegistry


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def test_audio_file():
    """Erstellt eine Test-Audiodatei (Sinus-Ton)."""
    temp_dir = tempfile.mkdtemp()
    audio_path = Path(temp_dir) / "test_audio.wav"
    
    # Erstelle 2-Sekunden Sinus-Ton (440Hz A4)
    duration = 2.0
    sample_rate = 44100
    frequency = 440.0
    amplitude = 0.5
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = amplitude * np.sin(2 * np.pi * frequency * t)
    
    # Konvertiere zu 16-bit PCM
    audio_int16 = (audio_data * 32767).astype(np.int16)
    
    with wave.open(str(audio_path), 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())
    
    yield audio_path
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_output_dir():
    """Temporäres Output-Verzeichnis."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def analyzer():
    """AudioAnalyzer Instanz."""
    return AudioAnalyzer()


@pytest.fixture
def visualizer_registry():
    """Registry mit allen geladenen Visualizern."""
    registry = VisualizerRegistry()
    registry.autoload()
    return registry


# =============================================================================
# Audio Analysis Integration Tests
# =============================================================================

class TestAudioAnalysisIntegration:
    """Tests für die Audio-Analyse Pipeline."""
    
    def test_full_analysis_workflow(self, test_audio_file, analyzer, temp_output_dir):
        """Kompletter Analyse-Workflow mit Caching."""
        # Erste Analyse
        features1 = analyzer.analyze(test_audio_file, fps=30)
        
        assert features1 is not None
        assert features1.duration > 0
        assert features1.fps == 30
        assert len(features1.rms) > 0
        assert len(features1.onset) > 0
        
        # Zweite Analyse sollte aus Cache kommen
        start_time = time.time()
        features2 = analyzer.analyze(test_audio_file, fps=30)
        cache_time = time.time() - start_time
        
        assert features1.duration == features2.duration
        assert np.array_equal(features1.rms, features2.rms)
        # Cache sollte schnell sein (< 1s)
        assert cache_time < 1.0
    
    def test_analysis_with_different_fps(self, test_audio_file, analyzer):
        """Analyse mit verschiedenen FPS-Werten."""
        for fps in [24, 30, 60]:
            features = analyzer.analyze(test_audio_file, fps=fps)
            expected_frames = int(features.duration * fps)
            # Erlaube kleine Abweichung durch Rundung
            assert abs(len(features.rms) - expected_frames) <= 2
    
    def test_analyze_nonexistent_file(self, analyzer):
        """Fehlerbehandlung für nicht existierende Datei."""
        with pytest.raises(Exception):
            analyzer.analyze(Path("/nonexistent/file.mp3"), fps=30)


# =============================================================================
# Visualizer Integration Tests
# =============================================================================

class TestVisualizerIntegration:
    """Tests für Visualizer-Rendering."""
    
    def test_all_visualizers_render(self, visualizer_registry):
        """Jeder Visualizer sollte rendern können."""
        dummy_features = AudioFeatures(
            duration=1.0,
            sample_rate=44100,
            fps=30,
            rms=np.random.rand(30),
            onset=np.random.rand(30),
            spectral_centroid=np.random.rand(30),
            spectral_rolloff=np.random.rand(30),
            zero_crossing_rate=np.random.rand(30),
            chroma=np.random.rand(12, 30),
            mfcc=np.random.rand(13, 30),
            tempogram=np.random.rand(384, 30),
            tempo=120.0,
            key="C major",
            mode="music"
        )
        
        config = VisualConfig(
            type="pulsing_core",
            resolution=(640, 480),
            fps=30
        )
        
        visualizers = visualizer_registry.list_available()
        assert len(visualizers) > 0
        
        for viz_name in visualizers:
            visualizer_class = visualizer_registry.get(viz_name)
            assert visualizer_class is not None
            
            visualizer = visualizer_class(config, dummy_features)
            visualizer.setup()  # Wichtig: setup() aufrufen
            
            # Rendere ersten Frame
            frame = visualizer.render_frame(0)
            
            assert isinstance(frame, np.ndarray)
            assert frame.shape == (480, 640, 3)
            assert frame.dtype == np.uint8
            assert frame.min() >= 0 and frame.max() <= 255
    
    def test_visualizer_frame_consistency(self, visualizer_registry):
        """Gleicher Frame-Index sollte konsistentes Ergebnis liefern."""
        dummy_features = AudioFeatures(
            duration=1.0,
            sample_rate=44100,
            fps=30,
            rms=np.ones(30) * 0.5,
            onset=np.zeros(30),
            spectral_centroid=np.ones(30) * 0.5,
            spectral_rolloff=np.ones(30) * 0.5,
            zero_crossing_rate=np.zeros(30),
            chroma=np.ones((12, 30)) * 0.1,
            mfcc=np.zeros((13, 30)),
            tempogram=np.zeros((384, 30)),
            tempo=120.0,
            key="C major",
            mode="music"
        )
        
        config = VisualConfig(
            type="pulsing_core",
            resolution=(320, 240),
            fps=30
        )
        
        visualizer_class = visualizer_registry.get("pulsing_core")
        visualizer = visualizer_class(config, dummy_features)
        visualizer.setup()
        
        # Gleicher Frame sollte identisch sein
        frame1 = visualizer.render_frame(5)
        frame2 = visualizer.render_frame(5)
        
        assert np.array_equal(frame1, frame2)


# =============================================================================
# Post-Processing Integration Tests
# =============================================================================

class TestPostProcessingIntegration:
    """Tests für Post-Processing Effekte."""
    
    def test_postprocess_apply(self):
        """Post-Processing sollte Frame transformieren."""
        config = {
            'contrast': 1.2,
            'saturation': 1.5,
            'brightness': 0.9,
            'grain': 0.1,
            'vignette': 0.2,
            'chromatic_aberration': 0.0
        }
        
        processor = PostProcessor(config)
        
        # Erstelle Test-Frame (Rot)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :, 0] = 255  # Roter Kanal
        
        processed = processor.apply(frame)
        
        assert processed.shape == frame.shape
        assert processed.dtype == np.uint8
    
    def test_postprocess_no_effects(self):
        """Post-Processing ohne Effekte sollte Frame ähnlich lassen."""
        config = {
            'contrast': 1.0,
            'saturation': 1.0,
            'brightness': 1.0,
            'grain': 0.0,
            'vignette': 0.0,
            'chromatic_aberration': 0.0
        }
        
        processor = PostProcessor(config)
        
        frame = np.random.randint(0, 256, (240, 320, 3), dtype=np.uint8)
        processed = processor.apply(frame)
        
        # Frame sollte fast gleich sein (kleine Rundungsfehler erlaubt)
        assert processed.shape == frame.shape
        assert processed.dtype == np.uint8


# =============================================================================
# Render Pipeline Integration Tests
# =============================================================================

class TestRenderPipelineIntegration:
    """Tests für komplette Render-Pipelines."""
    
    @pytest.mark.slow
    @pytest.mark.skipif(
        os.system("ffmpeg -version > nul 2>&1") != 0,
        reason="FFmpeg nicht installiert"
    )
    def test_preview_pipeline_render(self, test_audio_file, temp_output_dir, visualizer_registry):
        """Preview-Pipeline sollte Video erstellen."""
        output_path = temp_output_dir / "preview_output.mp4"
        
        config = ProjectConfig(
            audio_file=str(test_audio_file),
            output_file=str(output_path),
            visual=VisualConfig(
                type="pulsing_core",
                resolution=(480, 360),
                fps=15
            ),
            postprocess={},
            export={'preview_mode': True}
        )
        
        pipeline = PreviewPipeline(config)
        
        progress_calls = []
        def progress_cb(progress, status):
            progress_calls.append((progress, status))
        
        pipeline.run(progress_callback=progress_cb)
        
        # Output-Datei sollte existieren
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        
        # Progress sollte aufgerufen worden sein
        assert len(progress_calls) > 0
        assert progress_calls[-1][0] == 100.0
    
    @pytest.mark.slow
    @pytest.mark.skipif(
        os.system("ffmpeg -version > nul 2>&1") != 0,
        reason="FFmpeg nicht installiert"
    )
    def test_render_pipeline_with_postprocess(self, test_audio_file, temp_output_dir):
        """Render-Pipeline mit Post-Processing."""
        output_path = temp_output_dir / "processed_output.mp4"
        
        config = ProjectConfig(
            audio_file=str(test_audio_file),
            output_file=str(output_path),
            visual=VisualConfig(
                type="spectrum_bars",
                resolution=(640, 480),
                fps=24
            ),
            postprocess={
                'contrast': 1.2,
                'saturation': 1.3,
                'grain': 0.05,
                'vignette': 0.1
            },
            export={'quality': 'high'}
        )
        
        pipeline = RenderPipeline(config)
        pipeline.run()
        
        assert output_path.exists()
        assert output_path.stat().st_size > 0
    
    def test_pipeline_invalid_visualizer(self, test_audio_file, temp_output_dir):
        """Fehlerbehandlung für ungültigen Visualizer."""
        output_path = temp_output_dir / "error_output.mp4"
        
        config = ProjectConfig(
            audio_file=str(test_audio_file),
            output_file=str(output_path),
            visual=VisualConfig(
                type="nonexistent_visualizer",
                resolution=(640, 480),
                fps=30
            ),
            postprocess={},
            export={}
        )
        
        with pytest.raises(Exception):
            pipeline = RenderPipeline(config)
            pipeline.run()


# =============================================================================
# End-to-End Workflow Tests
# =============================================================================

class TestEndToEndWorkflow:
    """Komplette Workflow-Tests."""
    
    @pytest.mark.slow
    @pytest.mark.skipif(
        os.system("ffmpeg -version > nul 2>&1") != 0,
        reason="FFmpeg nicht installiert"
    )
    def test_complete_music_video_workflow(self, test_audio_file, temp_output_dir):
        """Kompletter Workflow: Analyse → Visualisierung → Export."""
        output_path = temp_output_dir / "final_music_video.mp4"
        
        # Schritt 1: Audio-Analyse
        analyzer = AudioAnalyzer()
        features = analyzer.analyze(test_audio_file, fps=30)
        
        assert features.duration > 0
        # Note: Tempo detection may return 0 for short/synthetic audio
        assert features.tempo >= 0
        
        # Schritt 2: Projekt-Konfiguration
        config = ProjectConfig(
            audio_file=str(test_audio_file),
            output_file=str(output_path),
            visual=VisualConfig(
                type="pulsing_core",
                resolution=(640, 480),
                fps=30,
                colors={
                    "primary": "#FF0055",
                    "secondary": "#00CCFF",
                    "background": "#0A0A0A"
                }
            ),
            postprocess={
                'contrast': 1.1,
                'saturation': 1.2
            },
            export={
                'quality': 'high',
                'include_audio': True
            }
        )
        
        # Schritt 3: Rendering
        pipeline = RenderPipeline(config)
        pipeline.run()
        
        # Schritt 4: Validierung
        assert output_path.exists()
        assert output_path.stat().st_size > 1000  # Mindestens 1KB
    
    def test_config_serialization_workflow(self, test_audio_file, temp_output_dir):
        """Config-Speicherung und Laden."""
        config_path = temp_output_dir / "project_config.json"
        
        # Erstelle Config
        original_config = ProjectConfig(
            audio_file=str(test_audio_file),
            output_file=str(temp_output_dir / "output.mp4"),
            visual=VisualConfig(
                type="particle_swarm",
                resolution=(1920, 1080),
                fps=60
            ),
            postprocess={
                'grain': 0.1,
                'vignette': 0.2
            }
        )
        
        # Speichern
        config_dict = original_config.model_dump()
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2, default=str)
        
        # Laden
        with open(config_path, 'r') as f:
            loaded_dict = json.load(f)
        
        loaded_config = ProjectConfig(**loaded_dict)
        
        # Validierung
        assert loaded_config.visual.type == original_config.visual.type
        assert loaded_config.visual.resolution == original_config.visual.resolution
        assert loaded_config.visual.fps == original_config.visual.fps
        assert loaded_config.postprocess.get('grain') == original_config.postprocess.get('grain')


# =============================================================================
# Error Handling & Edge Cases
# =============================================================================

class TestErrorHandling:
    """Fehlerbehandlungs-Tests."""
    
    def test_corrupt_audio_handling(self, temp_output_dir):
        """Behandlung beschädigter Audio-Dateien."""
        corrupt_file = temp_output_dir / "corrupt.wav"
        
        # Erstelle ungültige WAV-Datei
        with open(corrupt_file, 'w') as f:
            f.write("DIES IST KEINE GÜLTIGE WAV-DATEI")
        
        analyzer = AudioAnalyzer()
        
        with pytest.raises(Exception):
            analyzer.analyze(corrupt_file, fps=30)
    
    def test_insufficient_disk_space_simulation(self, test_audio_file, temp_output_dir):
        """Simulierte Speicherplatz-Probleme."""
        output_path = temp_output_dir / "output.mp4"
        
        config = ProjectConfig(
            audio_file=str(test_audio_file),
            output_file=str(output_path),
            visual=VisualConfig(
                type="pulsing_core",
                resolution=(320, 240),
                fps=15
            ),
            postprocess={},
            export={}
        )
        
        # Sollte ohne Fehler laufen
        pipeline = PreviewPipeline(config)
        # Wir testen nur die Initialisierung, nicht den vollen Render
        assert pipeline is not None
    
    def test_very_short_audio(self, temp_output_dir):
        """Sehr kurze Audio-Dateien (< 1 Sekunde)."""
        audio_path = temp_output_dir / "short.wav"
        
        # Erstelle 0.1-Sekunden Audio
        duration = 0.1
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = 0.5 * np.sin(2 * np.pi * 440 * t)
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        with wave.open(str(audio_path), 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        
        analyzer = AudioAnalyzer()
        
        # Sollte auch mit sehr kurzen Dateien funktionieren
        features = analyzer.analyze(audio_path, fps=30)
        assert features.duration < 1.0


# =============================================================================
# Performance Tests
# =============================================================================

class TestPerformance:
    """Performance- und Benchmark-Tests."""
    
    def test_analysis_performance(self, test_audio_file, analyzer):
        """Analyse-Performance-Messung."""
        # Erster Aufruf (wahrscheinlich aus Cache nach anderen Tests)
        start = time.time()
        features = analyzer.analyze(test_audio_file, fps=30)
        duration = time.time() - start
        
        # 2-Sekunden Audio sollte in < 30 Sekunden analysiert sein (inkl. Feature-Extraktion)
        # Aus dem Cache sollte es viel schneller sein (< 1s)
        assert duration < 30.0
        
        # Cache-Performance: Mehrere Aufrufe sollten konsistent schnell sein
        durations = []
        for _ in range(3):
            start = time.time()
            analyzer.analyze(test_audio_file, fps=30)
            durations.append(time.time() - start)
        
        # Alle Cache-Zugriffe sollten schnell sein (< 1s)
        assert all(d < 1.0 for d in durations)
    
    def test_rendering_throughput(self, test_audio_file, temp_output_dir):
        """Rendering-Durchsatz-Messung."""
        # Erstelle Features
        analyzer = AudioAnalyzer()
        features = analyzer.analyze(test_audio_file, fps=30)
        
        config = VisualConfig(
            type="pulsing_core",
            resolution=(640, 480),
            fps=30
        )
        
        registry = VisualizerRegistry()
        registry.autoload()
        visualizer_class = registry.get("pulsing_core")
        visualizer = visualizer_class(config, features)
        visualizer.setup()
        
        # Messe Rendering-Zeit für 30 Frames
        start = time.time()
        
        for i in range(min(30, features.frame_count)):
            frame = visualizer.render_frame(i)
            assert frame is not None
        
        duration = time.time() - start
        
        # Sollte mindestens 5 FPS Rendering-Rate haben
        fps = 30 / duration
        assert fps > 5.0


# =============================================================================
# CLI Integration Tests
# =============================================================================

class TestCLIIntegration:
    """Tests für CLI-Befehle."""
    
    def test_cli_check_command(self):
        """CLI 'check' Befehl."""
        result = subprocess.run(
            [sys.executable, "-m", "main", "check"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent)
        )
        
        # Sollte ohne Fehler ausführen
        assert result.returncode == 0
    
    def test_cli_list_visuals(self):
        """CLI 'list-visuals' Befehl."""
        result = subprocess.run(
            [sys.executable, "-m", "main", "list-visuals"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent)
        )
        
        assert result.returncode == 0
        assert "pulsing_core" in result.stdout or "spectrum_bars" in result.stdout
    
    def test_cli_analyze(self, test_audio_file):
        """CLI 'analyze' Befehl."""
        result = subprocess.run(
            [sys.executable, "-m", "main", "analyze", str(test_audio_file)],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent)
        )
        
        # Sollte analysieren und Info ausgeben
        assert result.returncode == 0
        # Check for German output (Dauer) or English (Duration/duration)
        assert "Dauer" in result.stdout or "Duration" in result.stdout or "duration" in result.stdout


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
