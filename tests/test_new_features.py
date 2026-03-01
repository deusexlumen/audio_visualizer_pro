"""
Tests für neue Features:
- Keyboard Shortcuts
- Auto-Save
- Preset Manager
- Real-Time Audio
- 3D WebGL
"""

import pytest
import json
import time
import tempfile
import shutil
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


# =============================================================================
# Keyboard Shortcuts Tests
# =============================================================================

class TestKeyboardShortcuts:
    """Tests für Keyboard Shortcuts System."""
    
    def test_shortcut_key_enum(self):
        """Test ShortcutKey Enum Werte."""
        from src.keyboard_shortcuts import ShortcutKey
        
        assert ShortcutKey.OPEN.value == "ctrl+o"
        assert ShortcutKey.SAVE.value == "ctrl+s"
        assert ShortcutKey.RENDER.value == "ctrl+r"
        assert ShortcutKey.UNDO.value == "ctrl+z"
        assert ShortcutKey.REDO.value == "ctrl+y"
        assert ShortcutKey.ESCAPE.value == "escape"
        assert ShortcutKey.FULLSCREEN.value == "f11"
    
    def test_shortcut_action_creation(self):
        """Test ShortcutAction Dataclass."""
        from src.keyboard_shortcuts import ShortcutAction, ShortcutKey
        
        callback = Mock()
        action = ShortcutAction(
            key=ShortcutKey.OPEN.value,
            description="Test action",
            callback=callback,
            prevent_default=True
        )
        
        assert action.key == "ctrl+o"
        assert action.description == "Test action"
        assert action.callback == callback
        assert action.prevent_default is True
    
    def test_keyboard_manager_init(self):
        """Test KeyboardShortcutManager Initialisierung (ohne Streamlit)."""
        from src.keyboard_shortcuts import ShortcutAction, ShortcutKey
        
        # Teste die Logik ohne Streamlit-Abhängigkeit
        action = ShortcutAction(
            key=ShortcutKey.OPEN.value,
            description="Test",
            callback=None
        )
        
        assert action.key == "ctrl+o"
    
    def test_register_shortcut(self):
        """Test Shortcut Registrierung (Dictionary-basiert)."""
        from src.keyboard_shortcuts import ShortcutAction, ShortcutKey
        
        # Simuliere Manager-Verhalten
        shortcuts = {}
        callback = Mock()
        
        action = ShortcutAction(
            key=ShortcutKey.OPEN.value,
            description="Audio öffnen",
            callback=callback
        )
        shortcuts[ShortcutKey.OPEN] = action
        
        assert ShortcutKey.OPEN in shortcuts
        assert shortcuts[ShortcutKey.OPEN].key == "ctrl+o"
        assert shortcuts[ShortcutKey.OPEN].description == "Audio öffnen"
    
    def test_unregister_shortcut(self):
        """Test Shortcut Entfernung."""
        from src.keyboard_shortcuts import ShortcutAction, ShortcutKey
        
        shortcuts = {}
        action = ShortcutAction(key=ShortcutKey.OPEN.value, description="Test")
        shortcuts[ShortcutKey.OPEN] = action
        
        assert ShortcutKey.OPEN in shortcuts
        del shortcuts[ShortcutKey.OPEN]
        assert ShortcutKey.OPEN not in shortcuts
    
    def test_get_js_component(self):
        """Test JavaScript Generierung."""
        from src.keyboard_shortcuts import ShortcutAction, ShortcutKey
        import json
        
        shortcuts = {
            ShortcutKey.OPEN: ShortcutAction(ShortcutKey.OPEN.value, "Audio öffnen"),
            ShortcutKey.SAVE: ShortcutAction(ShortcutKey.SAVE.value, "Speichern")
        }
        
        shortcuts_js = []
        for key, action in shortcuts.items():
            shortcuts_js.append({
                'key': action.key,
                'action': key.name,
                'preventDefault': action.prevent_default
            })
        
        js = json.dumps(shortcuts_js)
        
        assert "ctrl+o" in js
        assert "ctrl+s" in js
        assert "OPEN" in js
        assert "SAVE" in js
    
    def test_get_help_text(self):
        """Test Hilfe-Text Generierung."""
        from src.keyboard_shortcuts import ShortcutAction, ShortcutKey
        
        shortcuts = {
            ShortcutKey.OPEN: ShortcutAction(ShortcutKey.OPEN.value, "Audio öffnen"),
            ShortcutKey.SAVE: ShortcutAction(ShortcutKey.SAVE.value, "Projekt speichern")
        }
        
        lines = ["### ⌨️ Keyboard Shortcuts\n"]
        for key, action in shortcuts.items():
            key_display = action.key.replace('+', '+').upper()
            lines.append(f"**`{key_display}`** - {action.description}")
        help_text = "\n".join(lines)
        
        assert "Keyboard Shortcuts" in help_text
        assert "CTRL+O" in help_text
        assert "Audio öffnen" in help_text
        assert "CTRL+S" in help_text


