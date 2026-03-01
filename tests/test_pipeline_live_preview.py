"""
Tests für Pipeline und Live Preview.

Diese Tests mocken FFmpeg und externe Abhängigkeiten,
um schnelle, deterministische Tests zu ermöglichen.
"""

import pytest
import numpy as np
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import subprocess
import io


# =============================================================================
# Pipeline Tests (FFmpeg-Mocking)
# =============================================================================

class TestRenderPipeline:
    """Tests für RenderPipeline mit gemocktem FFmpeg."""
    
    @pytest.fixture
    def mock_features(self):
        """Erstellt gemockte AudioFeatures."""
        features = Mock()
        features.duration = 2.0
        features.tempo = 120.0
        features.mode = "music"
        features.key = "C major"
        features.fps = 30
        features.frame_count = 60
        features.sample_rate = 44100
        return features
    
    @pytest.fixture
    def mock_config(self, tmp_path):
        """Erstellt eine ProjectConfig."""
        from src.types import ProjectConfig, VisualConfig
        
        audio_file = tmp_path / "test_audio.wav"
        audio_file.write_bytes(b"RIFF" + b"\x00" * 100)  # Dummy WAV
        
        return ProjectConfig(
            audio_file=str(audio_file),
            output_file=str(tmp_path / "output.mp4"),
            visual=VisualConfig(
                type="pulsing_core",
                resolution=(640, 480),
                fps=30
            ),
            postprocess={}
        )
    
    @pytest.fixture
    def mock_visualizer(self):
        """Erstellt einen gemockten Visualizer."""
        visualizer = Mock()
        # Rendere schwarze Frames
        visualizer.render_frame = Mock(return_value=np.zeros((480, 640, 3), dtype=np.uint8))
        return visualizer
    
    def test_pipeline_init(self, mock_config):
        """Test Pipeline-Initialisierung."""
        from src.pipeline import RenderPipeline
        
        pipeline = RenderPipeline(mock_config)
        
        assert pipeline.config == mock_config
        assert pipeline.parallel is False
        assert pipeline.num_workers > 0
    
    def test_pipeline_init_with_parallel(self, mock_config):
        """Test Pipeline mit parallelem Rendering."""
        from src.pipeline import RenderPipeline
        
        pipeline = RenderPipeline(mock_config, parallel=True, num_workers=4)
        
        assert pipeline.parallel is True
        assert pipeline.num_workers == 4
    
    @patch('src.pipeline.verify_ffmpeg_or_raise')
    @patch('src.pipeline.validate_audio_file')
    @patch('src.pipeline.AudioAnalyzer')
    @patch('src.pipeline.VisualizerRegistry')
    @patch('subprocess.Popen')
    def test_render_video_success(self, mock_popen, mock_registry, mock_analyzer_class, 
                                   mock_validate, mock_ffmpeg_check, mock_config, mock_features):
        """Test erfolgreiches Video-Rendering."""
        from src.pipeline import RenderPipeline
        
        # Mocks einrichten
        mock_validate.return_value = {"path": mock_config.audio_file}
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = mock_features
        mock_analyzer_class.return_value = mock_analyzer
        
        mock_vis_class = Mock()
        mock_visualizer = Mock()
        mock_visualizer.render_frame.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_vis_class.return_value = mock_visualizer
        mock_registry.get.return_value = mock_vis_class
        mock_registry.autoload = Mock()
        
        # Mock FFmpeg-Prozess
        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        # Mock _mux_audio
        with patch.object(RenderPipeline, '_mux_audio') as mock_mux:
            pipeline = RenderPipeline(mock_config)
            pipeline.run(preview_mode=True, preview_duration=1.0)
            
            # Prüfe dass FFmpeg gestartet wurde
            assert mock_popen.called
            ffmpeg_call = mock_popen.call_args
            assert 'ffmpeg' in ffmpeg_call[0][0]
            
            # Prüfe dass Frames gerendert wurden
            assert mock_visualizer.render_frame.called
            
            # Prüfe dass Audio gemuxt wurde
            assert mock_mux.called
    
    @patch('src.pipeline.verify_ffmpeg_or_raise')
    @patch('src.pipeline.validate_audio_file')
    @patch('src.pipeline.AudioAnalyzer')
    @patch('src.pipeline.VisualizerRegistry')
    def test_run_preview_mode(self, mock_registry, mock_analyzer_class, 
                              mock_validate, mock_ffmpeg_check, 
                              mock_config, mock_features):
        """Test Preview-Mode reduziert Dauer."""
        from src.pipeline import RenderPipeline
        
        mock_validate.return_value = {"path": mock_config.audio_file}
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = mock_features
        mock_analyzer_class.return_value = mock_analyzer
        
        mock_vis_class = Mock()
        mock_visualizer = Mock()
        mock_visualizer.render_frame.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_vis_class.return_value = mock_visualizer
        mock_registry.get.return_value = mock_vis_class
        mock_registry.autoload = Mock()
        
        with patch.object(RenderPipeline, '_render_video') as mock_render:
            pipeline = RenderPipeline(mock_config)
            pipeline.run(preview_mode=True, preview_duration=1.0)
            
            # Preview-Mode sollte duration begrenzen
            assert mock_features.duration == 1.0
    
    @patch('subprocess.run')
    def test_mux_audio_success(self, mock_run, mock_config):
        """Test erfolgreiches Audio-Muxing."""
        from src.pipeline import RenderPipeline
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        pipeline = RenderPipeline(mock_config)
        
        # Sollte keinen Fehler werfen
        pipeline._mux_audio("/tmp/video.mp4", Path("/tmp/audio.mp3"), "/tmp/output.mp4")
        
        # Prüfe FFmpeg-Aufruf
        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        assert 'ffmpeg' in cmd
        assert '-c:v' in cmd
        assert '-c:a' in cmd
    
    @patch('subprocess.run')
    def test_mux_audio_failure(self, mock_run, mock_config):
        """Test Audio-Muxing Fehlerbehandlung."""
        from src.pipeline import RenderPipeline
        
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "FFmpeg error"
        mock_run.return_value = mock_result
        
        pipeline = RenderPipeline(mock_config)
        
        with pytest.raises(RuntimeError) as exc_info:
            pipeline._mux_audio("/tmp/video.mp4", Path("/tmp/audio.mp3"), "/tmp/output.mp4")
        
        assert "FFmpeg Fehler" in str(exc_info.value)
    
    @patch('src.pipeline.verify_ffmpeg_or_raise')
    @patch('src.pipeline.validate_audio_file')
    @patch('src.pipeline.AudioAnalyzer')
    @patch('src.pipeline.VisualizerRegistry')
    @patch('subprocess.Popen')
    def test_progress_callback(self, mock_popen, mock_registry, mock_analyzer_class,
                               mock_validate, mock_ffmpeg_check, 
                               mock_config, mock_features):
        """Test Progress-Callback wird aufgerufen."""
        from src.pipeline import RenderPipeline
        
        mock_validate.return_value = {"path": mock_config.audio_file}
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = mock_features
        mock_analyzer_class.return_value = mock_analyzer
        
        mock_vis_class = Mock()
        mock_visualizer = Mock()
        mock_visualizer.render_frame.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_vis_class.return_value = mock_visualizer
        mock_registry.get.return_value = mock_vis_class
        mock_registry.autoload = Mock()
        
        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        progress_calls = []
        def progress_cb(progress, message):
            progress_calls.append((progress, message))
        
        with patch.object(RenderPipeline, '_mux_audio'):
            pipeline = RenderPipeline(mock_config)
            pipeline.run(progress_callback=progress_cb)
            
            assert len(progress_calls) > 0
            # Erster Aufruf bei 0.0
            assert progress_calls[0][0] == 0.0
            # Letzter Aufruf bei 1.0
            assert progress_calls[-1][0] == 1.0
    
    @patch('src.pipeline.verify_ffmpeg_or_raise')
    @patch('src.pipeline.validate_audio_file')
    @patch('src.pipeline.AudioAnalyzer')
    @patch('src.pipeline.VisualizerRegistry')
    @patch('subprocess.Popen')
    def test_render_video_ffmpeg_error(self, mock_popen, mock_registry, mock_analyzer_class,
                                       mock_validate, mock_ffmpeg_check, 
                                       mock_config, mock_features):
        """Test Fehlerbehandlung bei FFmpeg-Fehler."""
        from src.pipeline import RenderPipeline
        
        mock_validate.return_value = {"path": mock_config.audio_file}
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = mock_features
        mock_analyzer_class.return_value = mock_analyzer
        
        mock_vis_class = Mock()
        mock_visualizer = Mock()
        mock_visualizer.render_frame.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_vis_class.return_value = mock_visualizer
        mock_registry.get.return_value = mock_vis_class
        mock_registry.autoload = Mock()
        
        # FFmpeg mit Fehler
        mock_process = Mock()
        mock_process.stdin = Mock()
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_process.returncode = 1
        mock_process.stderr.read.return_value = b"FFmpeg encoding error"
        mock_popen.return_value = mock_process
        
        with pytest.raises(RuntimeError) as exc_info:
            pipeline = RenderPipeline(mock_config)
            pipeline.run()
        
        assert "FFmpeg Fehler" in str(exc_info.value)


