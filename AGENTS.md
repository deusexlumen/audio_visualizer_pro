# Audio Visualizer Pro - Agent Guide

Dieses Dokument enthält alle relevanten Informationen für KI-Code-Agents, die an diesem Projekt arbeiten.

## Projekt-Übersicht

**Audio Visualizer Pro** ist ein modulares, KI-optimiertes Audio-Visualisierungs-System für professionelle Musikvideos, Podcast-Visuals und kreative Projekte.

### Kern-Features
- **13 integrierte Visualizer**: Pulsing Core, Spectrum Bars, Chroma Field, Particle Swarm, Typographic, Neon Oscilloscope, Sacred Mandala, Liquid Blobs, Neon Wave Circle, Frequency Flower, Waveform Line, 3D Spectrum, Circular Wave
- **Plugin-System**: Einfache Erweiterung mit `@register_visualizer` Decorator
- **Intelligente Audio-Analyse**: Beat-Erkennung, Key-Erkennung, Chroma-Features
- **Aggressives Caching**: Analysiere einmal, rendere millionenmal
- **Professionelle Codecs**: FFmpeg-basiert mit libx264 und AAC
- **Post-Processing**: LUTs, Film Grain, Vignette, Chromatic Aberration
- **Grafische Oberfläche**: Streamlit-basierte Web-GUI mit Live-Preview
- **Export-Profile**: Optimale Einstellungen für YouTube, Instagram, TikTok
- **Live-Preview**: Frame-Vorschau ohne FFmpeg
- **Preset-Editor**: Visueller Editor für Config-Presets

## Technologie-Stack

| Komponente | Bibliothek | Zweck |
|------------|------------|-------|
| Audio-Analyse | librosa>=0.10.0 | Feature-Extraktion (RMS, Onset, Chroma, etc.) |
| Bildverarbeitung | Pillow>=9.0.0 | Frame-Generierung |
| Datenvalidierung | pydantic>=2.0.0 | Konfiguration-Models |
| CLI | click>=8.0.0 | Kommandozeilen-Interface |
| GUI | streamlit>=1.28.0 | Web-basierte Oberfläche |
| Numerik | numpy>=1.21.0 | Array-Operationen |
| Testing | pytest>=7.0.0 | Test-Framework |
| Audio-I/O | soundfile>=0.11.0 | Test-Dateien |
| Fortschrittsbalken | tqdm>=4.62.0 | UX-Verbesserung |
| Video-Encoding | FFmpeg (system) | H.264/AAC Encoding |

**System-Voraussetzung**: FFmpeg muss system-seitig installiert sein.
- Ubuntu/Debian: `sudo apt-get install ffmpeg`
- macOS: `brew install ffmpeg`
- Windows: https://ffmpeg.org/download.html

## Projektstruktur

```
audio_visualizer_pro/
├── main.py                 # CLI Entry Point (Click-basiert)
├── gui.py                  # Streamlit-GUI (mit echtem Progress)
├── start_gui.py            # GUI-Launcher
├── start_gui.bat           # Windows GUI Starter
├── requirements.txt        # Python-Abhängigkeiten
├── .env.example            # Beispiel-Umgebungsvariablen
├── config/                 # Konfigurations-Presets und Validierung
│   ├── schemas.py          # Pydantic-v2-Schemas für Config-Validierung
│   ├── default.json        # Standard-Konfiguration
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
│   ├── __init__.py
│   ├── analyzer.py         # AudioAnalyzer mit Caching
│   ├── pipeline.py         # RenderPipeline, PreviewPipeline
│   ├── types.py            # Pydantic Models (AudioFeatures, VisualConfig, etc.)
│   ├── postprocess.py      # PostProcessor für Color Grading
│   ├── logger.py           # Zentrales Logging-System
│   ├── settings.py         # Konfiguration via Umgebungsvariablen
│   ├── utils.py            # System-Checks (FFmpeg), Validierung
│   ├── parallel_renderer.py # [EXP] Paralleles Rendering
│   ├── visuals/            # Plugin-System
│   │   ├── __init__.py
│   │   ├── base.py         # BaseVisualizer (abstrakte Basisklasse)
│   │   ├── registry.py     # VisualizerRegistry mit @register_visualizer
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
│   └── renderers/
│       ├── __init__.py
│       └── pil_renderer.py # PILRenderer für Frame-Generierung
└── tests/
    ├── __init__.py
    ├── test_analyzer.py    # Tests für AudioAnalyzer
    └── test_visuals.py     # Tests für alle Visualizer
```

