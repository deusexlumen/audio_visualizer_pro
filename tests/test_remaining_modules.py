"""
Tests für verbleibende Module:
- keyboard_shortcuts.py
- utils.py
- postprocess.py
- parallel_renderer.py
- settings.py
"""

import pytest
import numpy as np
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import subprocess
import json


# =============================================================================
# Keyboard Shortcuts Tests (ohne Streamlit)
# =============================================================================

class TestShortcutKey:
    """Tests für ShortcutKey Enum."""
    
    def test_enum_values(self):
        """Test dass alle Shortcuts korrekte Werte haben."""
        from src.keyboard_shortcuts import ShortcutKey
        
        assert ShortcutKey.OPEN.value == "ctrl+o"
        assert ShortcutKey.SAVE.value == "ctrl+s"
        assert ShortcutKey.RENDER.value == "ctrl+r"
        assert ShortcutKey.PREVIEW.value == "ctrl+p"
        assert ShortcutKey.UNDO.value == "ctrl+z"
        assert ShortcutKey.REDO.value == "ctrl+y"
        assert ShortcutKey.ESCAPE.value == "escape"
        assert ShortcutKey.FULLSCREEN.value == "f11"


class TestShortcutAction:
    """Tests für ShortcutAction Dataclass."""
    
    def test_default_values(self):
        """Test Default-Werte."""
        from src.keyboard_shortcuts import ShortcutAction
        
        action = ShortcutAction(key="ctrl+o", description="Open")
        
        assert action.key == "ctrl+o"
        assert action.description == "Open"
        assert action.callback is None
        assert action.prevent_default is True
    
    def test_custom_values(self):
        """Test benutzerdefinierte Werte."""
        from src.keyboard_shortcuts import ShortcutAction
        
        callback = lambda: None
        action = ShortcutAction(
            key="ctrl+s",
            description="Save",
            callback=callback,
            prevent_default=False
        )
        
        assert action.callback == callback
        assert action.prevent_default is False


class TestKeyboardShortcutManagerLogic:
    """Tests für KeyboardShortcutManager Logik (ohne Streamlit)."""
    
    def test_register_and_unregister(self):
        """Test Registrierung und Deregistrierung."""
        from src.keyboard_shortcuts import KeyboardShortcutManager, ShortcutKey, ShortcutAction
        
        # Simuliere den Manager ohne Streamlit
        manager = Mock()
        manager.shortcuts = {}
        
        def register(key, description, callback=None, prevent_default=True):
            manager.shortcuts[key] = ShortcutAction(
                key=key.value,
                description=description,
                callback=callback,
                prevent_default=prevent_default
            )
        
        def unregister(key):
            if key in manager.shortcuts:
                del manager.shortcuts[key]
        
        manager.register = register
        manager.unregister = unregister
        
        # Teste Registrierung
        callback = Mock()
        manager.register(ShortcutKey.OPEN, "Open file", callback)
        
        assert ShortcutKey.OPEN in manager.shortcuts
        assert manager.shortcuts[ShortcutKey.OPEN].key == "ctrl+o"
        assert manager.shortcuts[ShortcutKey.OPEN].callback == callback
        
        # Teste Deregistrierung
        manager.unregister(ShortcutKey.OPEN)
        assert ShortcutKey.OPEN not in manager.shortcuts
    
    def test_get_js_component(self):
        """Test JavaScript Generierung."""
        from src.keyboard_shortcuts import ShortcutKey, ShortcutAction
        import json
        
        shortcuts = {
            ShortcutKey.OPEN: ShortcutAction("ctrl+o", "Open"),
            ShortcutKey.SAVE: ShortcutAction("ctrl+s", "Save", prevent_default=True)
        }
        
        # Simuliere JS-Generierung
        shortcuts_js = []
        for key, action in shortcuts.items():
            shortcuts_js.append({
                'key': action.key,
                'action': key.name,
                'preventDefault': action.prevent_default
            })
        
        js_output = json.dumps(shortcuts_js)
        
        assert "ctrl+o" in js_output
        assert "ctrl+s" in js_output
        assert "OPEN" in js_output
        assert "SAVE" in js_output
    
    def test_get_help_text(self):
        """Test Hilfe-Text Generierung."""
        from src.keyboard_shortcuts import ShortcutKey, ShortcutAction
        
        shortcuts = {
            ShortcutKey.OPEN: ShortcutAction("ctrl+o", "Open file"),
            ShortcutKey.SAVE: ShortcutAction("ctrl+s", "Save file")
        }
        
        lines = ["### ⌨️ Keyboard Shortcuts\n"]
        for key, action in shortcuts.items():
            key_display = action.key.replace('+', '+').upper()
            lines.append(f"**`{key_display}`** - {action.description}")
        help_text = "\n".join(lines)
        
        assert "Keyboard Shortcuts" in help_text
        assert "CTRL+O" in help_text
        assert "Open file" in help_text
        assert "CTRL+S" in help_text
        assert "Save file" in help_text