class TestPreviewPipeline:
    """Tests für PreviewPipeline."""
    
    @pytest.fixture
    def mock_config(self, tmp_path):
        """Erstellt eine ProjectConfig."""
        from src.types import ProjectConfig, VisualConfig
        
        audio_file = tmp_path / "test_audio.wav"
        audio_file.write_bytes(b"RIFF" + b"\x00" * 100)
        
        return ProjectConfig(
            audio_file=str(audio_file),
            output_file=str(tmp_path / "output.mp4"),
            visual=VisualConfig(
                type="pulsing_core",
                resolution=(1920, 1080),  # Hohe Auflösung
                fps=60
            ),
            postprocess={}
        )
    
    @patch('src.pipeline.verify_ffmpeg_or_raise')
    @patch('src.pipeline.validate_audio_file')
    @patch('src.pipeline.AudioAnalyzer')
    @patch('src.pipeline.VisualizerRegistry')
    def test_preview_reduces_resolution(self, mock_registry, mock_analyzer_class,
                                        mock_validate, mock_ffmpeg_check,
                                        mock_config):
        """Test dass Preview-Auflösung reduziert wird."""
        from src.pipeline import PreviewPipeline
        from src.types import AudioFeatures
        
        mock_validate.return_value = {"path": mock_config.audio_file}
        
        # Erstelle echte Features
        features = AudioFeatures(
            duration=2.0,
            sample_rate=44100,
            fps=60,
            rms=np.random.rand(120),
            onset=np.random.rand(120),
            spectral_centroid=np.random.rand(120),
            spectral_rolloff=np.random.rand(120),
            zero_crossing_rate=np.random.rand(120),
            chroma=np.random.rand(12, 120),
            mfcc=np.random.rand(13, 120),
            tempogram=np.random.rand(384, 120),
            tempo=120.0,
            key="C major",
            mode="music"
        )
        
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = features
        mock_analyzer_class.return_value = mock_analyzer
        
        mock_vis_class = Mock()
        mock_visualizer = Mock()
        mock_visualizer.render_frame.return_value = np.zeros((360, 640, 3), dtype=np.uint8)
        mock_vis_class.return_value = mock_visualizer
        mock_registry.get.return_value = mock_vis_class
        mock_registry.autoload = Mock()
        
        original_resolution = mock_config.visual.resolution
        original_fps = mock_config.visual.fps
        
        with patch.object(PreviewPipeline, '_render_video'):
            pipeline = PreviewPipeline(mock_config)
            pipeline.run(preview_duration=1.0)
            
            # Nach dem Run sollten Original-Werte wiederhergestellt sein
            assert mock_config.visual.resolution == original_resolution
            assert mock_config.visual.fps == original_fps
    
    @patch('src.pipeline.verify_ffmpeg_or_raise')
    @patch('src.pipeline.validate_audio_file')
    @patch('src.pipeline.AudioAnalyzer')
    @patch('src.pipeline.VisualizerRegistry')
    def test_preview_default_duration(self, mock_registry, mock_analyzer_class,
                                      mock_validate, mock_ffmpeg_check,
                                      mock_config):
        """Test Default-Preview-Dauer aus Settings."""
        from src.pipeline import PreviewPipeline
        from src.types import AudioFeatures
        
        mock_validate.return_value = {"path": mock_config.audio_file}
        
        features = AudioFeatures(
            duration=10.0,
            sample_rate=44100,
            fps=30,
            rms=np.random.rand(300),
            onset=np.random.rand(300),
            spectral_centroid=np.random.rand(300),
            spectral_rolloff=np.random.rand(300),
            zero_crossing_rate=np.random.rand(300),
            chroma=np.random.rand(12, 300),
            mfcc=np.random.rand(13, 300),
            tempogram=np.random.rand(384, 300),
            tempo=120.0,
            key="C major",
            mode="music"
        )
        
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = features
        mock_analyzer_class.return_value = mock_analyzer
        
        mock_vis_class = Mock()
        mock_visualizer = Mock()
        mock_visualizer.render_frame.return_value = np.zeros((360, 640, 3), dtype=np.uint8)
        mock_vis_class.return_value = mock_visualizer
        mock_registry.get.return_value = mock_vis_class
        mock_registry.autoload = Mock()
        
        with patch.object(PreviewPipeline, '_render_video'):
            pipeline = PreviewPipeline(mock_config)
            # Keine Dauer angegeben -> Settings werden verwendet
            pipeline.run()
            
            # Sollte nicht fehlschlagen
            assert True


