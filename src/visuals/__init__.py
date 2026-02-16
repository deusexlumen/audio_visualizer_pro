"""
Visuals Plugin-System

Automatisches Laden und Registrieren von Visualizer-Plugins.
"""

from .base import BaseVisualizer
from .registry import VisualizerRegistry, register_visualizer

__all__ = ['BaseVisualizer', 'VisualizerRegistry', 'register_visualizer']