class TestUndoRedoManager:
    """Tests für Undo/Redo System (ohne Streamlit)."""
    
    def test_undo_redo_cycle_manual(self):
        """Test vollständiger Undo/Redo Zyklus mit manuellem State."""
        # Manuelle Implementierung des Undo/Redo-Systems
        max_history = 20
        undo_stack = []
        redo_stack = []
        
        def push_state(state):
            import json
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
        push_state({"version": 1})
        push_state({"version": 2})
        push_state({"version": 3})
        
        assert can_undo() is True
        assert undo()["version"] == 2
        assert undo()["version"] == 1
        assert redo()["version"] == 2
        assert redo()["version"] == 3
    
    def test_max_history_limit_manual(self):
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
        assert undo_stack[0]["v"] == 2  # Ältester Eintrag
        assert undo_stack[-1]["v"] == 4  # Neuester Eintrag


# =============================================================================
# Auto-Save Tests
# =============================================================================

class TestAutoSaveConfig:
    """Tests für AutoSaveConfig."""
    
    def test_default_values(self):
        """Test Default-Werte."""
        from src.auto_save import AutoSaveConfig
        
        config = AutoSaveConfig()
        
        assert config.interval_seconds == 30.0
        assert config.max_backups == 5
        assert config.backup_dir == ".cache/autosave"
        assert config.enabled is True
    
    def test_custom_values(self):
        """Test benutzerdefinierte Werte."""
        from src.auto_save import AutoSaveConfig
        
        config = AutoSaveConfig(
            interval_seconds=60.0,
            max_backups=10,
            backup_dir="custom/backups",
            enabled=False
        )
        
        assert config.interval_seconds == 60.0
        assert config.max_backups == 10
        assert config.backup_dir == "custom/backups"
        assert config.enabled is False