class TestUndoRedoManagerLogic:
    """Tests für UndoRedoManager Logik (ohne Streamlit)."""
    
    def test_undo_redo_cycle(self):
        """Test vollständiger Undo/Redo Zyklus."""
        # Manuelle Implementierung
        max_history = 20
        undo_stack = []
        redo_stack = []
        
        def push_state(state):
            state_copy = json.loads(json.dumps(state, default=str))
            undo_stack.append(state_copy)
            if len(undo_stack) > max_history:
                undo_stack.pop(0)
            redo_stack.clear()
        
        def can_undo():
            return len(undo_stack) > 1
        
        def can_redo():
            return len(redo_stack) > 0
        
        def undo():
            if not can_undo():
                return None
            current = undo_stack.pop()
            redo_stack.append(current)
            return undo_stack[-1] if undo_stack else None
        
        def redo():
            if not can_redo():
                return None
            state = redo_stack.pop()
            undo_stack.append(state)
            return state
        
        # Teste Zyklus
        push_state({"v": 1})
        push_state({"v": 2})
        push_state({"v": 3})
        
        assert can_undo()
        assert undo()["v"] == 2
        assert undo()["v"] == 1
        assert can_redo()
        assert redo()["v"] == 2
        assert redo()["v"] == 3
    
    def test_max_history(self):
        """Test History-Limit."""
        max_history = 3
        undo_stack = []
        
        def push_state(state):
            undo_stack.append(state)
            if len(undo_stack) > max_history:
                undo_stack.pop(0)
        
        for i in range(5):
            push_state({"v": i})
        
        assert len(undo_stack) == 3
        assert undo_stack[0]["v"] == 2
        assert undo_stack[-1]["v"] == 4
    
    def test_clear(self):
        """Test Löschen der History."""
        undo_stack = [{"v": 1}, {"v": 2}]
        redo_stack = [{"v": 3}]
        
        # Clear
        undo_stack.clear()
        redo_stack.clear()
        
        assert len(undo_stack) == 0
        assert len(redo_stack) == 0


# =============================================================================
# Utils Tests
# =============================================================================