# =============================================================================
# Live Preview Tests
# =============================================================================

class TestLivePreview:
    """Tests für LivePreview Klasse."""
    
    @pytest.fixture
    def mock_audio_features(self):
        """Erstellt Mock AudioFeatures."""
        from src.types import AudioFeatures
        
        return AudioFeatures(
            duration=5.0,
            sample_rate=44100,
            fps=30,
            rms=np.random.rand(150),
            onset=np.random.rand(150),
            spectral_centroid=np.random.rand(150),
            spectral_rolloff=np.random.rand(150),
            zero_crossing_rate=np.random.rand(150),
            chroma=np.random.rand(12, 150),
            mfcc=np.random.rand(13, 150),
            tempogram=np.random.rand(384, 150),
            tempo=120.0,
            key="C major",
            mode="music"
        )
    
    @patch('src.live_preview.AudioAnalyzer')
    @patch('src.live_preview.VisualizerRegistry')
    def test_init(self, mock_registry, mock_analyzer_class):
        """Test LivePreview Initialisierung."""
        from src.live_preview import LivePreview
        
        mock_registry.autoload = Mock()
        mock_registry.get.return_value = Mock()
        
        preview = LivePreview("spectrum_bars", resolution=(640, 360))
        
        assert preview.visualizer_type == "spectrum_bars"
        assert preview.resolution == (640, 360)
        assert preview.visualizer is None
        assert preview.features is None
    
    @patch('src.live_preview.AudioAnalyzer')
    @patch('src.live_preview.VisualizerRegistry')
    def test_analyze_audio(self, mock_registry, mock_analyzer_class, mock_audio_features, tmp_path):
        """Test Audio-Analyse."""
        from src.live_preview import LivePreview
        
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = mock_audio_features
        mock_analyzer_class.return_value = mock_analyzer
        
        mock_registry.autoload = Mock()
        mock_registry.get.return_value = Mock()
        
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"RIFF" + b"\x00" * 100)
        
        preview = LivePreview("spectrum_bars")
        features = preview.analyze_audio(str(audio_file))
        
        assert features == mock_audio_features
        assert preview.features == mock_audio_features
        mock_analyzer.analyze.assert_called_once_with(str(audio_file), fps=30)
    
    @patch('src.live_preview.AudioAnalyzer')
    @patch('src.live_preview.VisualizerRegistry')
    def test_setup_visualizer(self, mock_registry, mock_analyzer_class, mock_audio_features):
        """Test Visualizer-Setup."""
        from src.live_preview import LivePreview
        
        mock_vis_class = Mock()
        mock_visualizer = Mock()
        mock_vis_class.return_value = mock_visualizer
        mock_registry.get.return_value = mock_vis_class
        mock_registry.autoload = Mock()
        
        preview = LivePreview("spectrum_bars", resolution=(640, 360))
        preview.features = mock_audio_features
        
        colors = {"primary": "#FF0000", "secondary": "#00FF00", "background": "#000000"}
        preview.setup_visualizer(colors=colors)
        
        assert preview.visualizer == mock_visualizer
        mock_visualizer.setup.assert_called_once()
    
    @patch('src.live_preview.AudioAnalyzer')
    @patch('src.live_preview.VisualizerRegistry')
    def test_setup_visualizer_no_features(self, mock_registry, mock_analyzer_class):
        """Test Setup ohne Features wirft Fehler."""
        from src.live_preview import LivePreview
        
        mock_registry.autoload = Mock()
        mock_registry.get.return_value = Mock()
        
        preview = LivePreview("spectrum_bars")
        
        with pytest.raises(ValueError) as exc_info:
            preview.setup_visualizer()
        
        assert "Audio muss zuerst analysiert werden" in str(exc_info.value)
    
    @patch('src.live_preview.AudioAnalyzer')
    @patch('src.live_preview.VisualizerRegistry')
    def test_render_frame(self, mock_registry, mock_analyzer_class, mock_audio_features):
        """Test Frame-Rendering."""
        from src.live_preview import LivePreview
        
        mock_vis_class = Mock()
        mock_visualizer = Mock()
        expected_frame = np.zeros((360, 640, 3), dtype=np.uint8)
        mock_visualizer.render_frame.return_value = expected_frame
        mock_vis_class.return_value = mock_visualizer
        mock_registry.get.return_value = mock_vis_class
        mock_registry.autoload = Mock()
        
        preview = LivePreview("spectrum_bars")
        preview.features = mock_audio_features
        preview.setup_visualizer()
        
        frame = preview.render_frame(0)
        
        assert np.array_equal(frame, expected_frame)
        mock_visualizer.render_frame.assert_called_once_with(0)
    
    @patch('src.live_preview.AudioAnalyzer')
    @patch('src.live_preview.VisualizerRegistry')
    def test_render_frame_not_initialized(self, mock_registry, mock_analyzer_class):
        """Test Render ohne Visualizer wirft Fehler."""
        from src.live_preview import LivePreview
        
        mock_registry.autoload = Mock()
        mock_registry.get.return_value = Mock()
        
        preview = LivePreview("spectrum_bars")
        
        with pytest.raises(ValueError) as exc_info:
            preview.render_frame(0)
        
        assert "Visualizer nicht initialisiert" in str(exc_info.value)
    
    @patch('src.live_preview.AudioAnalyzer')
    @patch('src.live_preview.VisualizerRegistry')
    def test_render_preview_frames(self, mock_registry, mock_analyzer_class, mock_audio_features):
        """Test Rendern mehrerer Preview-Frames."""
        from src.live_preview import LivePreview
        
        mock_vis_class = Mock()
        mock_visualizer = Mock()
        mock_visualizer.render_frame.return_value = np.zeros((360, 640, 3), dtype=np.uint8)
        mock_vis_class.return_value = mock_visualizer
        mock_registry.get.return_value = mock_vis_class
        mock_registry.autoload = Mock()
        
        preview = LivePreview("spectrum_bars")
        preview.features = mock_audio_features
        preview.setup_visualizer()
        
        frames = preview.render_preview_frames(num_frames=10, start_frame=0)
        
        assert len(frames) == 10
        assert mock_visualizer.render_frame.call_count == 10
    
    @patch('src.live_preview.AudioAnalyzer')
    @patch('src.live_preview.VisualizerRegistry')
    def test_render_preview_frames_respects_frame_count(self, mock_registry, mock_analyzer_class, mock_audio_features):
        """Test dass Frame-Count respektiert wird."""
        from src.live_preview import LivePreview
        
        mock_vis_class = Mock()
        mock_visualizer = Mock()
        mock_visualizer.render_frame.return_value = np.zeros((360, 640, 3), dtype=np.uint8)
        mock_vis_class.return_value = mock_visualizer
        mock_registry.get.return_value = mock_vis_class
        mock_registry.autoload = Mock()
        
        preview = LivePreview("spectrum_bars")
        preview.features = mock_audio_features
        preview.setup_visualizer()
        
        # Versuche mehr Frames als verfügbar
        frames = preview.render_preview_frames(num_frames=1000, start_frame=0)
        
        # Sollte nur verfügbare Frames rendern
        assert len(frames) <= mock_audio_features.frame_count
    
    @patch('src.live_preview.AudioAnalyzer')
    @patch('src.live_preview.VisualizerRegistry')
    def test_frame_to_image(self, mock_registry, mock_analyzer_class, mock_audio_features):
        """Test Frame zu PIL Image Konvertierung."""
        from src.live_preview import LivePreview
        from PIL import Image
        
        mock_vis_class = Mock()
        mock_visualizer = Mock()
        mock_vis_class.return_value = mock_visualizer
        mock_registry.get.return_value = mock_vis_class
        mock_registry.autoload = Mock()
        
        preview = LivePreview("spectrum_bars")
        preview.features = mock_audio_features
        preview.setup_visualizer()
        
        frame = np.zeros((360, 640, 3), dtype=np.uint8)
        img = preview.frame_to_image(frame)
        
        assert isinstance(img, Image.Image)
        assert img.size == (640, 360)
    
    @patch('src.live_preview.AudioAnalyzer')
    @patch('src.live_preview.VisualizerRegistry')
    def test_frame_to_base64(self, mock_registry, mock_analyzer_class, mock_audio_features):
        """Test Frame zu Base64 Konvertierung."""
        from src.live_preview import LivePreview
        import base64
        
        mock_vis_class = Mock()
        mock_visualizer = Mock()
        mock_vis_class.return_value = mock_visualizer
        mock_registry.get.return_value = mock_vis_class
        mock_registry.autoload = Mock()
        
        preview = LivePreview("spectrum_bars")
        preview.features = mock_audio_features
        preview.setup_visualizer()
        
        frame = np.zeros((360, 640, 3), dtype=np.uint8)
        b64_str = preview.frame_to_base64(frame)
        
        assert b64_str.startswith("data:image/png;base64,")
        # Prüfe dass es gültiges Base64 ist
        encoded_part = b64_str.split(",")[1]
        decoded = base64.b64decode(encoded_part)
        assert len(decoded) > 0
    
    @patch('src.live_preview.AudioAnalyzer')
    @patch('src.live_preview.VisualizerRegistry')
    def test_get_thumbnail(self, mock_registry, mock_analyzer_class, mock_audio_features):
        """Test Thumbnail-Generierung."""
        from src.live_preview import LivePreview
        from PIL import Image
        
        mock_vis_class = Mock()
        mock_visualizer = Mock()
        mock_visualizer.render_frame.return_value = np.zeros((360, 640, 3), dtype=np.uint8)
        mock_vis_class.return_value = mock_visualizer
        mock_registry.get.return_value = mock_vis_class
        mock_registry.autoload = Mock()
        
        preview = LivePreview("spectrum_bars")
        preview.features = mock_audio_features
        preview.setup_visualizer()
        
        thumb = preview.get_thumbnail(frame_idx=0, size=(160, 90))
        
        assert isinstance(thumb, Image.Image)
        assert thumb.size[0] <= 160
        assert thumb.size[1] <= 90


