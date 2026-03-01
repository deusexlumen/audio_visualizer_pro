"""
Erweitertes Preset-System mit Favoriten, Custom Presets und Thumbnails

Features:
- Favoriten-Stern in GUI
- Custom User-Presets speichern/laden
- Thumbnail-Vorschau
- Import/Export von Presets
"""

import json
import hashlib
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any

import numpy as np
from PIL import Image
import streamlit as st

from .logger import get_logger

logger = get_logger("audio_visualizer.presets")


@dataclass
class PresetMetadata:
    """Metadaten für ein Preset."""

    name: str
    description: str
    category: str  # "default", "custom", "favorites"
    author: str = "User"
    created_at: str = ""
    modified_at: str = ""
    tags: List[str] = None
    thumbnail_path: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.modified_at:
            self.modified_at = self.created_at
        if self.tags is None:
            self.tags = []


@dataclass
class VisualizerPreset:
    """Ein komplettes Visualizer-Preset."""

    id: str
    metadata: PresetMetadata
    visual_config: Dict[str, Any]
    postprocess_config: Dict[str, Any]
    preview_params: Dict[str, Any] = None

    def to_dict(self) -> dict:
        """Konvertiert zu Dictionary."""
        return {
            "id": self.id,
            "metadata": asdict(self.metadata),
            "visual_config": self.visual_config,
            "postprocess_config": self.postprocess_config,
            "preview_params": self.preview_params or {},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VisualizerPreset":
        """Erstellt aus Dictionary."""
        return cls(
            id=data["id"],
            metadata=PresetMetadata(**data["metadata"]),
            visual_config=data["visual_config"],
            postprocess_config=data["postprocess_config"],
            preview_params=data.get("preview_params", {}),
        )


class PresetManager:
    """
    Verwaltet Visualizer-Presets mit Favoriten, Thumbnails und Import/Export.

    Usage:
        pm = PresetManager()

        # Preset speichern
        pm.save_preset("Mein Preset", visual_config, postprocess_config)

        # Favoriten verwalten
        pm.add_to_favorites("preset_id")

        # Thumbnail generieren
        pm.generate_thumbnail("preset_id", frame_array)

        # Export/Import
        pm.export_preset("preset_id", "/path/to/export.zip")
        pm.import_preset("/path/to/import.zip")
    """

    def __init__(self, presets_dir: Optional[str] = None):
        self.presets_dir = Path(presets_dir) if presets_dir else Path(".cache/presets")
        self.presets_dir.mkdir(parents=True, exist_ok=True)

        self.thumbnails_dir = self.presets_dir / "thumbnails"
        self.thumbnails_dir.mkdir(exist_ok=True)

        self.favorites_file = self.presets_dir / "favorites.json"
        self._favorites: List[str] = self._load_favorites()

        # Cache für geladene Presets
        self._preset_cache: Dict[str, VisualizerPreset] = {}

    def _load_favorites(self) -> List[str]:
        """Lädt Favoriten-Liste."""
        if self.favorites_file.exists():
            try:
                with open(self.favorites_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Favoriten laden fehlgeschlagen: {e}")
        return []

    def _save_favorites(self):
        """Speichert Favoriten-Liste."""
        try:
            with open(self.favorites_file, "w") as f:
                json.dump(self._favorites, f)
        except Exception as e:
            logger.error(f"Favoriten speichern fehlgeschlagen: {e}")

    def _generate_preset_id(self, name: str) -> str:
        """Generiert eine eindeutige ID für ein Preset."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_input = f"{name}_{timestamp}"
        hash_id = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"{self._sanitize_filename(name)}_{hash_id}"

    def _sanitize_filename(self, name: str) -> str:
        """Bereinigt einen Namen für Dateinamen."""
        return (
            "".join(c for c in name if c.isalnum() or c in ("-", "_", " "))
            .rstrip()
            .replace(" ", "_")[:30]
        )

    def _get_preset_path(self, preset_id: str) -> Path:
        """Pfad zu einer Preset-Datei."""
        return self.presets_dir / f"{preset_id}.json"

    def _get_thumbnail_path(self, preset_id: str) -> Path:
        """Pfad zu einem Thumbnail."""
        return self.thumbnails_dir / f"{preset_id}.png"

    def save_preset(
        self,
        name: str,
        visual_config: dict,
        postprocess_config: dict,
        description: str = "",
        author: str = "User",
        tags: List[str] = None,
        preview_params: dict = None,
    ) -> str:
        """
        Speichert ein neues Preset.

        Returns:
            Preset ID
        """
        preset_id = self._generate_preset_id(name)

        metadata = PresetMetadata(
            name=name,
            description=description,
            category="custom",
            author=author,
            tags=tags or [],
        )

        preset = VisualizerPreset(
            id=preset_id,
            metadata=metadata,
            visual_config=visual_config,
            postprocess_config=postprocess_config,
            preview_params=preview_params,
        )

        # Speichern
        preset_path = self._get_preset_path(preset_id)
        try:
            with open(preset_path, "w", encoding="utf-8") as f:
                json.dump(preset.to_dict(), f, indent=2, default=str)

            self._preset_cache[preset_id] = preset
            logger.info(f"Preset gespeichert: {name} ({preset_id})")
            return preset_id

        except Exception as e:
            logger.error(f"Preset speichern fehlgeschlagen: {e}")
            raise

    def load_preset(self, preset_id: str) -> Optional[VisualizerPreset]:
        """Lädt ein Preset."""
        # Cache check
        if preset_id in self._preset_cache:
            return self._preset_cache[preset_id]

        preset_path = self._get_preset_path(preset_id)
        if not preset_path.exists():
            return None

        try:
            with open(preset_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            preset = VisualizerPreset.from_dict(data)
            self._preset_cache[preset_id] = preset
            return preset

        except Exception as e:
            logger.error(f"Preset laden fehlgeschlagen: {e}")
            return None

    def delete_preset(self, preset_id: str) -> bool:
        """Löscht ein Preset."""
        try:
            # Lösche Preset-Datei
            preset_path = self._get_preset_path(preset_id)
            if preset_path.exists():
                preset_path.unlink()

            # Lösche Thumbnail
            thumb_path = self._get_thumbnail_path(preset_id)
            if thumb_path.exists():
                thumb_path.unlink()

            # Entferne aus Favoriten
            if preset_id in self._favorites:
                self._favorites.remove(preset_id)
                self._save_favorites()

            # Cache löschen
            if preset_id in self._preset_cache:
                del self._preset_cache[preset_id]

            logger.info(f"Preset gelöscht: {preset_id}")
            return True

        except Exception as e:
            logger.error(f"Preset löschen fehlgeschlagen: {e}")
            return False

    def list_presets(self, category: Optional[str] = None) -> List[VisualizerPreset]:
        """Listet alle Presets auf."""
        presets = []

        for preset_file in self.presets_dir.glob("*.json"):
            try:
                with open(preset_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                preset = VisualizerPreset.from_dict(data)

                # Kategorie-Filter
                if category and preset.metadata.category != category:
                    continue

                presets.append(preset)

            except Exception as e:
                logger.warning(f"Preset übersprungen {preset_file}: {e}")

        # Sortiere nach Modified-Datum (neueste zuerst)
        presets.sort(key=lambda p: p.metadata.modified_at, reverse=True)
        return presets

    def add_to_favorites(self, preset_id: str) -> bool:
        """Fügt ein Preset zu Favoriten hinzu."""
        if preset_id not in self._favorites:
            self._favorites.append(preset_id)
            self._save_favorites()
            logger.info(f"Zu Favoriten hinzugefügt: {preset_id}")
        return True

    def remove_from_favorites(self, preset_id: str) -> bool:
        """Entfernt ein Preset aus Favoriten."""
        if preset_id in self._favorites:
            self._favorites.remove(preset_id)
            self._save_favorites()
            logger.info(f"Aus Favoriten entfernt: {preset_id}")
        return True

    def is_favorite(self, preset_id: str) -> bool:
        """Prüft ob ein Preset ein Favorit ist."""
        return preset_id in self._favorites

    def get_favorites(self) -> List[VisualizerPreset]:
        """Gibt alle Favoriten-Presets zurück."""
        favorites = []
        for preset_id in self._favorites:
            preset = self.load_preset(preset_id)
            if preset:
                favorites.append(preset)
        return favorites

    def generate_thumbnail(self, preset_id: str, frame: np.ndarray) -> bool:
        """Generiert ein Thumbnail für ein Preset."""
        try:
            # Konvertiere zu PIL Image
            if frame.dtype != np.uint8:
                frame = (frame * 255).astype(np.uint8)

            img = Image.fromarray(frame)

            # Resize für Thumbnail (320x180)
            img.thumbnail((320, 180), Image.Resampling.LANCZOS)

            # Speichern
            thumb_path = self._get_thumbnail_path(preset_id)
            img.save(thumb_path, "PNG", optimize=True)

            # Update Preset
            preset = self.load_preset(preset_id)
            if preset:
                preset.metadata.thumbnail_path = str(thumb_path)
                self._update_preset(preset)

            logger.info(f"Thumbnail generiert: {preset_id}")
            return True

        except Exception as e:
            logger.error(f"Thumbnail-Generierung fehlgeschlagen: {e}")
            return False

    def get_thumbnail(self, preset_id: str) -> Optional[Image.Image]:
        """Lädt das Thumbnail eines Presets."""
        thumb_path = self._get_thumbnail_path(preset_id)
        if thumb_path.exists():
            try:
                return Image.open(thumb_path)
            except Exception as e:
                logger.warning(f"Thumbnail laden fehlgeschlagen: {e}")
        return None

    def _update_preset(self, preset: VisualizerPreset):
        """Aktualisiert ein bestehendes Preset."""
        preset.metadata.modified_at = datetime.now().isoformat()
        preset_path = self._get_preset_path(preset.id)

        with open(preset_path, "w", encoding="utf-8") as f:
            json.dump(preset.to_dict(), f, indent=2, default=str)

        self._preset_cache[preset.id] = preset

    def export_preset(self, preset_id: str, export_path: str) -> bool:
        """Exportiert ein Preset als ZIP."""
        import zipfile

        try:
            preset = self.load_preset(preset_id)
            if not preset:
                return False

            export_path = Path(export_path)

            with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Preset JSON
                preset_file = self._get_preset_path(preset_id)
                zf.write(preset_file, f"{preset_id}.json")

                # Thumbnail falls vorhanden
                thumb_file = self._get_thumbnail_path(preset_id)
                if thumb_file.exists():
                    zf.write(thumb_file, f"{preset_id}_thumbnail.png")

            logger.info(f"Preset exportiert: {export_path}")
            return True

        except Exception as e:
            logger.error(f"Export fehlgeschlagen: {e}")
            return False

    def import_preset(self, import_path: str) -> Optional[str]:
        """Importiert ein Preset aus ZIP."""
        import zipfile

        try:
            import_path = Path(import_path)

            with zipfile.ZipFile(import_path, "r") as zf:
                # Finde Preset JSON
                json_files = [f for f in zf.namelist() if f.endswith(".json")]
                if not json_files:
                    raise ValueError("Keine Preset-Datei im ZIP gefunden")

                # Extrahiere
                for file in zf.namelist():
                    if file.endswith(".json"):
                        dest = self.presets_dir / Path(file).name
                        with zf.open(file) as src:
                            with open(dest, "wb") as dst:
                                dst.write(src.read())
                    elif "thumbnail" in file:
                        dest = self.thumbnails_dir / Path(file).name
                        with zf.open(file) as src:
                            with open(dest, "wb") as dst:
                                dst.write(src.read())

                # Neue ID generieren um Kollisionen zu vermeiden
                preset_data = json.loads(zf.read(json_files[0]))
                old_id = preset_data["id"]
                new_id = self._generate_preset_id(preset_data["metadata"]["name"])

                # Update ID im File
                preset_data["id"] = new_id
                preset_data["metadata"]["category"] = "custom"
                preset_data["metadata"]["imported_at"] = datetime.now().isoformat()

                new_path = self._get_preset_path(new_id)
                with open(new_path, "w") as f:
                    json.dump(preset_data, f, indent=2)

                # Alte Datei löschen falls ID geändert
                old_path = self._get_preset_path(old_id)
                if old_path.exists() and old_path != new_path:
                    old_path.unlink()

                logger.info(f"Preset importiert: {new_id}")
                return new_id

        except Exception as e:
            logger.error(f"Import fehlgeschlagen: {e}")
            return None

    def duplicate_preset(
        self, preset_id: str, new_name: Optional[str] = None
    ) -> Optional[str]:
        """Dupliziert ein Preset."""
        preset = self.load_preset(preset_id)
        if not preset:
            return None

        # Neue ID und Name
        name = new_name or f"{preset.metadata.name} (Kopie)"
        new_id = self.save_preset(
            name=name,
            visual_config=preset.visual_config,
            postprocess_config=preset.postprocess_config,
            description=preset.metadata.description,
            author=preset.metadata.author,
            tags=preset.metadata.tags.copy(),
            preview_params=preset.preview_params,
        )

        # Thumbnail kopieren
        old_thumb = self._get_thumbnail_path(preset_id)
        if old_thumb.exists():
            new_thumb = self._get_thumbnail_path(new_id)
            shutil.copy2(old_thumb, new_thumb)

        return new_id


# UI Komponenten für Streamlit
class PresetUI:
    """UI-Komponenten für das Preset-System."""

    @staticmethod
    def render_preset_card(
        preset: VisualizerPreset,
        pm: PresetManager,
        on_load: Callable,
        on_delete: Callable,
        col_width: int = 4,
    ) -> bool:
        """Rendert eine Preset-Karte."""
        is_fav = pm.is_favorite(preset.id)

        with st.container():
            # Thumbnail oder Placeholder
            thumb = pm.get_thumbnail(preset.id)
            if thumb:
                st.image(thumb, use_container_width=True)
            else:
                st.markdown(
                    """
                <div style="
                    background: linear-gradient(135deg, #1a1a2e, #16213e);
                    height: 100px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 8px;
                    margin-bottom: 8px;
                ">
                    <span style="font-size: 2em;">🎨</span>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            # Titel und Favoriten-Stern
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{preset.metadata.name}**")
            with col2:
                fav_icon = "⭐" if is_fav else "☆"
                if st.button(fav_icon, key=f"fav_{preset.id}"):
                    if is_fav:
                        pm.remove_from_favorites(preset.id)
                    else:
                        pm.add_to_favorites(preset.id)
                    st.rerun()

            # Beschreibung
            if preset.metadata.description:
                st.caption(preset.metadata.description[:50] + "...")

            # Tags
            if preset.metadata.tags:
                st.markdown(" ".join([f"`{t}`" for t in preset.metadata.tags[:3]]))

            # Actions
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "📂 Laden", key=f"load_{preset.id}", use_container_width=True
                ):
                    on_load(preset)
            with col2:
                if st.button("🗑️", key=f"del_{preset.id}", use_container_width=True):
                    on_delete(preset.id)

        return True

    @staticmethod
    def render_preset_gallery(
        pm: PresetManager,
        on_load: Callable,
        on_delete: Callable,
        filter_favorites: bool = False,
        search_term: str = "",
    ):
        """Rendert eine Galerie von Presets."""
        if filter_favorites:
            presets = pm.get_favorites()
            st.markdown("### ⭐ Favoriten")
        else:
            presets = pm.list_presets()
            st.markdown("### 🎨 Alle Presets")

        # Filter
        if search_term:
            presets = [
                p
                for p in presets
                if search_term.lower() in p.metadata.name.lower()
                or search_term.lower() in p.metadata.description.lower()
            ]

        if not presets:
            st.info(
                "Keine Presets gefunden" + (" in Favoriten" if filter_favorites else "")
            )
            return

        # Grid-Layout
        cols = st.columns(3)
        for idx, preset in enumerate(presets):
            with cols[idx % 3]:
                PresetUI.render_preset_card(preset, pm, on_load, on_delete)

    @staticmethod
    def render_preset_editor(
        pm: PresetManager, preset: Optional[VisualizerPreset] = None
    ):
        """Rendert einen Editor für ein Preset."""
        st.markdown("### 💾 Preset Speichern")

        name = st.text_input("Name", value=preset.metadata.name if preset else "")
        description = st.text_area(
            "Beschreibung",
            value=preset.metadata.description if preset else "",
            max_chars=200,
        )
        tags = st.text_input(
            "Tags (komma-getrennt)",
            value=",".join(preset.metadata.tags) if preset else "",
        )

        return {
            "name": name,
            "description": description,
            "tags": [t.strip() for t in tags.split(",") if t.strip()],
        }


def init_preset_manager() -> PresetManager:
    """Initialisiert den Preset Manager."""
    if "preset_manager" not in st.session_state:
        st.session_state.preset_manager = PresetManager()
    return st.session_state.preset_manager
