"""
VisualizerRegistry - Automatisches Plugin-Loading

Ermöglicht die Registrierung neuer Visualizer über einen Decorator.
"""

import importlib
import pkgutil
from typing import Dict, Type
from .base import BaseVisualizer


class VisualizerRegistry:
    """Automatisches Laden aller Visualizer aus dem visuals-Paket."""
    
    _plugins: Dict[str, Type[BaseVisualizer]] = {}
    
    @classmethod
    def register(cls, name: str):
        """Decorator für neue Visualizer."""
        def decorator(visualizer_class: Type[BaseVisualizer]):
            cls._plugins[name] = visualizer_class
            return visualizer_class
        return decorator
    
    @classmethod
    def get(cls, name: str) -> Type[BaseVisualizer]:
        if name not in cls._plugins:
            raise ValueError(f"Unbekannter Visualizer: {name}. Verfügbar: {list(cls._plugins.keys())}")
        return cls._plugins[name]
    
    @classmethod
    def list_available(cls):
        return list(cls._plugins.keys())
    
    @classmethod
    def autoload(cls):
        """Lädt alle Module im visuals-Paket."""
        from . import __path__ as visuals_path
        for _, name, _ in pkgutil.iter_modules(visuals_path):
            try:
                importlib.import_module(f"src.visuals.{name}")
            except Exception as e:
                print(f"[Registry] Warnung: Konnte {name} nicht laden: {e}")


# Decorator-Export für einfache Verwendung
register_visualizer = VisualizerRegistry.register
