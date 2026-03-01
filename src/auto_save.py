"""
Auto-Save System für Projekt-Konfigurationen

Speichert automatisch alle Änderungen im Hintergrund.
"""

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

import streamlit as st

from .logger import get_logger

logger = get_logger("audio_visualizer.autosave")


@dataclass
class AutoSaveConfig:
    """Konfiguration für Auto-Save."""

    interval_seconds: float = 30.0
    max_backups: int = 5
    backup_dir: str = ".cache/autosave"
    enabled: bool = True


class AutoSaveManager:
    """
    Automatisches Speichern von Projekt-Konfigurationen.

    Features:
    - Automatisches Speichern alle N Sekunden
    - Backup-Rotation (älteste werden gelöscht)
    - Recovery nach Crash
    - Manuelles Speichern/Laden

    Usage:
        autosave = AutoSaveManager()
        autosave.start(project_config)

        # In der GUI:
        autosave.check_and_save(current_config)
    """

    def __init__(self, config: Optional[AutoSaveConfig] = None):
        self.config = config or AutoSaveConfig()
        self._last_save_time: float = 0
        self._last_config_hash: Optional[str] = None
        self._current_project_name: str = "untitled"
        self._backup_dir = Path(self.config.backup_dir)
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def _get_config_hash(self, config: dict) -> str:
        """Berechnet einen Hash für die Config (für Change-Detection)."""
        import hashlib

        config_str = json.dumps(config, sort_keys=True, default=str)
        return hashlib.md5(config_str.encode()).hexdigest()[:12]

    def _get_backup_path(self, timestamp: Optional[str] = None) -> Path:
        """Generiert den Pfad für eine Backup-Datei."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self._current_project_name}_{timestamp}.json"
        return self._backup_dir / filename

    def _get_recovery_path(self) -> Path:
        """Pfad für die Recovery-Datei (letzter Stand)."""
        return self._backup_dir / f"{self._current_project_name}_recovery.json"

    def save(self, config: dict, force: bool = False) -> bool:
        """
        Speichert die Konfiguration.

        Args:
            config: Zu speichernde Konfiguration
            force: True = sofort speichern, False = nur wenn nötig

        Returns:
            True wenn gespeichert wurde
        """
        if not self.config.enabled:
            return False

        current_time = time.time()
        current_hash = self._get_config_hash(config)

        # Prüfe ob sich etwas geändert hat
        if not force and current_hash == self._last_config_hash:
            return False

        # Prüfe Zeitintervall
        if (
            not force
            and (current_time - self._last_save_time) < self.config.interval_seconds
        ):
            return False

        try:
            # Speichere Recovery-Version
            recovery_path = self._get_recovery_path()
            with open(recovery_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "config": config,
                        "timestamp": datetime.now().isoformat(),
                        "project_name": self._current_project_name,
                        "version": "1.0",
                    },
                    f,
                    indent=2,
                    default=str,
                )

            # Speichere Backup-Version (nur alle 5 Minuten oder bei force)
            if force or (current_time - self._last_save_time) > 300:
                backup_path = self._get_backup_path()
                with open(backup_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, default=str)

                # Rotiere alte Backups
                self._rotate_backups()

            self._last_save_time = current_time
            self._last_config_hash = current_hash

            logger.debug(f"💾 Auto-saved: {recovery_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Auto-save fehlgeschlagen: {e}")
            return False

    def _rotate_backups(self):
        """Löscht alte Backups, behält nur die neuesten N."""
        try:
            backups = sorted(
                self._backup_dir.glob(f"{self._current_project_name}_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            # Entferne Recovery-Datei aus der Liste
            backups = [b for b in backups if "recovery" not in b.name]

            # Lösche alte Backups
            for old_backup in backups[self.config.max_backups :]:
                old_backup.unlink()
                logger.debug(f"🗑️ Altes Backup gelöscht: {old_backup}")

        except Exception as e:
            logger.warning(f"Backup-Rotation fehlgeschlagen: {e}")

    def load_recovery(self) -> Optional[dict]:
        """Lädt die Recovery-Datei (letzter Stand vor Crash)."""
        recovery_path = self._get_recovery_path()

        if not recovery_path.exists():
            return None

        try:
            with open(recovery_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            logger.info(f"📂 Recovery geladen: {recovery_path}")
            return data.get("config")

        except Exception as e:
            logger.error(f"❌ Recovery fehlgeschlagen: {e}")
            return None

    def list_backups(self) -> list:
        """Listet alle verfügbaren Backups auf."""
        try:
            backups = []
            for path in self._backup_dir.glob(f"{self._current_project_name}_*.json"):
                if "recovery" not in path.name:
                    stat = path.stat()
                    backups.append(
                        {
                            "path": path,
                            "name": path.name,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime),
                            "age_hours": (time.time() - stat.st_mtime) / 3600,
                        }
                    )

            return sorted(backups, key=lambda b: b["modified"], reverse=True)

        except Exception as e:
            logger.error(f"Backup-Liste fehlgeschlagen: {e}")
            return []

    def load_backup(self, backup_path: Path) -> Optional[dict]:
        """Lädt ein spezifisches Backup."""
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Backup laden fehlgeschlagen: {e}")
            return None

    def delete_backup(self, backup_path: Path) -> bool:
        """Löscht ein Backup."""
        try:
            backup_path.unlink()
            return True
        except Exception as e:
            logger.error(f"❌ Backup löschen fehlgeschlagen: {e}")
            return False

    def set_project_name(self, name: str):
        """Setzt den Projektnamen (für Dateinamen)."""
        # Sanitize filename
        safe_name = "".join(c for c in name if c.isalnum() or c in ("-", "_")).rstrip()
        safe_name = safe_name or "untitled"
        self._current_project_name = safe_name

    def get_last_save_info(self) -> Optional[dict]:
        """Gibt Informationen über den letzten Save zurück."""
        recovery_path = self._get_recovery_path()

        if not recovery_path.exists():
            return None

        try:
            stat = recovery_path.stat()
            return {
                "path": recovery_path,
                "timestamp": datetime.fromtimestamp(stat.st_mtime),
                "age_seconds": time.time() - stat.st_mtime,
                "size_bytes": stat.st_size,
            }
        except Exception:
            return None


class AutoSaveUI:
    """
    UI-Komponenten für Auto-Save in Streamlit.
    """

    @staticmethod
    def render_status(autosave: AutoSaveManager):
        """Rendert den Auto-Save Status in der Sidebar."""
        with st.sidebar:
            st.divider()

            info = autosave.get_last_save_info()

            if info:
                age_minutes = int(info["age_seconds"] / 60)

                if age_minutes < 1:
                    status = "🟢 Gerade gespeichert"
                elif age_minutes < 5:
                    status = f"🟢 Vor {age_minutes}m"
                else:
                    status = f"🟡 Vor {age_minutes}m"

                st.caption(f"💾 {status}")
            else:
                st.caption("⚪ Noch nicht gespeichert")

    @staticmethod
    def render_recovery_dialog(autosave: AutoSaveManager, on_recover: Callable):
        """Zeigt einen Recovery-Dialog nach Crash."""
        recovery = autosave.load_recovery()

        if recovery:
            with st.sidebar:
                st.warning("🔄 Wiederherstellung verfügbar")

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("Wiederherstellen", type="primary"):
                        on_recover(recovery)
                        st.success("✅ Wiederhergestellt!")

                with col2:
                    if st.button("Verwerfen"):
                        # Lösche Recovery
                        recovery_path = autosave._get_recovery_path()
                        if recovery_path.exists():
                            recovery_path.unlink()
                        st.rerun()

    @staticmethod
    def render_backup_manager(autosave: AutoSaveManager, on_load: Callable):
        """Rendert den Backup-Manager."""
        with st.expander("📁 Backup-Verwaltung"):
            backups = autosave.list_backups()

            if not backups:
                st.info("Keine Backups verfügbar")
                return

            st.write(f"**{len(backups)} Backups gefunden**")

            for backup in backups:
                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    age_text = (
                        f"{int(backup['age_hours'])}h"
                        if backup["age_hours"] < 24
                        else f"{int(backup['age_hours']/24)}d"
                    )
                    st.text(
                        f"{backup['modified'].strftime('%d.%m.%Y %H:%M')} ({age_text})"
                    )

                with col2:
                    if st.button("Laden", key=f"load_{backup['name']}"):
                        config = autosave.load_backup(backup["path"])
                        if config:
                            on_load(config)
                            st.success("✅ Geladen!")
                            st.rerun()

                with col3:
                    if st.button("🗑️", key=f"del_{backup['name']}"):
                        if autosave.delete_backup(backup["path"]):
                            st.success("🗑️ Gelöscht!")
                            st.rerun()


def init_auto_save(config: Optional[AutoSaveConfig] = None) -> AutoSaveManager:
    """Initialisiert den Auto-Save Manager."""
    if "autosave_manager" not in st.session_state:
        st.session_state.autosave_manager = AutoSaveManager(config)

    return st.session_state.autosave_manager
