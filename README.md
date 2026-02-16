# Audio Visualizer Pro 🎵✨

Ein modulares, KI-optimiertes Audio-Visualisierungs-System für professionelle Musikvideos, Podcast-Visuals und kreative Projekte.

## 🚀 Schnellstart

**Neu hier?** Siehe [QUICKSTART.md](QUICKSTART.md) für eine vollständige Schritt-für-Schritt-Anleitung!

### Option 1: Grafische Oberfläche (Empfohlen für Einsteiger)
```bash
# Windows: Doppelklicke auf start_gui.bat
# Oder überall:
python start_gui.py

# Öffnet automatisch http://localhost:8501 im Browser
```

### Option 2: Kommandozeile
```bash
# Installation
pip install -r requirements.txt

# FFmpeg muss system-seitig installiert sein (siehe QUICKSTART.md)

# 5-Sekunden Vorschau rendern
python main.py render song.mp3 --visual pulsing_core --preview

# Volles Video rendern
python main.py render song.mp3 --visual spectrum_bars -o output.mp4
```

## Features

- **🖥️ Grafische Oberfläche**: Moderne Web-GUI mit Streamlit (keine Kommandozeile nötig!)
- **10 integrierte Visualizer**: Pulsing Core, Spectrum Bars, Chroma Field, Particle Swarm, Typographic, Neon Oscilloscope, Sacred Mandala, Liquid Blobs, Neon Wave Circle, Frequency Flower
- **Plugin-System**: Einfache Erweiterung mit `@register_visualizer` Decorator
- **Intelligente Audio-Analyse**: Beat-Erkennung, Key-Erkennung, Chroma-Features
- **Aggressives Caching**: Analysiere einmal, rendere millionenmal
- **Professionelle Codecs**: FFmpeg-basiert mit libx264 und AAC
- **Post-Processing**: LUTs, Film Grain, Vignette, Chromatic Aberration

## Schnellstart

```bash
# Installation
pip install -r requirements.txt

# FFmpeg muss system-seitig installiert sein:
# Ubuntu: sudo apt-get install ffmpeg
# macOS: brew install ffmpeg
# Windows: https://ffmpeg.org/download.html

# Audio analysieren
python main.py analyze song.mp3

# Verfügbare Visualizer anzeigen
python main.py list-visuals

# 5-Sekunden Vorschau rendern
python main.py render song.mp3 --visual pulsing_core --preview

# Volles Video rendern
python main.py render song.mp3 --visual spectrum_bars -o output.mp4

# Mit Config-Preset rendern
python main.py render song.mp3 --config config/neon_cyberpunk.json
```

## Verfügbare Visualizer

| Visualizer | Beschreibung | Best für |
|------------|--------------|----------|
| `pulsing_core` | Pulsierender Kreis mit Chroma-Farben | EDM, Pop |
| `spectrum_bars` | 40-Balken Equalizer | Rock, Hip-Hop |
| `chroma_field` | Partikel-Feld basierend auf Tonart | Ambient, Jazz |
| `particle_swarm` | Physik-basierte Partikel-Explosionen | Dubstep, Trap |
| `typographic` | Minimalistisch mit Wellenform | Podcasts, Sprache |
| `neon_oscilloscope` | Retro-futuristischer Oszilloskop mit Neon-Effekten | Synthwave, Cyberpunk |
| `sacred_mandala` | Heilige Geometrie mit rotierenden Mustern | Meditation, Ambient |
| `liquid_blobs` | Flüssige MetaBall-ähnliche Blob-Animation | House, Techno |
| `neon_wave_circle` | Konzentrische Neon-Ringe mit Wellen | EDM, Techno |
| `frequency_flower` | Organische Blumen mit Audio-reaktiven Blütenblättern | Indie, Folk, Pop |

## Neuer Visualizer erstellen

```bash
# Template generieren
python main.py create-template mein_visualizer

# Implementieren in src/visuals/mein_visualizer.py
# Automatisch registriert via @register_visualizer
```

### Template-Struktur

```python
@register_visualizer("mein_visualizer")
class MeinVisualizer(BaseVisualizer):
    def setup(self):
        # Initialisierung
        self.center = (self.width // 2, self.height // 2)
    
    def render_frame(self, frame_idx: int) -> np.ndarray:
        # Features holen
        f = self.get_feature_at_frame(frame_idx)
        rms = f['rms']        # 0.0-1.0 Lautstärke
        onset = f['onset']    # 0.0-1.0 Beat-Trigger
        chroma = f['chroma']  # 12 Werte für Halbtöne
        
        # Deine Zeichen-Logik...
        img = Image.new('RGB', (self.width, self.height), (0, 0, 0))
        
        return np.array(img)
```