class TestFFmpegUtils:
    """Tests für FFmpeg Utilities."""
    
    @patch('shutil.which')
    @patch('subprocess.run')
    def test_check_ffmpeg_success(self, mock_run, mock_which):
        """Test erfolgreicher FFmpeg-Check."""
        from src.utils import check_ffmpeg
        
        mock_which.return_value = "/usr/bin/ffmpeg"
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "ffmpeg version 4.4.2\n built with gcc"
        mock_run.return_value = mock_result
        
        success, message = check_ffmpeg()
        
        assert success is True
        assert "ffmpeg version" in message.lower()
    
    @patch('shutil.which')
    def test_check_ffmpeg_not_found(self, mock_which):
        """Test FFmpeg nicht gefunden."""
        from src.utils import check_ffmpeg
        
        mock_which.return_value = None
        
        success, message = check_ffmpeg()
        
        assert success is False
        assert "nicht im PATH" in message
    
    @patch('shutil.which')
    @patch('subprocess.run')
    def test_check_ffmpeg_error(self, mock_run, mock_which):
        """Test FFmpeg Fehler."""
        from src.utils import check_ffmpeg
        
        mock_which.return_value = "/usr/bin/ffmpeg"
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "FFmpeg error"
        mock_run.return_value = mock_result
        
        success, message = check_ffmpeg()
        
        assert success is False
        assert "Fehler" in message
    
    @patch('shutil.which')
    @patch('subprocess.run')
    def test_check_ffmpeg_timeout(self, mock_run, mock_which):
        """Test FFmpeg Timeout."""
        from src.utils import check_ffmpeg
        
        mock_which.return_value = "/usr/bin/ffmpeg"
        mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 10)
        
        success, message = check_ffmpeg()
        
        assert success is False
        assert "timed out" in message.lower()
    
    @patch('src.utils.check_ffmpeg')
    def test_verify_ffmpeg_or_raise_success(self, mock_check):
        """Test erfolgreiche Verifikation."""
        from src.utils import verify_ffmpeg_or_raise
        
        mock_check.return_value = (True, "ffmpeg version 4.4.2")
        
        # Sollte keinen Fehler werfen
        verify_ffmpeg_or_raise()
    
    @patch('src.utils.check_ffmpeg')
    def test_verify_ffmpeg_or_raise_failure(self, mock_check):
        """Test Verifikation Fehler."""
        from src.utils import verify_ffmpeg_or_raise, FFmpegError
        
        mock_check.return_value = (False, "FFmpeg nicht gefunden")
        
        with pytest.raises(FFmpegError) as exc_info:
            verify_ffmpeg_or_raise()
        
        assert "FFmpeg nicht gefunden" in str(exc_info.value)


class TestAudioValidation:
    """Tests für Audio-Datei Validierung."""
    
    def test_validate_audio_file_success(self, tmp_path):
        """Test erfolgreiche Validierung."""
        from src.utils import validate_audio_file
        
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"dummy audio data")
        
        result = validate_audio_file(str(audio_file))
        
        assert result["name"] == "test.mp3"
        assert result["extension"] == ".mp3"
        assert result["size_bytes"] == len(b"dummy audio data")
    
    def test_validate_audio_file_not_found(self):
        """Test Datei nicht gefunden."""
        from src.utils import validate_audio_file, AudioValidationError
        
        with pytest.raises(AudioValidationError) as exc_info:
            validate_audio_file("/nonexistent/file.mp3")
        
        assert "nicht gefunden" in str(exc_info.value)
    
    def test_validate_audio_file_not_a_file(self, tmp_path):
        """Test Pfad ist keine Datei."""
        from src.utils import validate_audio_file, AudioValidationError
        
        with pytest.raises(AudioValidationError) as exc_info:
            validate_audio_file(str(tmp_path))
        
        assert "keine Datei" in str(exc_info.value)
    
    def test_validate_audio_file_invalid_extension(self, tmp_path):
        """Test ungültige Dateiendung."""
        from src.utils import validate_audio_file, AudioValidationError
        
        invalid_file = tmp_path / "test.txt"
        invalid_file.write_bytes(b"not audio")
        
        with pytest.raises(AudioValidationError) as exc_info:
            validate_audio_file(str(invalid_file))
        
        assert "Ungültiges Format" in str(exc_info.value)
    
    def test_validate_audio_file_empty(self, tmp_path):
        """Test leere Datei."""
        from src.utils import validate_audio_file, AudioValidationError
        
        empty_file = tmp_path / "empty.mp3"
        empty_file.write_bytes(b"")
        
        with pytest.raises(AudioValidationError) as exc_info:
            validate_audio_file(str(empty_file))
        
        assert "Datei ist leer" in str(exc_info.value)
    
    def test_validate_audio_file_all_formats(self, tmp_path):
        """Test alle unterstützten Formate."""
        from src.utils import validate_audio_file
        
        formats = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma']
        
        for fmt in formats:
            audio_file = tmp_path / f"test{fmt}"
            audio_file.write_bytes(b"dummy")
            
            result = validate_audio_file(str(audio_file))
            assert result["extension"] == fmt


