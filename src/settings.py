"""
Settings-Management für Audio Visualizer Pro.

Zentrale Konfiguration via Umgebungsvariablen und .env-Dateien.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class Settings:
    """
    Anwendungs-Einstellungen.

    Werte können via Umgebungsvariablen oder .env-Datei überschrieben werden.
    """

    # Cache-Einstellungen
    cache_dir: Path = field(default_factory=lambda: Path(".cache/audio_features"))
    max_cache_size_gb: float = 10.0

    # Render-Einstellungen
    default_resolution: Tuple[int, int] = (1920, 1080)
    default_fps: int = 60
    default_preview_duration: float = 5.0
    preview_resolution: Tuple[int, int] = (854, 480)
    preview_fps: int = 30

    # Pfade
    temp_dir: Path = field(default_factory=lambda: Path(tempfile.gettempdir()))
    output_dir: Path = field(default_factory=lambda: Path("output"))

    # FFmpeg
    ffmpeg_preset: str = "medium"
    ffmpeg_crf: int = 23
    ffmpeg_audio_bitrate: str = "320k"

    # Logging
    log_level: str = "INFO"
    log_file: Optional[Path] = None

    # GUI
    gui_port: int = 8501
    gui_host: str = "localhost"

    def __post_init__(self):
        """Stellt sicher, dass alle Verzeichnisse existieren."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls, env_file: Optional[Path] = None) -> "Settings":
        """
        Lädt Settings aus Umgebungsvariablen und optionaler .env-Datei.

        Args:
            env_file: Pfad zur .env-Datei (default: .env im aktuellen Verzeichnis)

        Returns:
            Settings-Instanz mit geladenen Werten
        """
        # Lade .env-Datei wenn vorhanden
        if env_file is None:
            env_file = Path(".env")

        if env_file.exists():
            cls._load_dotenv(env_file)

        # Erstelle Settings mit Umgebungsvariablen
        return cls(
            cache_dir=Path(os.getenv("AV_CACHE_DIR", ".cache/audio_features")),
            max_cache_size_gb=float(os.getenv("AV_MAX_CACHE_SIZE_GB", "10")),
            default_resolution=cls._parse_resolution(
                os.getenv("AV_DEFAULT_RESOLUTION", "1920x1080")
            ),
            default_fps=int(os.getenv("AV_DEFAULT_FPS", "60")),
            default_preview_duration=float(os.getenv("AV_PREVIEW_DURATION", "5.0")),
            preview_resolution=cls._parse_resolution(
                os.getenv("AV_PREVIEW_RESOLUTION", "854x480")
            ),
            preview_fps=int(os.getenv("AV_PREVIEW_FPS", "30")),
            temp_dir=Path(os.getenv("AV_TEMP_DIR", tempfile.gettempdir())),
            output_dir=Path(os.getenv("AV_OUTPUT_DIR", "output")),
            ffmpeg_preset=os.getenv("AV_FFMPEG_PRESET", "medium"),
            ffmpeg_crf=int(os.getenv("AV_FFMPEG_CRF", "23")),
            ffmpeg_audio_bitrate=os.getenv("AV_FFMPEG_AUDIO_BITRATE", "320k"),
            log_level=os.getenv("AV_LOG_LEVEL", "INFO"),
            log_file=(
                Path(os.getenv("AV_LOG_FILE")) if os.getenv("AV_LOG_FILE") else None
            ),
            gui_port=int(os.getenv("AV_GUI_PORT", "8501")),
            gui_host=os.getenv("AV_GUI_HOST", "localhost"),
        )

    @staticmethod
    def _load_dotenv(env_file: Path):
        """Lädt Variablen aus einer .env-Datei."""
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip().strip("\"'")

    @staticmethod
    def _parse_resolution(res_str: str) -> Tuple[int, int]:
        """Parst '1920x1080' -> (1920, 1080)."""
        width, height = res_str.lower().split("x")
        return (int(width), int(height))

    def get_cache_size_mb(self) -> float:
        """Berechnet aktuelle Cache-Größe in MB."""
        if not self.cache_dir.exists():
            return 0.0

        total_size = sum(
            f.stat().st_size for f in self.cache_dir.rglob("*") if f.is_file()
        )
        return total_size / (1024 * 1024)

    def is_cache_full(self) -> bool:
        """Prüft ob Cache-Limit erreicht ist."""
        return self.get_cache_size_mb() > (self.max_cache_size_gb * 1024)

    def create_env_template(self, output_path: Path = Path(".env.example")):
        """Erstellt eine Beispiel-.env-Datei."""
        template = """# Audio Visualizer Pro - Konfiguration
# Kopiere diese Datei nach .env und passe die Werte an

# Cache-Einstellungen
AV_CACHE_DIR=.cache/audio_features
AV_MAX_CACHE_SIZE_GB=10

# Render-Einstellungen
AV_DEFAULT_RESOLUTION=1920x1080
AV_DEFAULT_FPS=60
AV_PREVIEW_DURATION=5.0
AV_PREVIEW_RESOLUTION=854x480
AV_PREVIEW_FPS=30

# Ausgabe
AV_OUTPUT_DIR=output
AV_TEMP_DIR=/tmp

# FFmpeg-Qualität (slower = bessere Qualität, langsamer)
# Presets: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
AV_FFMPEG_PRESET=medium
# CRF: 0-51 (0=lossless, 23=default, 51=worst)
AV_FFMPEG_CRF=23
AV_FFMPEG_AUDIO_BITRATE=320k

# Logging (DEBUG, INFO, WARNING, ERROR)
AV_LOG_LEVEL=INFO
# AV_LOG_FILE=logs/audio_visualizer.log

# GUI-Einstellungen
AV_GUI_PORT=8501
AV_GUI_HOST=localhost
"""
        output_path.write_text(template, encoding="utf-8")
        return output_path


# Globale Settings-Instanz (Lazy Loading)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Gibt die globale Settings-Instanz zurück."""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def reload_settings() -> Settings:
    """Lädt Settings neu (z.B. nach Änderung der .env-Datei)."""
    global _settings
    _settings = Settings.from_env()
    return _settings