## Wichtige Features-Keys

| Key | Bereich | Verwendung |
|-----|---------|------------|
| `rms` | 0.0-1.0 | Lautstärke → Größe/Opazität |
| `onset` | 0.0-1.0 | Beats → Trigger/Explosionen |
| `chroma` | Array[12] | Tonart → Farben |
| `spectral_centroid` | 0.0-1.0 | Helligkeit/Detail |
| `progress` | 0.0-1.0 | Zeit-Fortschritt |

## Konfiguration

### Beispiel-Config erstellen

```bash
python main.py create-config --output meine_config.json
```

### Config-Struktur

```json
{
  "audio_file": "song.mp3",
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
      "particle_intensity": 2.0
    }
  },
  "postprocess": {
    "contrast": 1.1,
    "saturation": 1.2,
    "grain": 0.05,
    "vignette": 0.3
  }
}
```

## Tests ausführen

```bash
# Alle Tests
pytest tests/ -v

# Spezifische Tests
pytest tests/test_visuals.py -v
pytest tests/test_analyzer.py -v
```

## Projektstruktur

```
audio_visualizer_pro/
├── config/                 # Konfigurations-Presets (10 Stück)
│   ├── default.json
│   ├── music_aggressive.json
│   ├── podcast_minimal.json
│   ├── chromatic_dream.json
│   ├── particle_explosion.json
│   ├── neon_cyberpunk.json
│   ├── sacred_geometry.json
│   ├── liquid_blobs.json
│   ├── neon_circle.json
│   └── flower_bloom.json
├── src/
│   ├── analyzer.py         # Audio-Feature-Extraktion
│   ├── pipeline.py         # Haupt-Orchestrator
│   ├── types.py            # Pydantic Models
│   ├── visuals/            # Plugin-System
│   │   ├── base.py         # BaseVisualizer
│   │   ├── registry.py     # Plugin-Registry
│   │   ├── 01_pulsing_core.py
│   │   ├── 02_spectrum_bars.py
│   │   ├── 03_chroma_field.py
│   │   ├── 04_particle_swarm.py
│   │   ├── 05_typographic.py
│   │   ├── 06_neon_oscilloscope.py
│   │   ├── 07_sacred_mandala.py
│   │   ├── 08_liquid_blobs.py
│   │   ├── 09_neon_wave_circle.py
│   │   └── 10_frequency_flower.py
│   ├── renderers/
│   │   └── pil_renderer.py
│   └── postprocess.py      # Color Grading
├── tests/
│   ├── test_analyzer.py
│   └── test_visuals.py
├── main.py                 # CLI Entry Point
├── gui.py                  # 🆕 Grafische Oberfläche
├── start_gui.py            # 🆕 GUI Launcher
├── start_gui.bat           # 🆕 Windows GUI Starter
└── requirements.txt
```

## CLI-Referenz

```bash
# Hauptbefehle
python main.py render <audio> [options]
python main.py analyze <audio>
python main.py list-visuals
python main.py create-template <name>
python main.py create-config [options]

# Render-Optionen
--visual, -v        Visualizer-Typ (default: pulsing_core)
--output, -o        Output-Datei (default: output.mp4)
--config, -c        Config-JSON verwenden
--resolution, -r    Auflösung (default: 1920x1080)
--fps               FPS (default: 60)
--preview           5-Sekunden-Vorschau
--preview-duration  Vorschau-Dauer in Sekunden
```

## Performance-Tipps

1. **Vorschau zuerst**: Nutze `--preview` für schnelles Testen
2. **Caching**: Audio-Analyse wird automatisch gecached
3. **Niedrigere FPS**: 30fps statt 60fps für schnelleres Rendering
4. **Niedrigere Auflösung**: PreviewPipeline nutzt automatisch 480p

## Lizenz

MIT License - Siehe LICENSE-Datei

## Credits

- Audio-Analyse: [Librosa](https://librosa.org/)
- Bildverarbeitung: [Pillow](https://python-pillow.org/)
- Video-Encoding: [FFmpeg](https://ffmpeg.org/)