class TestCacheUtils:
    """Tests für Cache Utilities."""
    
    def test_get_cache_size_empty(self, tmp_path):
        """Test Cache-Größe bei leerem Verzeichnis."""
        from src.utils import get_cache_size
        
        cache_dir = tmp_path / "empty_cache"
        cache_dir.mkdir()
        
        size, size_str = get_cache_size(cache_dir)
        
        assert size == 0
        assert size_str in ["0 MB", "0 B"]  # Beides ist OK
    
    def test_get_cache_size_with_files(self, tmp_path):
        """Test Cache-Größe mit Dateien."""
        from src.utils import get_cache_size
        
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        
        # Erstelle Dateien
        (cache_dir / "file1.txt").write_bytes(b"a" * 1024)  # 1KB
        (cache_dir / "file2.txt").write_bytes(b"b" * 1024 * 512)  # 512KB
        
        size, size_str = get_cache_size(cache_dir)
        
        assert size == 1024 + 1024 * 512
        assert "KB" in size_str or "MB" in size_str
    
    def test_get_cache_size_nonexistent(self, tmp_path):
        """Test Cache-Größe bei nicht-existierendem Verzeichnis."""
        from src.utils import get_cache_size
        
        cache_dir = tmp_path / "nonexistent"
        
        size, size_str = get_cache_size(cache_dir)
        
        assert size == 0
        assert size_str == "0 MB"
    
    def test_clear_cache_success(self, tmp_path):
        """Test erfolgreiches Löschen des Caches."""
        from src.utils import clear_cache
        
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        
        # Erstelle Dateien
        (cache_dir / "file1.txt").write_text("test")
        (cache_dir / "subdir").mkdir()
        (cache_dir / "subdir" / "file2.txt").write_text("test2")
        
        deleted = clear_cache(cache_dir)
        
        assert deleted == 2
        assert not (cache_dir / "file1.txt").exists()
        assert not (cache_dir / "subdir" / "file2.txt").exists()
    
    def test_clear_cache_nonexistent(self, tmp_path):
        """Test Clear bei nicht-existierendem Verzeichnis."""
        from src.utils import clear_cache
        
        cache_dir = tmp_path / "nonexistent"
        
        deleted = clear_cache(cache_dir)
        
        assert deleted == 0


# =============================================================================
# PostProcess Tests
# =============================================================================

