"""
VisualizerRegistry - Automatisches Plugin-Loading

Ermöglicht die Registrierung neuer Visualizer über einen Decorator.
"""

import importlib
import pkgutil
from typing import Dict, Type
from .base import BaseVisualizer
from ..logger import get_logger

logger = get_logger("audio_visualizer.registry")


class VisualizerRegistry:
    """
    Automatisches Laden und Verwalten aller Visualizer-Plugins.

    Ermöglicht die Registrierung neuer Visualizer über den @register_visualizer
    Decorator. Lädt automatisch alle Visualizer aus dem visuals-Paket.

    Usage:
        @register_visualizer("mein_visualizer")
        class MeinVisualizer(BaseVisualizer):
            ...

        # Später:
        viz_class = VisualizerRegistry.get("mein_visualizer")
    """

    _plugins: Dict[str, Type[BaseVisualizer]] = {}

    @classmethod
    def register(cls, name: str):
        """
        Decorator für neue Visualizer.

        Args:
            name: Eindeutiger Name für den Visualizer

        Returns:
            Decorator-Funktion die die Klasse registriert
        """

        def decorator(visualizer_class: Type[BaseVisualizer]):
            cls._plugins[name] = visualizer_class
            logger.debug(f"Visualizer registriert: {name}")
            return visualizer_class

        return decorator

    @classmethod
    def get(cls, name: str) -> Type[BaseVisualizer]:
        """
        Gibt eine Visualizer-Klasse zurück.

        Args:
            name: Name des registrierten Visualizers

        Returns:
            Die Visualizer-Klasse

        Raises:
            ValueError: Wenn der Visualizer nicht registriert ist
        """
        if name not in cls._plugins:
            raise ValueError(
                f"Unbekannter Visualizer: {name}. Verfügbar: {list(cls._plugins.keys())}"
            )
        return cls._plugins[name]

    @classmethod
    def list_available(cls) -> list:
        """
        Listet alle verfügbaren Visualizer auf.

        Returns:
            Liste der registrierten Visualizer-Namen
        """
        return list(cls._plugins.keys())

    @classmethod
    def autoload(cls):
        """
        Lädt alle Module im visuals-Paket automatisch.

        Durchsucht das visuals-Verzeichnis nach Python-Modulen und
        importiert diese, um alle @register_visualizer Decorators
        auszuführen.
        """
        from . import __path__ as visuals_path

        for _, name, _ in pkgutil.iter_modules(visuals_path):
            try:
                importlib.import_module(f"src.visuals.{name}")
            except Exception as e:
                logger.warning(f"Konnte Visualizer '{name}' nicht laden: {e}")


# Decorator-Export für einfache Verwendung
register_visualizer = VisualizerRegistry.register
