"""
Utility-Funktionen für Audio Visualizer Pro.

Hilfsfunktionen für System-Checks, Validierung und allgemeine Aufgaben.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Tuple
from .logger import get_logger

logger = get_logger("audio_visualizer.utils")


class FFmpegError(Exception):
    """Exception für FFmpeg-bezogene Fehler."""

    pass


class AudioValidationError(Exception):
    """Exception für ungültige Audio-Dateien."""

    pass


def check_ffmpeg() -> Tuple[bool, str]:
    """
    Prüft ob FFmpeg installiert ist und funktioniert.

    Returns:
        Tuple[bool, str]: (Erfolg, Version-String oder Fehlermeldung)
    """
    try:
        # Prüfe ob ffmpeg im PATH ist
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            return False, "FFmpeg nicht im PATH gefunden"

        # Führe ffmpeg -version aus
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True, timeout=10
        )

        if result.returncode != 0:
            return False, f"FFmpeg Fehler: {result.stderr}"

        # Extrahiere Version (erste Zeile)
        version_line = result.stdout.split("\n")[0]
        return True, version_line

    except subprocess.TimeoutExpired:
        return False, "FFmpeg-Check timed out"
    except FileNotFoundError:
        return False, "FFmpeg nicht gefunden"
    except Exception as e:
        return False, f"Unerwarteter Fehler: {e}"


def verify_ffmpeg_or_raise():
    """
    Prüft FFmpeg und wirft eine FFmpegError wenn nicht verfügbar.

    Raises:
        FFmpegError: Wenn FFmpeg nicht installiert oder nicht funktioniert
    """
    success, message = check_ffmpeg()

    if not success:
        error_msg = f"""
╔════════════════════════════════════════════════════════════════╗
║  FFmpeg nicht gefunden!                                         ║
╠════════════════════════════════════════════════════════════════╣
║  {message:<62} ║
║                                                                ║
║  Installation:                                                 ║
║  • Windows: https://ffmpeg.org/download.html                   ║
║  • macOS:   brew install ffmpeg                                ║
║  • Ubuntu:  sudo apt-get install ffmpeg                        ║
╚════════════════════════════════════════════════════════════════╝
"""
        logger.error(f"FFmpeg-Check fehlgeschlagen: {message}")
        raise FFmpegError(error_msg)

    logger.info(f"FFmpeg gefunden: {message}")


def validate_audio_file(audio_path: str) -> dict:
    """
    Validiert eine Audio-Datei.

    Args:
        audio_path: Pfad zur Audio-Datei

    Returns:
        Dictionary mit Audio-Informationen

    Raises:
        AudioValidationError: Wenn die Datei ungültig ist
    """
    path = Path(audio_path)

    # Prüfe ob Datei existiert
    if not path.exists():
        raise AudioValidationError(f"Datei nicht gefunden: {audio_path}")

    if not path.is_file():
        raise AudioValidationError(f"Pfad ist keine Datei: {audio_path}")

    # Prüfe Dateiendung
    valid_extensions = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"}
    if path.suffix.lower() not in valid_extensions:
        raise AudioValidationError(
            f"Ungültiges Format '{path.suffix}'. "
            f"Unterstützt: {', '.join(valid_extensions)}"
        )

    # Prüfe Dateigröße (max 2GB)
    file_size = path.stat().st_size
    max_size = 2 * 1024 * 1024 * 1024  # 2GB

    if file_size == 0:
        raise AudioValidationError("Datei ist leer")

    if file_size > max_size:
        raise AudioValidationError(
            f"Datei zu groß ({file_size / 1024 / 1024:.0f}MB). " f"Maximum: 2GB"
        )

    logger.debug(
        f"Audio-Datei validiert: {path.name} ({file_size / 1024 / 1024:.1f}MB)"
    )

    return {
        "path": str(path.absolute()),
        "name": path.name,
        "size_bytes": file_size,
        "extension": path.suffix.lower(),
    }


def get_cache_size(cache_dir: Path = Path(".cache")) -> Tuple[int, str]:
    """
    Berechnet die Größe des Cache-Verzeichnisses.

    Returns:
        Tuple[int, str]: (Größe in Bytes, formatierte Größe)
    """
    if not cache_dir.exists():
        return 0, "0 MB"

    total_size = 0
    for file_path in cache_dir.rglob("*"):
        if file_path.is_file():
            total_size += file_path.stat().st_size

    # Formatiere Größe
    if total_size < 1024:
        size_str = f"{total_size} B"
    elif total_size < 1024 * 1024:
        size_str = f"{total_size / 1024:.1f} KB"
    elif total_size < 1024 * 1024 * 1024:
        size_str = f"{total_size / 1024 / 1024:.1f} MB"
    else:
        size_str = f"{total_size / 1024 / 1024 / 1024:.2f} GB"

    return total_size, size_str


def clear_cache(cache_dir: Path = Path(".cache")) -> int:
    """
    Löscht den Cache.

    Returns:
        Anzahl der gelöschten Dateien
    """
    if not cache_dir.exists():
        return 0

    deleted_count = 0
    for file_path in cache_dir.rglob("*"):
        if file_path.is_file():
            try:
                file_path.unlink()
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Konnte Cache-Datei nicht löschen: {file_path} - {e}")

    logger.info(f"Cache geleert: {deleted_count} Dateien gelöscht")
    return deleted_count
