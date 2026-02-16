# Audio Visualizer Pro - Schnellstart 🚀

Dein Audio-Visualisierungs-System ist bereit! Diese Anleitung zeigt dir, wie du sofort loslegen kannst.

## 🖥️ Grafische Oberfläche (GUI) - Einfachste Option!

Die GUI ist die benutzerfreundlichste Art, den Visualizer zu nutzen:

### Windows
```bash
# Doppelklicke auf:
start_gui.bat

# Oder via Python:
python start_gui.py
```

### macOS / Linux
```bash
python start_gui.py
```

Die GUI öffnet sich automatisch in deinem Browser unter `http://localhost:8501`

## ✅ Was wurde bereits eingerichtet

- [x] 10 integrierte Visualizer (Pulsing Core, Spectrum Bars, Chroma Field, Particle Swarm, Typographic, Neon Oscilloscope, Sacred Mandala, Liquid Blobs, Neon Wave Circle, Frequency Flower)
- [x] Plugin-System mit `@register_visualizer` Decorator
- [x] Audio-Analyse mit Beat-Erkennung und Key-Erkennung
- [x] Aggressives Caching (`.cache/` Ordner)
- [x] Post-Processing (Film Grain, Vignette, Chromatic Aberration)
- [x] FFmpeg-Integration für professionelles Video-Encoding
- [x] Roboto Font für saubere Text-Rendering
- [x] 10 Config-Presets (default, music_aggressive, podcast_minimal, particle_explosion, chromatic_dream, neon_cyberpunk, sacred_geometry, liquid_blobs, neon_circle, flower_bloom)
- [x] Moderne Web-GUI mit Streamlit
- [x] Vollständige Test-Suite

## 🛠️ Voraussetzungen

### FFmpeg muss installiert sein

**Windows:**
1. Lade FFmpeg von https://ffmpeg.org/download.html herunter
2. Entpacke es und füge den `bin` Ordner zu deinem PATH hinzu
3. Teste: `ffmpeg -version`

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

### Python-Abhängigkeiten

```bash
pip install -r requirements.txt
```

## 🚀 Erste Schritte

### 1. Audio analysieren

```bash
python main.py analyze dein_lied.mp3
```

Zeigt Informationen wie:
- Dauer, BPM, Key, Mode (Musik/Sprache)
- Feature-Statistiken (RMS, Onset, etc.)

### 2. Verfügbare Visualizer anzeigen

```bash
python main.py list-visuals
```

### 3. Schnelle Vorschau (5 Sekunden, 480p)

```bash
python main.py render dein_lied.mp3 --visual pulsing_core --preview
```

### 4. Volles Video rendern

```bash
python main.py render dein_lied.mp3 --visual spectrum_bars -o output.mp4
```

### 5. Mit Config-Preset rendern

```bash
python main.py render dein_lied.mp3 --config config/music_aggressive.json
```

## 🎨 Verfügbare Visualizer

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

## ⚙️ Config-Presets

| Preset | Beschreibung |
|--------|--------------|
| `default.json` | Ausgewogene Einstellungen für den Allgemeingebrauch |
| `music_aggressive.json` | Hoher Kontrast, Film Grain, Vignette für aggressive Musik |
| `podcast_minimal.json` | Sauber, minimalistisch mit Wellenform für Sprache |
| `particle_explosion.json` | Optimiert für den Particle Swarm Visualizer |
| `chromatic_dream.json` | Weiche Farben, Chromatic Aberration für Ambient |
| `neon_cyberpunk.json` | Cyan/Magenta Neon-Effekte für Synthwave |
| `sacred_geometry.json` | Lila/Orange für spirituelle/ambient Musik |
| `liquid_blobs.json` | Flüssige Blau/Pink Blobs für elektronische Musik |
| `neon_circle.json` | Grün/Rot konzentrische Ringe für EDM |
| `flower_bloom.json` | Sanfte Pastellfarben für Indie/Folk |

## 🧪 Tests ausführen

```bash
# Alle Tests
pytest tests/ -v

# Nur Visualizer-Tests (schnell)
pytest tests/test_visuals.py -v

# Nur Analyzer-Tests (braucht länger)
pytest tests/test_analyzer.py -v
```

## 🎨 Eigenen Visualizer erstellen