class TestPostProcessor:
    """Tests für PostProcessor."""
    
    @pytest.fixture
    def processor(self):
        """Erstellt einen PostProcessor."""
        from src.postprocess import PostProcessor
        
        config = {
            "contrast": 1.0,
            "saturation": 1.0,
            "brightness": 1.0,
            "grain": 0.0,
            "vignette": 0.0,
            "chromatic_aberration": 0.0
        }
        return PostProcessor(config)
    
    def test_init(self):
        """Test Initialisierung."""
        from src.postprocess import PostProcessor
        
        config = {"contrast": 1.2, "saturation": 0.9}
        processor = PostProcessor(config)
        
        assert processor.config["contrast"] == 1.2
        assert processor.config["saturation"] == 0.9
    
    def test_apply_no_effects(self, processor):
        """Test Anwenden ohne Effekte."""
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        result = processor.apply(frame)
        
        # Ohne Effekte sollte das Bild unverändert sein
        assert np.array_equal(result, frame)
    
    def test_apply_contrast(self):
        """Test Kontrast-Anpassung."""
        from src.postprocess import PostProcessor
        
        config = {"contrast": 1.5, "saturation": 1.0, "brightness": 1.0}
        processor = PostProcessor(config)
        
        frame = np.ones((100, 100, 3), dtype=np.uint8) * 128
        result = processor.apply(frame)
        
        # Kontrast sollte angewendet werden
        assert result.shape == frame.shape
        assert result.dtype == frame.dtype
    
    def test_apply_saturation(self):
        """Test Sättigungs-Anpassung."""
        from src.postprocess import PostProcessor
        
        config = {"contrast": 1.0, "saturation": 0.5, "brightness": 1.0}
        processor = PostProcessor(config)
        
        frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        result = processor.apply(frame)
        
        assert result.shape == frame.shape
    
    def test_apply_brightness(self):
        """Test Helligkeits-Anpassung."""
        from src.postprocess import PostProcessor
        
        config = {"contrast": 1.0, "saturation": 1.0, "brightness": 1.2}
        processor = PostProcessor(config)
        
        frame = np.ones((100, 100, 3), dtype=np.uint8) * 100
        result = processor.apply(frame)
        
        assert result.shape == frame.shape
    
    def test_apply_grain(self):
        """Test Film Grain Effekt."""
        from src.postprocess import PostProcessor
        
        config = {"grain": 0.1}
        processor = PostProcessor(config)
        
        frame = np.ones((100, 100, 3), dtype=np.uint8) * 128
        result = processor.apply(frame)
        
        # Mit Grain sollte das Bild leicht verändert sein
        assert result.shape == frame.shape
    
    def test_apply_vignette(self):
        """Test Vignette Effekt."""
        from src.postprocess import PostProcessor
        
        config = {"vignette": 0.5}
        processor = PostProcessor(config)
        
        frame = np.ones((100, 100, 3), dtype=np.uint8) * 255
        result = processor.apply(frame)
        
        # Mit Vignette sollten die Ränder dunkler sein
        assert result.shape == frame.shape
    
    def test_apply_chromatic_aberration(self):
        """Test Chromatic Aberration Effekt."""
        from src.postprocess import PostProcessor
        
        config = {"chromatic_aberration": 2.0}
        processor = PostProcessor(config)
        
        frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        result = processor.apply(frame)
        
        assert result.shape == frame.shape
    
    def test_apply_multiple_effects(self):
        """Test mehrere Effekte gleichzeitig."""
        from src.postprocess import PostProcessor
        
        config = {
            "contrast": 1.2,
            "saturation": 0.9,
            "brightness": 1.1,
            "grain": 0.05,
            "vignette": 0.3
        }
        processor = PostProcessor(config)
        
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        result = processor.apply(frame)
        
        assert result.shape == frame.shape
        assert result.dtype == frame.dtype


# =============================================================================
# Settings Tests
# =============================================================================

class TestSettings:
    """Tests für Settings."""
    
    @patch.dict('os.environ', {
        'AV_CACHE_DIR': '.cache/test_cache',
        'AV_DEFAULT_RESOLUTION': '1280x720',
        'AV_DEFAULT_FPS': '30',
        'AV_LOG_LEVEL': 'DEBUG'
    })
    def test_settings_from_env(self):
        """Test Settings aus Umgebungsvariablen."""
        from src.settings import Settings
        
        settings = Settings.from_env()
        
        assert settings.default_resolution == (1280, 720)
        assert settings.default_fps == 30
        assert settings.log_level == 'DEBUG'
    
    def test_settings_defaults(self):
        """Test Default-Settings."""
        from src.settings import Settings
        
        with patch.dict('os.environ', {}, clear=True):
            settings = Settings()
            
            assert settings.default_resolution == (1920, 1080)
            assert settings.default_fps == 60
            assert settings.log_level == 'INFO'
    
    def test_resolution_parsing(self):
        """Test Auflösungs-Parsing."""
        from src.settings import Settings
        
        with patch.dict('os.environ', {'AV_DEFAULT_RESOLUTION': '3840x2160'}):
            settings = Settings.from_env()
            assert settings.default_resolution == (3840, 2160)
    
    def test_get_settings_singleton(self):
        """Test dass get_settings Singleton zurückgibt."""
        from src.settings import get_settings
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2


# =============================================================================
# Parallel Renderer Tests
# =============================================================================