## Build- und Test-Kommandos

### Installation
```bash
pip install -r requirements.txt
```

### System-Check
```bash
# Prüfe ob FFmpeg installiert ist und alle Komponenten funktionieren
python main.py check
```

### Settings & Konfiguration

Über Umgebungsvariablen oder `.env`-Datei:
```bash
# .env-Datei erstellen
python main.py env-template

# Wichtige Variablen:
AV_CACHE_DIR=.cache/audio_features
AV_DEFAULT_RESOLUTION=1920x1080
AV_DEFAULT_FPS=60
AV_LOG_LEVEL=INFO
AV_FFMPEG_PRESET=medium
AV_FFMPEG_CRF=23
```

Im Code verwenden:
```python
from src.settings import get_settings

settings = get_settings()
print(settings.default_resolution)  # (1920, 1080)
print(settings.cache_dir)           # Path('.cache/audio_features')
```

### Cache-Management
```bash
# Cache-Größe anzeigen (via check)
python main.py check

# Cache leeren
python main.py clear-cache

# Oder mit Bestätigung überspringen
python main.py clear-cache --yes
```

### CLI-Befehle
```bash
# Audio analysieren
python main.py analyze song.mp3

# Verfügbare Visualizer anzeigen
python main.py list-visuals

# 5-Sekunden Vorschau rendern
python main.py render song.mp3 --visual pulsing_core --preview

# Volles Video rendern
python main.py render song.mp3 --visual spectrum_bars -o output.mp4

# Mit Config-Datei
python main.py render song.mp3 --config config/music_aggressive.json

# Neues Visualizer-Template erstellen
python main.py create-template mein_visualizer

# Beispiel-Config erstellen
python main.py create-config --output meine_config.json

# System-Check (FFmpeg, Cache, etc.)
python main.py check

# Cache leeren
python main.py clear-cache

# Env-Template erstellen
python main.py env-template

# Paralleles Rendering (experimentell)
python main.py render song.mp3 --visual spectrum_bars --parallel --workers 4

# Mit Export-Profil
python main.py render song.mp3 --profile youtube
python main.py render song.mp3 --profile instagram_reels
python main.py render song.mp3 --profile tiktok
```

### GUI starten
```bash
# Windows: Doppelklicke auf start_gui.bat
# Oder überall:
python start_gui.py

# Öffnet automatisch http://localhost:8501 im Browser
```

### Testing
```bash
# Alle Tests ausführen
pytest tests/ -v

# Spezifische Tests
pytest tests/test_visuals.py -v
pytest tests/test_analyzer.py -v
```

## Architektur

### 3-Schichten-Architektur

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Post-Processing (LUTs, Grain, Vignette)          │
│  → PostProcessor.apply(frame)                              │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Visualization (Frame-Generierung)                │
│  → BaseVisualizer.render_frame(frame_idx)                  │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Audio-Analyse (Feature-Extraktion)               │
│  → AudioAnalyzer.analyze(audio_path, fps)                  │
└─────────────────────────────────────────────────────────────┘
```

### Datenfluss

1. **Audio-Analyse** (`analyzer.py`):
   - Extrahiert Features: RMS, Onset, Chroma, Spectral Centroid, etc.
   - Caching in `.cache/audio_features/` (NPZ-Format)
   - Deterministisch und thread-safe
   - Key-Erkennung für Tonart-basierte Visuals

2. **Visualization** (`visuals/`):
   - Jeder Visualizer erbt von `BaseVisualizer`
   - Registrierung via `@register_visualizer("name")`
   - `render_frame(frame_idx)` gibt RGB-Array zurück
   - Automatisches Laden via `VisualizerRegistry.autoload()`

3. **Rendering** (`pipeline.py`):
   - `RenderPipeline` steuert den kompletten Flow
   - FFmpeg-Subprozess für Video-Encoding (libx264, yuv420p)
   - Audio-Muxing mit AAC-Codec zum Schluss
   - `PreviewPipeline` für schnelle 480p-Vorschau

4. **Post-Processing** (`postprocess.py`):
   - Kontrast, Sättigung, Helligkeit
   - Film Grain, Vignette, Chromatic Aberration
   - LUT-Unterstützung (.cube-Dateien)

## Code-Style Guidelines

### Visualizer erstellen

**WICHTIG**: Neue Visualizer MÜSSEN diese Struktur folgen:

```python
from .base import BaseVisualizer
from .registry import register_visualizer