class TestGeneratePreviewGif:
    """Tests für generate_preview_gif Funktion."""
    
    @patch('src.live_preview.LivePreview')
    @patch('PIL.Image.Image.save')
    def test_generate_preview_gif_success(self, mock_save, mock_preview_class, tmp_path):
        """Test erfolgreiche GIF-Generierung."""
        from src.live_preview import generate_preview_gif
        from PIL import Image
        
        mock_preview = Mock()
        mock_preview.features.frame_count = 60
        # Mock render_frame to return a valid array that can be converted to image
        mock_preview.render_frame.return_value = np.zeros((180, 320, 3), dtype=np.uint8)
        mock_preview_class.return_value = mock_preview
        
        audio_path = tmp_path / "test.wav"
        audio_path.write_bytes(b"RIFF" + b"\x00" * 100)
        output_path = tmp_path / "preview.gif"
        
        result = generate_preview_gif(
            str(audio_path),
            "spectrum_bars",
            str(output_path),
            duration=1.0,
            fps=10
        )
        
        assert result == str(output_path)
        mock_preview.analyze_audio.assert_called_once()
        mock_preview.setup_visualizer.assert_called_once()


class TestCompareVisualizers:
    """Tests für compare_visualizers Funktion."""
    
    @patch('src.live_preview.AudioAnalyzer')
    @patch('src.live_preview.VisualizerRegistry')
    def test_compare_visualizers_success(self, mock_registry, mock_analyzer_class, tmp_path):
        """Test erfolgreicher Visualizer-Vergleich."""
        from src.live_preview import compare_visualizers
        
        audio_path = tmp_path / "test.wav"
        audio_path.write_bytes(b"RIFF" + b"\x00" * 100)
        
        # Mock Features
        from src.types import AudioFeatures
        features = AudioFeatures(
            duration=2.0,
            sample_rate=44100,
            fps=30,
            rms=np.random.rand(60),
            onset=np.random.rand(60),
            spectral_centroid=np.random.rand(60),
            spectral_rolloff=np.random.rand(60),
            zero_crossing_rate=np.random.rand(60),
            chroma=np.random.rand(12, 60),
            mfcc=np.random.rand(13, 60),
            tempogram=np.random.rand(384, 60),
            tempo=120.0,
            key="C major",
            mode="music"
        )
        
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = features
        mock_analyzer_class.return_value = mock_analyzer
        
        mock_vis_class = Mock()
        mock_visualizer = Mock()
        mock_visualizer.render_frame.return_value = np.zeros((180, 320, 3), dtype=np.uint8)
        mock_vis_class.return_value = mock_visualizer
        mock_registry.get.return_value = mock_vis_class
        mock_registry.autoload = Mock()
        
        results = compare_visualizers(
            str(audio_path),
            ["spectrum_bars", "pulsing_core"],
            frame_idx=0
        )
        
        assert "spectrum_bars" in results
        assert "pulsing_core" in results
        assert results["spectrum_bars"] is not None
        assert results["pulsing_core"] is not None
    
    @patch('src.live_preview.AudioAnalyzer')
    @patch('src.live_preview.VisualizerRegistry')
    def test_compare_visualizers_with_error(self, mock_registry, mock_analyzer_class, tmp_path):
        """Test dass Fehler in einem Visualizer nicht alles stoppt."""
        from src.live_preview import compare_visualizers
        
        audio_path = tmp_path / "test.wav"
        audio_path.write_bytes(b"RIFF" + b"\x00" * 100)
        
        from src.types import AudioFeatures
        features = AudioFeatures(
            duration=2.0,
            sample_rate=44100,
            fps=30,
            rms=np.random.rand(60),
            onset=np.random.rand(60),
            spectral_centroid=np.random.rand(60),
            spectral_rolloff=np.random.rand(60),
            zero_crossing_rate=np.random.rand(60),
            chroma=np.random.rand(12, 60),
            mfcc=np.random.rand(13, 60),
            tempogram=np.random.rand(384, 60),
            tempo=120.0,
            key="C major",
            mode="music"
        )
        
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = features
        mock_analyzer_class.return_value = mock_analyzer
        
        # Erster Visualizer funktioniert, zweiter wirft Fehler
        def side_effect(*args, **kwargs):
            mock_vis = Mock()
            if len(mock_registry.get.call_args_list) == 1:
                mock_vis.render_frame.return_value = np.zeros((180, 320, 3), dtype=np.uint8)
            else:
                mock_vis.render_frame.side_effect = Exception("Render error")
            return mock_vis
        
        mock_registry.get.side_effect = side_effect
        mock_registry.autoload = Mock()
        
        results = compare_visualizers(
            str(audio_path),
            ["working_viz", "broken_viz"],
            frame_idx=0
        )
        
        # Beide sollten im Ergebnis sein, einer None
        assert "working_viz" in results
        assert "broken_viz" in results