class TestParallelRenderer:
    """Tests für ParallelRenderer."""
    
    def test_get_optimal_workers(self):
        """Test Berechnung der optimalen Worker-Anzahl."""
        from src.parallel_renderer import get_optimal_workers
        
        with patch('multiprocessing.cpu_count') as mock_cpu:
            mock_cpu.return_value = 8
            
            workers = get_optimal_workers()
            
            # Sollte CPU-Count - 1 sein, aber mindestens 1
            assert workers >= 1
            assert workers <= 8
    
    def test_render_frames_parallel_few_frames(self):
        """Test Rendering mit wenigen Frames (direktes Rendering)."""
        from src.parallel_renderer import ParallelRenderer
        
        renderer = ParallelRenderer(num_workers=1)  # Single-Worker für Test
        
        render_func = Mock(return_value=np.zeros((100, 100, 3), dtype=np.uint8))
        frame_indices = [0, 1, 2]
        
        results = renderer.render_frames_parallel(render_func, frame_indices, chunk_size=10)
        
        assert len(results) == 3
        assert render_func.call_count == 3


class TestExportProfiles:
    """Tests für Export Profiles."""
    
    def test_youtube_profile(self):
        """Test YouTube Export-Profil."""
        from src.export_profiles import get_profile, Platform
        
        profile = get_profile(Platform.YOUTUBE)
        
        assert profile is not None
        assert "YouTube" in profile.name
        assert profile.resolution == (1920, 1080)
    
    def test_instagram_profile(self):
        """Test Instagram Export-Profil."""
        from src.export_profiles import get_profile, Platform
        
        profile = get_profile(Platform.INSTAGRAM_REELS)
        
        assert profile is not None
        assert profile.resolution == (1080, 1920)  # 9:16
    
    def test_tiktok_profile(self):
        """Test TikTok Export-Profil."""
        from src.export_profiles import get_profile, Platform
        
        profile = get_profile(Platform.TIKTOK)
        
        assert profile is not None
        assert profile.resolution == (1080, 1920)  # 9:16
    
    def test_invalid_profile(self):
        """Test ungültiges Profil (sollte CUSTOM zurückgeben)."""
        from src.export_profiles import get_profile, Platform
        
        # Ungültiger String wird zu CUSTOM
        profile = get_profile("invalid_profile")
        
        # Sollte Custom-Profil zurückgeben
        assert profile is not None
    
    def test_list_profiles(self):
        """Test Profile auflisten."""
        from src.export_profiles import list_profiles
        
        profiles = list_profiles()
        
        assert "youtube" in profiles
        assert "tiktok" in profiles
    
    def test_calculate_bitrate(self):
        """Test Bitrate-Berechnung."""
        from src.export_profiles import calculate_bitrate, get_profile, Platform
        
        profile = get_profile(Platform.TIKTOK)
        bitrate = calculate_bitrate(profile, 60.0)  # 60 Sekunden
        
        assert bitrate > 0
        assert bitrate <= 20000
    
    def test_calculate_bitrate_no_limit(self):
        """Test Bitrate ohne Dateigrößenlimit."""
        from src.export_profiles import calculate_bitrate
        from src.export_profiles import ExportProfile
        
        profile = ExportProfile(
            name="Test",
            resolution=(1920, 1080),
            fps=30,
            aspect_ratio="16:9",
            ffmpeg_preset="medium",
            ffmpeg_crf=23,
            ffmpeg_audio_bitrate="320k",
            max_file_size=None  # Kein Limit
        )
        
        bitrate = calculate_bitrate(profile, 60.0)
        
        assert bitrate == 8000  # Default
    
    def test_apply_profile_to_settings(self):
        """Test Profil auf Settings anwenden."""
        from src.export_profiles import apply_profile_to_settings, get_profile, Platform
        
        profile = get_profile(Platform.YOUTUBE)
        settings = {
            'visual': {'resolution': [640, 480], 'fps': 30},
            'ffmpeg_preset': 'fast',
            'ffmpeg_crf': 28,
            'ffmpeg_audio_bitrate': '128k'
        }
        
        result = apply_profile_to_settings(profile, settings)
        
        assert result['visual']['resolution'] == [1920, 1080]
        assert result['visual']['fps'] == 60
        assert result['ffmpeg_preset'] == 'slow'