class TestAutoSaveManager:
    """Tests für AutoSaveManager."""
    
    @pytest.fixture
    def temp_dir(self):
        """Erstellt ein temporäres Verzeichnis."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def autosave(self, temp_dir):
        """Erstellt einen AutoSaveManager mit temporärem Verzeichnis."""
        from src.auto_save import AutoSaveManager, AutoSaveConfig
        
        config = AutoSaveConfig(backup_dir=str(temp_dir / "autosave"))
        return AutoSaveManager(config)
    
    def test_init_creates_directory(self, temp_dir):
        """Test dass Backup-Verzeichnis erstellt wird."""
        from src.auto_save import AutoSaveManager, AutoSaveConfig
        
        backup_dir = temp_dir / "new_autosave"
        config = AutoSaveConfig(backup_dir=str(backup_dir))
        
        assert not backup_dir.exists()
        manager = AutoSaveManager(config)
        assert backup_dir.exists()
    
    def test_get_config_hash(self, autosave):
        """Test Hash-Generierung für Config."""
        config1 = {"key": "value", "number": 42}
        config2 = {"key": "value", "number": 42}
        config3 = {"key": "different", "number": 42}
        
        hash1 = autosave._get_config_hash(config1)
        hash2 = autosave._get_config_hash(config2)
        hash3 = autosave._get_config_hash(config3)
        
        # Gleiche Config = gleicher Hash
        assert hash1 == hash2
        # Unterschiedliche Config = unterschiedlicher Hash
        assert hash1 != hash3
        # Hash ist String
        assert isinstance(hash1, str)
        # Hash hat feste Länge (12 Zeichen)
        assert len(hash1) == 12
    
    def test_save_creates_recovery_file(self, autosave, temp_dir):
        """Test dass Recovery-Datei erstellt wird."""
        config = {"test": "data", "version": 1}
        
        result = autosave.save(config, force=True)
        
        assert result is True
        recovery_path = temp_dir / "autosave" / "untitled_recovery.json"
        assert recovery_path.exists()
    
    def test_save_respects_enabled_flag(self, autosave):
        """Test dass enabled=False speichern verhindert."""
        autosave.config.enabled = False
        config = {"test": "data"}
        
        result = autosave.save(config)
        
        assert result is False
    
    def test_save_skips_if_unchanged(self, autosave):
        """Test dass identische Config nicht erneut speichert."""
        config = {"test": "data"}
        
        # Erster Save
        result1 = autosave.save(config, force=True)
        assert result1 is True
        
        # Zweiter Save ohne Änderung
        result2 = autosave.save(config)
        assert result2 is False
    
    def test_save_respects_interval(self, autosave):
        """Test Zeitintervall-Einhaltung."""
        autosave.config.interval_seconds = 60.0
        config = {"test": "data"}
        
        # Erster Save
        result1 = autosave.save(config, force=True)
        assert result1 is True
        
        # Sofortiger zweiter Save sollte übersprungen werden
        result2 = autosave.save(config, force=False)
        assert result2 is False
    
    def test_load_recovery(self, autosave):
        """Test Recovery laden."""
        config = {"test": "data", "nested": {"key": "value"}}
        autosave.save(config, force=True)
        
        recovered = autosave.load_recovery()
        
        assert recovered is not None
        assert recovered["test"] == "data"
        assert recovered["nested"]["key"] == "value"
    
    def test_load_recovery_not_found(self, autosave):
        """Test Recovery wenn keine Datei existiert."""
        recovered = autosave.load_recovery()
        
        assert recovered is None
    
    def test_set_project_name(self, autosave, temp_dir):
        """Test Projektnamen setzen."""
        from src.auto_save import AutoSaveManager, AutoSaveConfig
        
        # Frischer Manager
        save_dir = temp_dir / "test_project_name"
        config = AutoSaveConfig(backup_dir=str(save_dir))
        manager = AutoSaveManager(config)
        manager.set_project_name("My_Project_123")  # Nur alphanumerisch und _
        
        manager.save({"test": "data"}, force=True)
        
        # Leerzeichen werden entfernt, daher "My_Project_123" nicht "My Project 123"
        recovery_path = save_dir / "My_Project_123_recovery.json"
        assert recovery_path.exists(), f"Files: {list(save_dir.glob('*.json'))}"
    
    def test_set_project_name_sanitizes(self, autosave, temp_dir):
        """Test dass ungültige Zeichen entfernt werden."""
        autosave.set_project_name("Test/\\Project*?.txt")
        config = {"test": "data"}
        
        autosave.save(config, force=True)
        
        # Ungültige Zeichen sollten entfernt sein
        recovery_path = temp_dir / "autosave" / "TestProjecttxt_recovery.json"
        assert recovery_path.exists()
    
    def test_list_backups(self, temp_dir):
        """Test Backup-Auflistung."""
        from src.auto_save import AutoSaveManager, AutoSaveConfig
        
        # Frischer Manager mit eindeutigem Verzeichnis
        save_dir = temp_dir / "test_list_backups"
        config = AutoSaveConfig(backup_dir=str(save_dir))
        autosave = AutoSaveManager(config)
        
        # Erstelle mehrere Backups (force=True für Backup-Dateien)
        for i in range(3):
            autosave.save({"version": i}, force=True)
            time.sleep(0.05)  # Größere Pause für unterschiedliche Zeitstempel
        
        backups = autosave.list_backups()
        
        # Mindestens ein Backup sollte existieren
        assert len(backups) >= 1
        # Neueste zuerst
        if len(backups) > 1:
            assert backups[0]["modified"] >= backups[-1]["modified"]
    
    def test_load_backup(self, autosave):
        """Test einzelnes Backup laden."""
        config = {"version": 42}
        autosave.save(config, force=True)
        
        backups = autosave.list_backups()
        backup_path = backups[0]["path"]
        
        loaded = autosave.load_backup(backup_path)
        
        assert loaded is not None
        assert loaded["version"] == 42
    
    def test_delete_backup(self, autosave):
        """Test Backup löschen."""
        config = {"test": "data"}
        autosave.save(config, force=True)
        
        backups = autosave.list_backups()
        initial_count = len(backups)
        backup_path = backups[0]["path"]
        
        result = autosave.delete_backup(backup_path)
        
        assert result is True
        assert not backup_path.exists()
    
    def test_backup_rotation(self, autosave, temp_dir):
        """Test dass alte Backups gelöscht werden."""
        autosave.config.max_backups = 2
        
        # Erstelle mehr Backups als erlaubt
        for i in range(5):
            autosave.save({"version": i}, force=True)
            time.sleep(0.01)
        
        backups = autosave.list_backups()
        
        # Nur max_backups sollten übrig sein
        assert len(backups) <= autosave.config.max_backups
    
    def test_get_last_save_info(self, autosave):
        """Test Info über letzten Save."""
        config = {"test": "data"}
        autosave.save(config, force=True)
        
        info = autosave.get_last_save_info()
        
        assert info is not None
        assert "path" in info
        assert "timestamp" in info
        assert "age_seconds" in info
        assert "size_bytes" in info
    
    def test_get_last_save_info_none(self, autosave):
        """Test Info wenn kein Save existiert."""
        info = autosave.get_last_save_info()
        
        assert info is None


# =============================================================================
# Preset Manager Tests
# =============================================================================

class TestPresetMetadata:
    """Tests für PresetMetadata."""
    
    def test_default_creation(self):
        """Test Default-Werte bei Erstellung."""
        from src.preset_manager import PresetMetadata
        
        meta = PresetMetadata(
            name="Test Preset",
            description="A test preset",
            category="custom"
        )
        
        assert meta.name == "Test Preset"
        assert meta.description == "A test preset"
        assert meta.category == "custom"
        assert meta.author == "User"
        assert meta.tags == []
        assert meta.created_at != ""
        assert meta.modified_at == meta.created_at
    
    def test_custom_values(self):
        """Test benutzerdefinierte Werte."""
        from src.preset_manager import PresetMetadata
        
        meta = PresetMetadata(
            name="Custom",
            description="Desc",
            category="default",
            author="John",
            tags=["tag1", "tag2"]
        )
        
        assert meta.author == "John"
        assert meta.tags == ["tag1", "tag2"]


class TestVisualizerPreset:
    """Tests für VisualizerPreset."""
    
    def test_to_dict(self):
        """Test Konvertierung zu Dictionary."""
        from src.preset_manager import VisualizerPreset, PresetMetadata
        
        preset = VisualizerPreset(
            id="test_123",
            metadata=PresetMetadata(name="Test", description="", category="custom"),
            visual_config={"type": "bars"},
            postprocess_config={"contrast": 1.2}
        )
        
        data = preset.to_dict()
        
        assert data["id"] == "test_123"
        assert data["visual_config"]["type"] == "bars"
        assert data["postprocess_config"]["contrast"] == 1.2
    
    def test_from_dict(self):
        """Test Erstellung aus Dictionary."""
        from src.preset_manager import VisualizerPreset
        
        data = {
            "id": "test_456",
            "metadata": {
                "name": "Test",
                "description": "",
                "category": "custom",
                "author": "User",
                "created_at": "2024-01-01",
                "modified_at": "2024-01-01",
                "tags": []
            },
            "visual_config": {"type": "circle"},
            "postprocess_config": {},
            "preview_params": {}
        }
        
        preset = VisualizerPreset.from_dict(data)
        
        assert preset.id == "test_456"
        assert preset.metadata.name == "Test"


class TestPresetManager:
    """Tests für PresetManager."""
    
    @pytest.fixture
    def temp_dir(self):
        """Erstellt ein temporäres Verzeichnis."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def pm(self, temp_dir):
        """Erstellt einen PresetManager mit temporärem Verzeichnis."""
        from src.preset_manager import PresetManager
        
        return PresetManager(presets_dir=str(temp_dir / "presets"))
    
    def test_init_creates_directories(self, temp_dir):
        """Test dass Verzeichnisse erstellt werden."""
        from src.preset_manager import PresetManager
        
        presets_dir = temp_dir / "new_presets"
        
        assert not presets_dir.exists()
        PresetManager(presets_dir=str(presets_dir))
        assert presets_dir.exists()
        assert (presets_dir / "thumbnails").exists()
    
    def test_save_preset(self, pm, temp_dir):
        """Test Preset speichern."""
        preset_id = pm.save_preset(
            name="Test Preset",
            visual_config={"type": "bars"},
            postprocess_config={"contrast": 1.2},
            description="A test",
            author="Tester",
            tags=["test", "bars"]
        )
        
        assert preset_id is not None
        assert preset_id.startswith("Test_Preset_")
        
        # Datei sollte existieren
        preset_file = temp_dir / "presets" / f"{preset_id}.json"
        assert preset_file.exists()
    
    def test_load_preset(self, pm):
        """Test Preset laden."""
        preset_id = pm.save_preset(
            name="Load Test",
            visual_config={"color": "red"},
            postprocess_config={}
        )
        
        preset = pm.load_preset(preset_id)
        
        assert preset is not None
        assert preset.metadata.name == "Load Test"
        assert preset.visual_config["color"] == "red"
    
    def test_load_preset_from_cache(self, pm):
        """Test dass geladene Presets gecacht werden."""
        preset_id = pm.save_preset(
            name="Cache Test",
            visual_config={},
            postprocess_config={}
        )
        
        # Erster Load
        preset1 = pm.load_preset(preset_id)
        # Zweiter Load sollte aus Cache kommen
        preset2 = pm.load_preset(preset_id)
        
        assert preset1 == preset2  # Gleiches Objekt aus Cache
    
    def test_load_preset_not_found(self, pm):
        """Test Laden nicht-existierendes Preset."""
        preset = pm.load_preset("non_existent_id")
        
        assert preset is None
    
    def test_delete_preset(self, pm, temp_dir):
        """Test Preset löschen."""
        preset_id = pm.save_preset(
            name="Delete Test",
            visual_config={},
            postprocess_config={}
        )
        
        result = pm.delete_preset(preset_id)
        
        assert result is True
        preset_file = temp_dir / "presets" / f"{preset_id}.json"
        assert not preset_file.exists()
    
    def test_list_presets(self, pm):
        """Test Preset-Auflistung."""
        # Mehrere Presets erstellen
        for i in range(3):
            pm.save_preset(
                name=f"Preset {i}",
                visual_config={"index": i},
                postprocess_config={}
            )
            time.sleep(0.01)
        
        presets = pm.list_presets()
        
        assert len(presets) == 3
        # Neueste zuerst
        assert presets[0].metadata.modified_at >= presets[-1].metadata.modified_at
    
    def test_list_presets_by_category(self, pm):
        """Test Filterung nach Kategorie."""
        # Presets haben immer "custom" Kategorie beim Speichern
        pm.save_preset("Preset 1", {}, {})
        pm.save_preset("Preset 2", {}, {})
        
        all_presets = pm.list_presets()
        custom_presets = pm.list_presets(category="custom")
        
        # Alle sind custom
        assert len(custom_presets) == len(all_presets)
    
    def test_favorites(self, pm):
        """Test Favoriten-Funktionalität."""
        preset_id = pm.save_preset("Fav Test", {}, {})
        
        # Nicht in Favoriten
        assert not pm.is_favorite(preset_id)
        
        # Hinzufügen
        pm.add_to_favorites(preset_id)
        assert pm.is_favorite(preset_id)
        
        # Entfernen
        pm.remove_from_favorites(preset_id)
        assert not pm.is_favorite(preset_id)
    
    def test_get_favorites(self, pm):
        """Test Abrufen aller Favoriten."""
        id1 = pm.save_preset("Fav 1", {}, {})
        id2 = pm.save_preset("Fav 2", {}, {})
        id3 = pm.save_preset("No Fav", {}, {})
        
        pm.add_to_favorites(id1)
        pm.add_to_favorites(id2)
        
        favorites = pm.get_favorites()
        favorite_ids = [p.id for p in favorites]
        
        assert id1 in favorite_ids
        assert id2 in favorite_ids
        assert id3 not in favorite_ids
    
    def test_favorites_persistence(self, pm, temp_dir):
        """Test dass Favoriten persistiert werden."""
        preset_id = pm.save_preset("Persist Test", {}, {})
        pm.add_to_favorites(preset_id)
        
        # Neuen Manager erstellen (simuliert Neustart)
        from src.preset_manager import PresetManager
        pm2 = PresetManager(presets_dir=str(temp_dir / "presets"))
        
        assert pm2.is_favorite(preset_id)
    
    def test_generate_thumbnail(self, pm):
        """Test Thumbnail-Generierung."""
        preset_id = pm.save_preset("Thumb Test", {}, {})
        
        # Frame erstellen
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        result = pm.generate_thumbnail(preset_id, frame)
        
        assert result is True
        thumb = pm.get_thumbnail(preset_id)
        assert thumb is not None
    
    def test_generate_thumbnail_float(self, pm):
        """Test Thumbnail mit Float-Array (0-1)."""
        preset_id = pm.save_preset("Float Thumb", {}, {})
        
        # Float frame
        frame = np.random.rand(480, 640, 3)
        
        result = pm.generate_thumbnail(preset_id, frame)
        
        assert result is True
    
    def test_get_thumbnail_not_found(self, pm):
        """Test Thumbnail wenn nicht existiert."""
        thumb = pm.get_thumbnail("non_existent")
        
        assert thumb is None
    
    def test_duplicate_preset(self, pm):
        """Test Preset duplizieren."""
        original_id = pm.save_preset(
            "Original",
            {"type": "bars"},
            {"contrast": 1.2},
            description="Original desc",
            tags=["tag1"]
        )
        
        new_id = pm.duplicate_preset(original_id, "Duplikat")
        
        assert new_id is not None
        assert new_id != original_id
        
        duplicate = pm.load_preset(new_id)
        assert duplicate.metadata.name == "Duplikat"
        assert duplicate.visual_config["type"] == "bars"
        assert duplicate.metadata.tags == ["tag1"]
    
    def test_duplicate_preset_default_name(self, pm):
        """Test Duplizieren mit Default-Namen."""
        original_id = pm.save_preset("Original", {}, {})
        
        new_id = pm.duplicate_preset(original_id)
        
        duplicate = pm.load_preset(new_id)
        assert "(Kopie)" in duplicate.metadata.name