### Template generieren

```bash
python main.py create-template mein_visualizer
```

### Implementieren

Bearbeite `src/visuals/mein_visualizer.py`:

```python
@register_visualizer("mein_visualizer")
class MeinVisualizer(BaseVisualizer):
    def setup(self):
        self.center = (self.width // 2, self.height // 2)
    
    def render_frame(self, frame_idx: int) -> np.ndarray:
        # Features holen
        f = self.get_feature_at_frame(frame_idx)
        rms = f['rms']        # 0.0-1.0 Lautstärke
        onset = f['onset']    # 0.0-1.0 Beat-Trigger
        chroma = f['chroma']  # 12 Werte für Halbtöne
        
        # Deine Zeichen-Logik...
        img = Image.new('RGB', (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Beispiel: Kreis mit RMS-Größe
        radius = int(50 + rms * 100)
        draw.ellipse([self.center[0]-radius, self.center[1]-radius,
                      self.center[0]+radius, self.center[1]+radius],
                     fill=(255, 0, 100))
        
        return np.array(img)
```

### Testen

```bash
python main.py render dein_lied.mp3 --visual mein_visualizer --preview
```

## 📊 Feature-Keys Referenz

| Key | Bereich | Verwendung |
|-----|---------|------------|
| `rms` | 0.0-1.0 | Lautstärke → Größe/Opazität |
| `onset` | 0.0-1.0 | Beats → Trigger/Explosionen |
| `chroma` | Array[12] | Tonart → Farben (C, C#, D, ...) |
| `spectral_centroid` | 0.0-1.0 | Helligkeit/Detail |
| `spectral_rolloff` | 0.0-1.0 | Bandbreite |
| `zero_crossing_rate` | 0.0-1.0 | Noise vs Tonal |
| `progress` | 0.0-1.0 | Zeit-Fortschritt |

## 🎬 CLI-Referenz

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
--preview-duration  Vorschau-Dauer in Sekunden (default: 5.0)
```

## 💡 Performance-Tipps

1. **Immer Vorschau zuerst**: Nutze `--preview` für schnelles Testen (5 Sekunden, 480p)
2. **Caching**: Audio-Analyse wird automatisch gecached (`.cache/audio_features/`)
3. **Niedrigere FPS**: 30fps statt 60fps für schnelleres Rendering
4. **Niedrigere Auflösung**: Starte mit 1280x720 für schnellere Tests

## 🆘 Troubleshooting

### FFmpeg nicht gefunden
```
Fehler: FFmpeg nicht installiert oder nicht im PATH
```
**Lösung**: FFmpeg installieren und zu PATH hinzufügen (siehe Voraussetzungen)

### Audio-Datei nicht gefunden
```
FileNotFoundError: Audio nicht gefunden
```
**Lösung**: Überprüfe den Dateipfad, verwende absolute Pfade wenn nötig

### ImportError: No module named 'librosa'
```
ModuleNotFoundError: No module named 'librosa'
```
**Lösung**: `pip install -r requirements.txt`

### Visualizer wird nicht gefunden
```
ValueError: Unbekannter Visualizer: xxx
```
**Lösung**: Überprüfe den Namen mit `python main.py list-visuals`

## 🎯 Workflow-Beispiele

### Musikvideo erstellen

```bash
# 1. Audio analysieren
python main.py analyze song.mp3

# 2. Vorschau mit verschiedenen Visualizern testen
python main.py render song.mp3 --visual pulsing_core --preview
python main.py render song.mp3 --visual spectrum_bars --preview

# 3. Besten Visualizer wählen und volles Video rendern
python main.py render song.mp3 --visual spectrum_bars -o music_video.mp4
```

### Podcast-Visual erstellen

```bash
# Podcast-Config verwenden (minimal, sauber)
python main.py render podcast.mp3 --config config/podcast_minimal.json -o podcast_visual.mp4
```

### Kreatives Projekt mit Custom Config

```bash
# Config-Template erstellen
python main.py create-config --output my_config.json

# Config anpassen (Farben, Effekte, etc.)
# ... editiere my_config.json ...

# Mit Custom Config rendern
python main.py render song.mp3 --config my_config.json
```

---

**🎉 Fertig! Viel Spaß beim Erstellen von Audio-Visualisierungen!**
