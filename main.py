#!/usr/bin/env python3
"""
Audio Visualizer Pro - CLI Entry Point

KI-Optimierter Workflow für Audio-Visualisierungen.
"""

import click
import json
from pathlib import Path
from src.pipeline import RenderPipeline, PreviewPipeline
from src.types import ProjectConfig, VisualConfig


@click.group()
def cli():
    """Audio Visualizer Pro - KI-Optimierter Workflow"""
    pass


@cli.command()
@click.argument('audio_file', type=click.Path(exists=True))
@click.option('--visual', '-v', default='pulsing_core', 
              help='Visualisierungs-Typ (pulsing_core, spectrum_bars, chroma_field, particle_swarm, typographic)')
@click.option('--output', '-o', default='output.mp4')
@click.option('--config', '-c', type=click.Path(), help='JSON Config-File')
@click.option('--resolution', '-r', default='1920x1080')
@click.option('--fps', default=60, type=int)
@click.option('--preview', is_flag=True, help='Schnelle 5-Sekunden-Vorschau')
@click.option('--preview-duration', default=5.0, type=float, help='Dauer der Vorschau in Sekunden')
def render(audio_file, visual, output, config, resolution, fps, preview, preview_duration):
    """Rendert Audio-Visualisierung."""
    
    # Config aufbauen
    if config:
        with open(config) as f:
            cfg_dict = json.load(f)
        project_config = ProjectConfig(**cfg_dict)
    else:
        width, height = map(int, resolution.split('x'))
        project_config = ProjectConfig(
            audio_file=audio_file,
            output_file=output,
            visual=VisualConfig(
                type=visual,
                resolution=(width, height),
                fps=fps,
                colors={"primary": "#FF0055", "secondary": "#00CCFF", "background": "#0A0A0A"}
            )
        )
    
    # Pipeline starten
    if preview:
        pipeline = PreviewPipeline(project_config)
        pipeline.run(preview_mode=True, preview_duration=preview_duration)
    else:
        pipeline = RenderPipeline(project_config)
        pipeline.run(preview_mode=False)


@cli.command()
def list_visuals():
    """Zeigt alle verfügbaren Visualizer an."""
    from src.visuals.registry import VisualizerRegistry
    VisualizerRegistry.autoload()
    click.echo("Verfügbare Visualisierungen:")
    for name in VisualizerRegistry.list_available():
        click.echo(f"  - {name}")


@cli.command()
@click.argument('name')
def create_template(name):
    """
    Erstellt ein neues Visualizer-Template für KI-Agenten.
    Generiert: src/visuals/{name}.py mit Boilerplate.
    """
    template = f'''"""
{name}.py - Neue Visualisierung

TODO: Beschreibung hier einfügen
"""

import numpy as np
import colorsys
from PIL import Image, ImageDraw
from .base import BaseVisualizer
from .registry import register_visualizer


@register_visualizer("{name}")
class {name.title()}Visualizer(BaseVisualizer):
    """
    TODO: Beschreibung hier einfügen
    
    Kreativ-Ideen: 
    - Nutze self.features.chroma für Farben
    - Nutze self.features.rms für Skalierung
    - Nutze self.features.onset für Beat-Trigger
    """
    
    def setup(self):
        """Initialisierung hier."""
        self.center = (self.width // 2, self.height // 2)
    
    def render_frame(self, frame_idx: int) -> np.ndarray:
        """Rendert einen einzelnen Frame."""
        # Hintergrund
        bg_color = self.colors.get('background', (10, 10, 10, 255))
        img = Image.new('RGB', (self.width, self.height), bg_color[:3])
        draw = ImageDraw.Draw(img)
        
        # Features holen
        f = self.get_feature_at_frame(frame_idx)
        rms = f['rms']
        onset = f['onset']
        chroma = f['chroma']
        
        # TODO: Deine Zeichen-Logik hier
        # Beispiel: Text anzeigen
        draw.text(self.center, "Hello Audio", fill=(255, 255, 255))
        
        return np.array(img)
'''
    
    target = Path(f"src/visuals/{name}.py")
    if target.exists():
        click.echo(f"Fehler: {target} existiert bereits!")
        return
    
    target.write_text(template)
    click.echo(f"Template erstellt: {target}")
    click.echo(f"KI-Agent: Implementiere die render_frame() Methode!")


@cli.command()
@click.argument('audio_file', type=click.Path(exists=True))
def analyze(audio_file):
    """Analysiert eine Audio-Datei und zeigt Features an."""
    from src.analyzer import AudioAnalyzer
    
    analyzer = AudioAnalyzer()
    features = analyzer.analyze(audio_file, fps=60)
    
    click.echo("\n=== Audio-Analyse Ergebnisse ===")
    click.echo(f"Dauer: {features.duration:.2f}s")
    click.echo(f"Sample Rate: {features.sample_rate}Hz")
    click.echo(f"Tempo: {features.tempo:.1f} BPM")
    click.echo(f"Key: {features.key or 'Unbekannt'}")
    click.echo(f"Mode: {features.mode}")
    click.echo(f"Frames: {int(features.duration * features.fps)}")
    
    click.echo("\n=== Feature-Statistiken ===")
    click.echo(f"RMS: min={features.rms.min():.3f}, max={features.rms.max():.3f}, mean={features.rms.mean():.3f}")
    click.echo(f"Onset: min={features.onset.min():.3f}, max={features.onset.max():.3f}")
    click.echo(f"Spectral Centroid: mean={features.spectral_centroid.mean():.3f}")


@cli.command()
@click.option('--output', '-o', default='config_template.json')
def create_config(output):
    """Erstellt eine Beispiel-Konfigurationsdatei."""
    config = {
        "audio_file": "input.mp3",
        "output_file": "output.mp4",
        "visual": {
            "type": "pulsing_core",
            "resolution": [1920, 1080],
            "fps": 60,
            "colors": {
                "primary": "#FF0055",
                "secondary": "#00CCFF",
                "background": "#0A0A0A"
            },
            "params": {
                "particle_intensity": 2.0,
                "shake_on_beat": True
            }
        },
        "postprocess": {
            "contrast": 1.1,
            "saturation": 1.2,
            "grain": 0.05,
            "vignette": 0.3
        }
    }
    
    with open(output, 'w') as f:
        json.dump(config, f, indent=2)
    
    click.echo(f"Konfigurations-Template erstellt: {output}")


if __name__ == '__main__':
    cli()