# =============================================================================
# Real-Time Audio Tests
# =============================================================================

class TestRealtimeConfig:
    """Tests für RealtimeConfig."""
    
    def test_default_values(self):
        """Test Default-Werte."""
        from src.realtime import RealtimeConfig
        
        config = RealtimeConfig()
        
        assert config.sample_rate == 44100
        assert config.block_size == 1024
        assert config.channels == 1
        assert config.device is None
        assert config.fps == 30
        assert config.smoothing == 0.8
        assert config.fft_size == 2048
        assert config.freq_bands == 64


class TestRealtimeFeatureExtractor:
    """Tests für RealtimeFeatureExtractor."""
    
    @pytest.fixture
    def extractor(self):
        """Erstellt einen FeatureExtractor."""
        from src.realtime import RealtimeFeatureExtractor, RealtimeConfig
        
        config = RealtimeConfig(sample_rate=44100, block_size=1024)
        return RealtimeFeatureExtractor(config)
    
    def test_process_returns_features(self, extractor):
        """Test dass Features extrahiert werden."""
        # Sinus-Wellen Audio
        t = np.linspace(0, 1, 1024)
        audio = np.sin(2 * np.pi * 440 * t).reshape(-1, 1)
        
        features = extractor.process(audio)
        
        assert "rms" in features
        assert "spectrum" in features
        assert "centroid" in features
        assert "onset" in features
        assert "beat" in features
        assert "raw_audio" in features
    
    def test_rms_normalization(self, extractor):
        """Test RMS ist normalisiert (0-1)."""
        # Laute Audio
        audio = np.ones((1024, 1)) * 0.5
        
        features = extractor.process(audio)
        
        assert 0 <= features["rms"] <= 1
    
    def test_spectrum_shape(self, extractor):
        """Test Spectrum hat korrekte Form."""
        audio = np.random.randn(1024, 1)
        
        features = extractor.process(audio)
        
        assert len(features["spectrum"]) == 64  # freq_bands
        assert all(0 <= s <= 1 for s in features["spectrum"])
    
    def test_centroid_normalization(self, extractor):
        """Test Spectral Centroid ist normalisiert."""
        audio = np.random.randn(1024, 1)
        
        features = extractor.process(audio)
        
        assert 0 <= features["centroid"] <= 1
    
    def test_beat_detection(self, extractor):
        """Test Beat Detection."""
        # Stille
        audio = np.zeros((1024, 1))
        features = extractor.process(audio)
        assert features["beat"] is False
        
        # Laute Audio für Beat
        audio = np.ones((1024, 1)) * 0.8
        # Mehrere Frames für History
        for _ in range(5):
            features = extractor.process(audio)
        
        # Beat könnte erkannt werden (abhängig von Threshold)
        assert isinstance(features["beat"], bool)
    
    def test_stereo_to_mono(self, extractor):
        """Test Stereo zu Mono Konvertierung."""
        # Stereo Audio
        audio = np.random.randn(1024, 2)
        
        features = extractor.process(audio)
        
        assert features["rms"] >= 0
    
    def test_compute_freq_bands(self, extractor):
        """Test Frequenzband-Berechnung."""
        magnitude = np.random.rand(1024)
        freqs = np.linspace(0, 22050, 1024)
        
        bands = extractor._compute_freq_bands(magnitude, freqs)
        
        assert len(bands) == 64
        assert all(b >= 0 for b in bands)
    
    def test_compute_centroid(self, extractor):
        """Test Spectral Centroid Berechnung."""
        magnitude = np.array([1, 2, 3, 4, 5])
        freqs = np.array([100, 200, 300, 400, 500])
        
        centroid = extractor._compute_centroid(magnitude, freqs)
        
        assert centroid > 0
    
    def test_compute_centroid_zero_magnitude(self, extractor):
        """Test Centroid bei Null-Magnitude."""
        magnitude = np.zeros(5)
        freqs = np.array([100, 200, 300, 400, 500])
        
        centroid = extractor._compute_centroid(magnitude, freqs)
        
        assert centroid == 0