@register_visualizer("einzigartiger_name")  # 1. Decorator
class MeinVisualizer(BaseVisualizer):        # 2. Erbe von BaseVisualizer
    """Dokumentation hier."""
    
    def setup(self):                         # 3. setup() implementieren
        """Einmalige Initialisierung."""
        self.center = (self.width // 2, self.height // 2)
    
    def render_frame(self, frame_idx: int) -> np.ndarray:  # 4. render_frame() implementieren
        """Rendert EINEN Frame als RGB-Array (H, W, 3), dtype uint8."""
        # Features holen
        f = self.get_feature_at_frame(frame_idx)
        rms = f['rms']        # 0.0-1.0 Lautstärke
        onset = f['onset']    # 0.0-1.0 Beat-Trigger
        chroma = f['chroma']  # 12 Werte für Halbtöne
        progress = f['progress']  # 0.0-1.0 Zeit-Fortschritt
        
        # Deine Zeichen-Logik...
        img = Image.new('RGB', (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        return np.array(img)
```

### Feature-Keys

| Key | Bereich | Verwendung |
|-----|---------|------------|
| `rms` | 0.0-1.0 | Lautstärke → Größe/Opazität |
| `onset` | 0.0-1.0 | Beats → Trigger/Explosionen |
| `chroma` | Array[12] | Tonart → Farben (C, C#, D, ...) |
| `spectral_centroid` | 0.0-1.0 | Helligkeit/Detail |
| `spectral_rolloff` | 0.0-1.0 | Bandbreite |
| `zero_crossing_rate` | 0.0-1.0 | Noise vs Tonal |
| `progress` | 0.0-1.0 | Zeit-Fortschritt |

### Verfügbare Visualizer

| Name | Emoji | Beschreibung | Best für |
|------|-------|--------------|----------|
| `pulsing_core` | 🔴 | Pulsierender Kreis mit Chroma-Farben | EDM, Pop |
| `spectrum_bars` | 📊 | 40-Balken Equalizer | Rock, Hip-Hop |
| `chroma_field` | ✨ | Partikel-Feld basierend auf Tonart | Ambient, Jazz |
| `particle_swarm` | 🔥 | Physik-basierte Partikel-Explosionen | Dubstep, Trap |
| `typographic` | 📝 | Minimalistisch mit Wellenform | Podcasts, Sprache |
| `neon_oscilloscope` | 💠 | Retro-futuristischer Oszilloskop | Synthwave, Cyberpunk |
| `sacred_mandala` | 🕉️ | Heilige Geometrie mit rotierenden Mustern | Meditation, Ambient |
| `liquid_blobs` | 💧 | Flüssige MetaBall-ähnliche Blobs | House, Techno |
| `neon_wave_circle` | ⭕ | Konzentrische Neon-Ringe mit Wellen | EDM, Techno |
| `frequency_flower` | 🌸 | Organische Blumen mit Audio-reaktiven Blütenblättern | Indie, Folk, Pop |

### Konfiguration

Pfade und Einstellungen werden in `src/types.py` als Pydantic-Models definiert:

```python
# AudioFeatures: Schema für alle Audio-Features
# VisualConfig: Jeder Visualizer hat diese Konfiguration
# ProjectConfig: Gesamtkonfiguration einer Render-Job
```

JSON-Configs werden in `config/schemas.py` validiert. Beispiel-Config-Struktur:

```json
{
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
      "particle_intensity": 1.0,
      "shake_on_beat": false
    }
  },
  "postprocess": {
    "contrast": 1.0,
    "saturation": 1.0,
    "grain": 0.0,
    "vignette": 0.0,
    "chromatic_aberration": 0.0
  }
}
```

## Testing Strategie

### Test-Dateien

- **`test_analyzer.py`**: Testet Audio-Feature-Extraktion
  - Feature-Shapes validieren
  - Caching-Verhalten testen
  - Wertebereiche prüfen (0-1)
  - Hilfsmethoden testen (_normalize, _interpolate_to_length)

- **`test_visuals.py`**: Testet alle Visualizer
  - Rückgabe muss `np.ndarray` sein
  - Shape muss `(H, W, 3)` sein
  - `dtype` muss `uint8` sein
  - Werte müssen in 0-255 liegen
  - Registry-Autoloading testen

### Test-Hilfsfunktionen

```python
# Dummy-Features für schnelle Tests
dummy_features = AudioFeatures(
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
```

## GUI-Architektur

Die GUI (`gui.py`) ist eine Streamlit-basierte Web-Anwendung:

- **Layout**: Zwei-Spalten-Layout (Audio-Upload / Visualizer-Auswahl)
- **Features**:
  - Audio-Upload mit Drag & Drop
  - Audio-Analyse-Anzeige (Dauer, BPM, Key, Modus)
  - Visualizer-Vorschau mit Beschreibungen
  - Config-Preset-Auswahl
  - Render-Modus: Vorschau (5s, 480p) oder Vollständig (HD)
  - Live-Fortschrittsbalken
  - Video-Download nach Rendering

- **Styling**: Custom CSS für dunkles Theme mit Gradienten

## Sicherheitsaspekte

1. **Datei-Validierung**: Audio-Dateien werden auf gültige Endungen geprüft (`.mp3`, `.wav`, `.flac`, `.aac`, `.ogg`, `.m4a`)
2. **Output-Validierung**: Output-Dateien müssen `.mp4` Endung haben
3. **Cache-Isolierung**: Cache wird in `.cache/` gespeichert, nicht im Output-Verzeichnis
4. **Temporäre Dateien**: Werden mit `tempfile` erstellt und aufgeräumt
5. **Subprozess-Sicherheit**: FFmpeg-Befehle sind parametrisiert, keine User-Input-Injection

## Performance-Tipps

1. **Vorschau zuerst**: Nutze `--preview` für schnelles Testen (5 Sekunden, 480p)
2. **Aggressives Caching**: Audio-Analyse wird automatisch gecached (`.cache/audio_features/`)
3. **Niedrigere FPS**: 30fps statt 60fps für schnelleres Rendering
4. **Niedrigere Auflösung**: PreviewPipeline nutzt automatisch 480p
5. **Key-Erkennung**: Wird für Dateien >10min übersprungen (Performance)
6. **Paralleles Rendering**: [EXPERIMENTAL] Nutze `--parallel` für Multi-Core-Rendering
7. **LUT-Optimierung**: Vectorisierte LUT-Anwendung (100x schneller als Schleifen)
8. **Temp-Verzeichnis**: Setze `AV_TEMP_DIR` auf schnelle SSD

## Wichtige Dateien für KI-Agents

| Datei | Beschreibung |
|-------|--------------|
| `src/visuals/base.py` | Muss gelesen werden für neue Visualizer |
| `src/visuals/registry.py` | Plugin-System verstehen |
| `src/types.py` | Alle Pydantic Models |
| `config/schemas.py` | Config-Validierung |
| `src/analyzer.py` | Audio-Feature-Extraktion (NICHT ÄNDERN, nur erweitern) |
| `src/pipeline.py` | Render-Flow verstehen |
| `src/postprocess.py` | Post-Processing-Effekte |
| `src/logger.py` | Logging-System |
| `src/settings.py` | Konfiguration via .env |
| `src/utils.py` | System-Checks und Validierung |
| `src/parallel_renderer.py` | Paralleles Rendering |
| `src/export_profiles.py` | Export-Profile für Plattformen |
| `src/live_preview.py` | Live-Frame-Preview |

## Häufige Aufgaben

### Neuen Visualizer hinzufügen

1. `python main.py create-template mein_visualizer` ausführen
2. `src/visuals/mein_visualizer.py` implementieren
3. In `test_visuals.py` automatisch getestet (Registry-Autoload)
4. In `gui.py` `get_visualizer_info()` um Info ergänzen (optional)

### Neue Config-Preset erstellen

1. `python main.py create-config --output config/mein_preset.json`
2. Werte anpassen
3. Schema in `config/schemas.py` bei Bedarf erweitern
4. Literal-Typen in `VisualConfigSchema` aktualisieren

### Audio-Analyse erweitern

**ACHTUNG**: Die `analyze()` Methode in `analyzer.py` sollte NICHT geändert werden (Caching!).
Stattdessen neue Features hinzufügen:
1. Neues Feature in `AudioFeatures` Model (`src/types.py`) ergänzen
2. Extraktion in `analyzer.py` hinzufügen (nach den bestehenden Features)
3. Caching-Logik bleibt unverändert

## Sprache und Kommentare

- **Code-Kommentare**: Deutsch
- **Dokumentation**: Deutsch
- **README**: Deutsch
- **Commit-Messages**: Deutsch (empfohlen)

## Lizenz

MIT License - Siehe LICENSE-Datei
