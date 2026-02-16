"""
test_visuals.py - Tests für alle Visualizer

Sicherstellt, dass alle Visualizer gültige Numpy-Arrays zurückgeben.
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# Füge src zum Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.visuals.registry import VisualizerRegistry
from src.types import AudioFeatures, VisualConfig


@pytest.fixture
def dummy_features():
    """Minimal Features für schnelle Tests."""
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


@pytest.fixture
def dummy_config():
    return VisualConfig(
        type="test",
        resolution=(640, 480),
        fps=30,
        colors={"primary": "#FF0000", "secondary": "#00FF00", "background": "#000000"}
    )


def test_all_visualizers(dummy_features, dummy_config):
    """Testet dass alle Visualizer gültige Numpy-Arrays zurückgeben."""
    VisualizerRegistry.autoload()
    
    available = VisualizerRegistry.list_available()
    print(f"\nGefundene Visualizer: {available}")
    
    assert len(available) > 0, "Keine Visualizer gefunden!"
    
    for name in available:
        print(f"\nTesting {name}...")
        vis_class = VisualizerRegistry.get(name)
        
        # Erstelle Config für diesen Visualizer
        config = VisualConfig(
            type=name,
            resolution=dummy_config.resolution,
            fps=dummy_config.fps,
            colors=dummy_config.colors
        )
        
        visualizer = vis_class(config, dummy_features)
        visualizer.setup()
        
        # Teste 3 Frames
        for i in [0, 15, 29]:
            frame = visualizer.render_frame(i)
            
            # Validierungen
            assert isinstance(frame, np.ndarray), f"{name}: Frame ist kein numpy array"
            assert frame.shape == (480, 640, 3), f"{name}: Falsche Shape {frame.shape}"
            assert frame.dtype == np.uint8, f"{name}: Falsches dtype {frame.dtype}"
            assert frame.min() >= 0 and frame.max() <= 255, f"{name}: Werte außerhalb 0-255"
        
        print(f"  ✓ {name} bestanden")


def test_visualizer_registry():
    """Testet das Registry-System."""
    VisualizerRegistry.autoload()
    
    available = VisualizerRegistry.list_available()
    print(f"\nVerfügbare Visualizer: {available}")
    
    # Sollte mindestens die 5 Standard-Visualizer haben
    expected = ['pulsing_core', 'spectrum_bars', 'chroma_field', 'particle_swarm', 'typographic']
    for vis in expected:
        assert vis in available, f"Visualizer '{vis}' nicht gefunden!"


def test_get_feature_at_frame(dummy_features, dummy_config):
    """Testet die get_feature_at_frame Hilfsmethode."""
    VisualizerRegistry.autoload()
    
    vis_class = VisualizerRegistry.get('pulsing_core')
    config = VisualConfig(
        type='pulsing_core',
        resolution=(640, 480),
        fps=30,
        colors={"primary": "#FF0000"}
    )
    
    visualizer = vis_class(config, dummy_features)
    visualizer.setup()
    
    # Teste Feature-Extraktion
    f = visualizer.get_feature_at_frame(15)
    
    assert 'rms' in f
    assert 'onset' in f
    assert 'chroma' in f
    assert 'progress' in f
    
    assert 0 <= f['rms'] <= 1
    assert 0 <= f['onset'] <= 1
    assert 0 <= f['progress'] <= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
