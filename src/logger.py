"""
Logging-Konfiguration für Audio Visualizer Pro.

Zentrales Logging-Setup mit farbiger Konsolenausgabe und optionaler Datei-Logging.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Farbiger Formatter für Konsolenausgabe."""
    
    # ANSI Farbcodes
    GREY = "\x1b[38;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    CYAN = "\x1b[36;20m"
    GREEN = "\x1b[32;20m"
    RESET = "\x1b[0m"
    
    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    FORMATS = {
        logging.DEBUG: GREY + FORMAT + RESET,
        logging.INFO: CYAN + "%(message)s" + RESET,  # Cleanere Info-Ausgabe
        logging.WARNING: YELLOW + FORMAT + RESET,
        logging.ERROR: RED + FORMAT + RESET,
        logging.CRITICAL: BOLD_RED + FORMAT + RESET
    }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    module_name: str = "audio_visualizer"
) -> logging.Logger:
    """
    Richtet das Logging ein.
    
    Args:
        level: Logging-Level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optionaler Pfad für Log-Datei
        module_name: Name des Loggers
    
    Returns:
        Konfigurierter Logger
    """
    logger = logging.getLogger(module_name)
    logger.setLevel(level)
    
    # Verhindere doppelte Handler
    if logger.handlers:
        return logger
    
    # Console Handler mit Farben
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)
    
    # Optional: File Handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


# Globaler Logger-Cache
_loggers = {}


def get_logger(name: str = "audio_visualizer") -> logging.Logger:
    """Gibt einen Logger zurück (Singleton pro Name)."""
    if name not in _loggers:
        # Lazy import um Zirkelabhängigkeit zu vermeiden
        try:
            from .settings import get_settings
            settings = get_settings()
            _loggers[name] = setup_logging(
                module_name=name,
                level=getattr(logging, settings.log_level.upper(), logging.INFO),
                log_file=settings.log_file
            )
        except ImportError:
            # Fallback wenn Settings noch nicht verfügbar
            _loggers[name] = setup_logging(module_name=name)
    return _loggers[name]