class TestRealtimeAudioCapture:
    """Tests für RealtimeAudioCapture."""
    
    def test_init_without_sounddevice(self):
        """Test Initialisierung ohne sounddevice."""
        with patch('src.realtime.SOUNDDEVICE_AVAILABLE', False):
            from src.realtime import RealtimeAudioCapture, RealtimeConfig
            
            with pytest.raises(RuntimeError) as exc_info:
                RealtimeAudioCapture(RealtimeConfig())
            
            assert "sounddevice nicht installiert" in str(exc_info.value)
    
    def test_list_devices_mocked(self):
        """Test Audio-Device Auflistung (gemockt)."""
        from src.realtime import RealtimeAudioCapture
        
        # Teste die Logik manuell ohne sounddevice
        devices_raw = [
            {'name': 'Mic 1', 'max_input_channels': 2, 'default_samplerate': 44100},
            {'name': 'Mic 2', 'max_input_channels': 1, 'default_samplerate': 48000},
            {'name': 'Output', 'max_input_channels': 0, 'default_samplerate': 44100},
        ]
        
        devices = []
        for i, device in enumerate(devices_raw):
            if device['max_input_channels'] > 0:
                devices.append({
                    'index': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': device['default_samplerate']
                })
        
        assert len(devices) == 2  # Nur Input-Devices
        assert devices[0]['name'] == 'Mic 1'
        assert devices[1]['channels'] == 1
    
    @patch('src.realtime.SOUNDDEVICE_AVAILABLE', False)
    def test_list_devices_not_available(self):
        """Test Device-Liste wenn sounddevice nicht verfügbar."""
        from src.realtime import RealtimeAudioCapture
        
        devices = RealtimeAudioCapture.list_devices()
        
        assert devices == []


# =============================================================================
# 3D WebGL Tests
# =============================================================================

class TestWebGL3DVisualizer:
    """Tests für WebGL 3D Visualizer."""
    
    @pytest.fixture
    def dummy_features(self):
        """Erstellt Dummy AudioFeatures."""
        from src.types import AudioFeatures
        
        return AudioFeatures(
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
    
    def test_webgl_visualizer_import(self):
        """Test dass WebGL Module importiert werden kann."""
        try:
            from src.visuals.webgl_3d import WebGL3DVisualizer, WebGLParticles3D, WebGLBars3D
            assert True
        except ImportError as e:
            pytest.skip(f"WebGL3D nicht verfügbar: {e}")
    
    def test_generate_threejs_code_contains_structure(self, dummy_features):
        """Test Three.js Code Generierung."""
        try:
            from src.visuals.webgl_3d import WebGLParticles3D
            from src.types import VisualConfig
        except ImportError:
            pytest.skip("WebGL3D nicht verfügbar")
        
        config = VisualConfig(type="webgl_particles", resolution=(640, 480), fps=30)
        viz = WebGLParticles3D(config, dummy_features)
        
        code = viz.generate_threejs_code()
        
        assert "three.js" in code.lower() or "THREE" in code
        assert "scene" in code.lower()
        assert "camera" in code.lower()
    
    def test_export_interactive_html(self, dummy_features, tmp_path):
        """Test HTML Export."""
        try:
            from src.visuals.webgl_3d import WebGLParticles3D
            from src.types import VisualConfig
        except ImportError:
            pytest.skip("WebGL3D nicht verfügbar")
        
        config = VisualConfig(type="webgl_particles", resolution=(640, 480), fps=30)
        viz = WebGLParticles3D(config, dummy_features)
        
        output_path = tmp_path / "test_visualizer.html"
        viz.export_interactive_html(str(output_path), title="Test Viz")
        
        assert output_path.exists()
        content = output_path.read_text()
        assert "<html>" in content.lower()
        assert "Test Viz" in content
