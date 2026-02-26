"""
Audio Visualizer Pro - Grafische Benutzeroberfläche (GUI)

Eine moderne Web-basierte GUI mit Streamlit.
Ermöglicht einfache Bedienung ohne Kommandozeile.
"""

import streamlit as st
import subprocess
import sys
import json
import os
import tempfile
import shutil
import io
from pathlib import Path
from datetime import datetime

# Füge src zum Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent))

from src.visuals.registry import VisualizerRegistry
from src.analyzer import AudioAnalyzer

# Seiten-Config
st.set_page_config(
    page_title="Audio Visualizer Pro",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS für besseres Styling
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: #ffffff;
    }
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 15px 30px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
    }
    .stProgress .st-bo {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    .stSelectbox {
        background: rgba(255, 255, 255, 0.1);
    }
    h1, h2, h3 {
        color: #ffffff !important;
    }
    .preview-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .success-box {
        background: rgba(39, 174, 96, 0.2);
        border-left: 4px solid #27ae60;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .info-box {
        background: rgba(52, 152, 219, 0.2);
        border-left: 4px solid #3498db;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


def get_available_visualizers():
    """Lädt alle verfügbaren Visualizer."""
    VisualizerRegistry.autoload()
    return VisualizerRegistry.list_available()


def get_config_presets():
    """Lädt alle Config-Presets."""
    config_dir = Path("config")
    presets = {}
    if config_dir.exists():
        for json_file in config_dir.glob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    presets[json_file.stem] = {
                        'file': str(json_file),
                        'visual': data.get('visual', {}).get('type', 'unknown'),
                        'description': data.get('description', '')
                    }
            except:
                pass
    return presets


def get_visualizer_info(visualizer_name: str) -> dict:
    """Gibt Informationen über einen Visualizer zurück."""
    info = {
        'pulsing_core': {
            'emoji': '🔴',
            'description': 'Pulsierender Kreis mit Chroma-Farben',
            'best_for': 'EDM, Pop',
            'color': '#FF0055'
        },
        'spectrum_bars': {
            'emoji': '📊',
            'description': '40-Balken Equalizer',
            'best_for': 'Rock, Hip-Hop',
            'color': '#00CCFF'
        },
        'chroma_field': {
            'emoji': '✨',
            'description': 'Partikel-Feld basierend auf Tonart',
            'best_for': 'Ambient, Jazz',
            'color': '#9D4EDD'
        },
        'particle_swarm': {
            'emoji': '🔥',
            'description': 'Physik-basierte Partikel-Explosionen',
            'best_for': 'Dubstep, Trap',
            'color': '#FF6B35'
        },
        'typographic': {
            'emoji': '📝',
            'description': 'Minimalistisch mit Wellenform',
            'best_for': 'Podcasts, Sprache',
            'color': '#00F5FF'
        },
        'neon_oscilloscope': {
            'emoji': '💠',
            'description': 'Retro-futuristischer Oszilloskop',
            'best_for': 'Synthwave, Cyberpunk',
            'color': '#00F5FF'
        },
        'sacred_mandala': {
            'emoji': '🕉️',
            'description': 'Heilige Geometrie mit rotierenden Mustern',
            'best_for': 'Meditation, Ambient',
            'color': '#FF9E00'
        },
        'liquid_blobs': {
            'emoji': '💧',
            'description': 'Flüssige MetaBall-ähnliche Blobs',
            'best_for': 'House, Techno',
            'color': '#00D9FF'
        },
        'neon_wave_circle': {
            'emoji': '⭕',
            'description': 'Konzentrische Neon-Ringe mit Wellen',
            'best_for': 'EDM, Techno',
            'color': '#39FF14'
        },
        'frequency_flower': {
            'emoji': '🌸',
            'description': 'Organische Blumen mit Audio-reaktiven Blütenblättern',
            'best_for': 'Indie, Folk, Pop',
            'color': '#FFB7B2'
        },
        'waveform_line': {
            'emoji': '📈',
            'description': 'Oszilloskop-ähnliche Wellenform-Linie',
            'best_for': 'Podcasts, Sprache, Akustik',
            'color': '#00FF96'
        },
        '3d_spectrum': {
            'emoji': '🏙️',
            'description': '3D-Balken-Equalizer mit Perspektive',
            'best_for': 'EDM, Techno, Elektronisch',
            'color': '#FF00FF'
        },
        'circular_wave': {
            'emoji': '🌀',
            'description': 'Kreisförmige, rotierende Wellenform',
            'best_for': 'Ambient, Meditation, Atmosphärisch',
            'color': '#9D4EDD'
        }
    }
    return info.get(visualizer_name, {
        'emoji': '🎨',
        'description': 'Visualizer',
        'best_for': 'Alle Genres',
        'color': '#ffffff'
    })


def render_preset_editor():
    """Rendert den Preset-Editor."""
    st.markdown("### ⚙️ Config-Preset Editor")
    st.markdown("Erstelle und speichere benutzerdefinierte Konfigurationen.")
    
    # Preset laden oder neu erstellen
    col_load, col_save = st.columns([1, 1])
    
    with col_load:
        presets = get_config_presets()
        if presets:
            selected_preset = st.selectbox(
                "Vorhandenes Preset laden",
                ["Neues Preset"] + list(presets.keys()),
                format_func=lambda x: f"{x} ({presets[x]['visual']})" if x in presets else x
            )
        else:
            selected_preset = "Neues Preset"
    
    # Konfiguration
    st.markdown("---")
    st.markdown("#### 🎨 Visualizer-Einstellungen")
    
    col_vis1, col_vis2 = st.columns([1, 1])
    
    with col_vis1:
        available_visualizers = get_available_visualizers()
        visualizer = st.selectbox(
            "Visualizer",
            available_visualizers,
            format_func=lambda x: f"{get_visualizer_info(x)['emoji']} {x.replace('_', ' ').title()}",
            key="preset_editor_visualizer"
        )
    
    with col_vis2:
        resolution = st.selectbox(
            "Auflösung",
            ["1920x1080", "1280x720", "3840x2160", "854x480"],
            index=0,
            key="preset_editor_resolution"
        )
        fps = st.selectbox("FPS", [60, 30, 24], index=0, key="preset_editor_fps")
    
    # Farben
    st.markdown("#### 🎨 Farben")
    col_colors = st.columns(3)
    
    with col_colors[0]:
        primary_color = st.color_picker("Primärfarbe", "#FF0055", key="preset_editor_primary")
    with col_colors[1]:
        secondary_color = st.color_picker("Sekundärfarbe", "#00CCFF", key="preset_editor_secondary")
    with col_colors[2]:
        background_color = st.color_picker("Hintergrund", "#0A0A0A", key="preset_editor_bg")
    
    # Post-Processing
    st.markdown("#### ✨ Post-Processing")
    col_post = st.columns(3)
    
    with col_post[0]:
        contrast = st.slider("Kontrast", 0.5, 2.0, 1.0, 0.1, key="preset_editor_contrast")
        saturation = st.slider("Sättigung", 0.0, 2.0, 1.0, 0.1, key="preset_editor_sat")
    with col_post[1]:
        brightness = st.slider("Helligkeit", 0.5, 2.0, 1.0, 0.1, key="preset_editor_brightness")
        grain = st.slider("Film Grain", 0.0, 1.0, 0.0, 0.05, key="preset_editor_grain")
    with col_post[2]:
        vignette = st.slider("Vignette", 0.0, 1.0, 0.0, 0.05, key="preset_editor_vignette")
        chromatic = st.slider("Chromatic Aberration", 0.0, 5.0, 0.0, 0.5, key="preset_editor_chromatic")
    
    # Erweiterte Parameter
    st.markdown("#### ⚡ Erweiterte Parameter")
    show_advanced = st.checkbox("Erweiterte Parameter anzeigen", key="preset_editor_advanced")
    
    params = {}
    if show_advanced:
        col_adv = st.columns(2)
        with col_adv[0]:
            params['particle_intensity'] = st.slider("Partikel-Intensität", 0.0, 10.0, 1.0, 0.5, key="preset_editor_intensity")
            params['shake_on_beat'] = st.checkbox("Shake auf Beat", value=False, key="preset_editor_shake")
        with col_adv[1]:
            params['bar_count'] = st.slider("Balken-Anzahl", 10, 100, 40, 5, key="preset_editor_bars")
            params['show_waveform'] = st.checkbox("Wellenform anzeigen", value=True, key="preset_editor_waveform")
    
    # Preset speichern
    st.markdown("---")
    
    col_save_btn, col_name = st.columns([1, 2])
    
    with col_name:
        preset_name = st.text_input("Preset-Name", f"mein_preset_{visualizer}", key="preset_editor_name")
    
    with col_save_btn:
        st.write("")  # Spacer
        st.write("")
        if st.button("💾 Speichern", use_container_width=True):
            # Erstelle Config-Dict
            config = {
                "audio_file": "input.mp3",
                "output_file": "output.mp4",
                "visual": {
                    "type": visualizer,
                    "resolution": [int(x) for x in resolution.split('x')],
                    "fps": fps,
                    "colors": {
                        "primary": primary_color,
                        "secondary": secondary_color,
                        "background": background_color
                    },
                    "params": params
                },
                "postprocess": {
                    "contrast": contrast,
                    "saturation": saturation,
                    "brightness": brightness,
                    "grain": grain,
                    "vignette": vignette,
                    "chromatic_aberration": chromatic
                }
            }
            
            # Speichern
            output_path = Path("config") / f"{preset_name}.json"
            output_path.parent.mkdir(exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            st.success(f"Preset gespeichert: {output_path}")
    
    # JSON-Preview
    st.markdown("---")
    st.markdown("#### 📝 JSON-Vorschau")
    
    preview_config = {
        "visual": {
            "type": visualizer,
            "resolution": resolution,
            "fps": fps,
            "colors": {
                "primary": primary_color,
                "secondary": secondary_color,
                "background": background_color
            }
        },
        "postprocess": {
            "contrast": contrast,
            "saturation": saturation,
            "grain": grain,
            "vignette": vignette
        }
    }
    st.code(json.dumps(preview_config, indent=2), language="json")


def render_with_pipeline(
    audio_path: str,
    visualizer: str,
    output_path: str,
    resolution: tuple = (1920, 1080),
    fps: int = 60,
    preview: bool = False,
    preview_duration: float = 5.0,
    progress_bar=None,
    status_text=None
):
    """
    Rendert mit direkter Pipeline-Nutzung für echten Progress.
    """
    from src.pipeline import PreviewPipeline, RenderPipeline
    from src.types import ProjectConfig, VisualConfig
    
    # Config erstellen
    config = ProjectConfig(
        audio_file=audio_path,
        output_file=output_path,
        visual=VisualConfig(
            type=visualizer,
            resolution=resolution,
            fps=fps,
            colors={"primary": "#FF0055", "secondary": "#00CCFF", "background": "#0A0A0A"}
        )
    )
    
    # Progress callback
    def progress_callback(progress: float, message: str):
        if progress_bar is not None:
            progress_bar.progress(min(progress, 1.0))
        if status_text is not None:
            status_text.text(message)
    
    # Pipeline ausführen
    if preview:
        pipeline = PreviewPipeline(config)
        pipeline.run(
            preview_mode=True,
            preview_duration=preview_duration,
            progress_callback=progress_callback
        )
    else:
        pipeline = RenderPipeline(config)
        pipeline.run(
            preview_mode=False,
            progress_callback=progress_callback
        )


def render_with_config_pipeline(
    audio_path: str,
    config_path: str,
    output_path: str,
    progress_bar=None,
    status_text=None
):
    """Rendert mit Config-Datei und echtem Progress."""
    from src.pipeline import RenderPipeline
    from src.types import ProjectConfig
    import json
    
    # Config laden
    with open(config_path) as f:
        config_dict = json.load(f)
    config_dict['audio_file'] = audio_path
    config_dict['output_file'] = output_path
    
    config = ProjectConfig(**config_dict)
    
    # Progress callback
    def progress_callback(progress: float, message: str):
        if progress_bar is not None:
            progress_bar.progress(min(progress, 1.0))
        if status_text is not None:
            status_text.text(message)
    
    pipeline = RenderPipeline(config)
    pipeline.run(preview_mode=False, progress_callback=progress_callback)


# ==================== MAIN APP ====================

def main():
    # Header
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 3.5rem; margin-bottom: 0;">🎵 Audio Visualizer Pro</h1>
        <p style="font-size: 1.3rem; color: #888; margin-top: 0.5rem;">
            KI-optimierte Audio-Visualisierungen für professionelle Musikvideos
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 🎛️ Einstellungen")
        
        # Export-Profil Auswahl
        from src.export_profiles import list_profiles, get_profile, Platform
        
        st.markdown("### 📱 Export-Profil")
        
        profile_options = list_profiles()
        selected_profile_key = st.selectbox(
            "Plattform",
            list(profile_options.keys()),
            format_func=lambda x: profile_options[x],
            help="Wähle ein vordefiniertes Profil für die Zielplattform"
        )
        
        # Zeige Profil-Details
        if selected_profile_key:
            profile = get_profile(Platform(selected_profile_key) if selected_profile_key in [p.value for p in Platform] else Platform.CUSTOM)
            with st.expander(f"ℹ️ {profile.name} Details"):
                st.markdown(f"""
                - **Auflösung:** {profile.resolution[0]}x{profile.resolution[1]}
                - **FPS:** {profile.fps}
                - **Seitenverhältnis:** {profile.aspect_ratio}
                - **Beschreibung:** {profile.description}
                """)
                
                if profile.max_duration:
                    st.markdown(f"- **Max. Dauer:** {profile.max_duration}s")
                if profile.max_file_size:
                    st.markdown(f"- **Max. Dateigröße:** {profile.max_file_size}MB")
        
        # Modus-Auswahl
        st.markdown("---")
        mode = st.radio(
            "Render-Modus",
            ["Schnell (Vorschau)", "Vollständig (HD)"],
            help="Vorschau = 5 Sekunden in 480p, Vollständig = Komplettes Video in HD"
        )
        
        if mode == "Vollständig (HD)":
            col1, col2 = st.columns(2)
            with col1:
                resolution = st.selectbox(
                    "Auflösung",
                    ["1920x1080", "1280x720", "3840x2160", "854x480"],
                    index=0
                )
            with col2:
                fps = st.selectbox(
                    "FPS",
                    [60, 30, 24],
                    index=0
                )
        else:
            resolution = "854x480"
            fps = 30
        
        st.markdown("---")
        
        # Info-Box
        st.markdown("""
        <div class="info-box">
            <strong>💡 Tipp:</strong><br>
            Nutze zuerst die Vorschau, um zu testen, welcher Visualizer am besten passt!
        </div>
        """, unsafe_allow_html=True)
    
    # Tabs für verschiedene Bereiche
    tab_main, tab_preset_editor, tab_preview = st.tabs(["🎬 Hauptbereich", "⚙️ Preset-Editor", "👁️ Live-Preview"])
    
    with tab_main:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 📁 Audio-Datei")
            
            # Drag & Drop Upload mit verbessertem UI
            st.markdown("""
            <style>
            .upload-box {
                border: 3px dashed #667eea;
                border-radius: 15px;
                padding: 40px;
                text-align: center;
                background: rgba(102, 126, 234, 0.1);
                transition: all 0.3s;
            }
            .upload-box:hover {
                background: rgba(102, 126, 234, 0.2);
                border-color: #764ba2;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Audio-Upload mit Drag & Drop
            uploaded_file = st.file_uploader(
                "⬆️ Audio-Datei hierhin ziehen oder klicken zum Auswählen",
                type=['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'wma'],
                help="Unterstützte Formate: MP3, WAV, FLAC, AAC, OGG, M4A, WMA (max. 100MB)",
                key="main_audio_upload",
                label_visibility="visible"
            )
            
            if not uploaded_file:
                st.markdown("""
                <div style="text-align: center; color: #888; padding: 20px;">
                    <p>🎵 Unterstützte Formate:</p>
                    <p><strong>MP3, WAV, FLAC, AAC, OGG, M4A</strong></p>
                    <p style="font-size: 0.8rem;">Maximale Dateigröße: 100MB</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Oder URL-Import
            st.markdown("---")
            st.markdown("<p style='text-align: center; color: #888;'>oder</p>", unsafe_allow_html=True)
            
            url_input = st.text_input(
                "🌐 Audio-URL eingeben",
                placeholder="https://example.com/song.mp3",
                help="Direktlink zu einer Audio-Datei (muss CORS-kompatibel sein)"
            )
            
            if url_input and not uploaded_file:
                with st.spinner("Lade Audio von URL..."):
                    try:
                        import urllib.request
                        import urllib.error
                        
                        # Prüfe URL
                        if not url_input.startswith(('http://', 'https://')):
                            st.error("URL muss mit http:// oder https:// beginnen")
                        else:
                            # Lade Datei
                            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                            urllib.request.urlretrieve(url_input, temp_file.name)
                            temp_file.close()
                            
                            # Erstelle UploadedFile-ähnliches Objekt
                            class URLFile:
                                def __init__(self, path, name):
                                    self.name = name
                                    self.path = path
                                    
                                def getvalue(self):
                                    with open(self.path, 'rb') as f:
                                        return f.read()
                            
                            uploaded_file = URLFile(temp_file.name, url_input.split('/')[-1] or "audio.mp3")
                            st.success(f"Audio geladen: {uploaded_file.name}")
                            
                    except urllib.error.URLError as e:
                        st.error(f"URL-Fehler: {e}")
                    except Exception as e:
                        st.error(f"Fehler beim Laden: {e}")
            
            # Batch-Upload Option
            st.markdown("---")
            with st.expander("📂 Batch-Upload (mehrere Dateien)"):
                batch_files = st.file_uploader(
                    "Mehrere Audio-Dateien auswählen",
                    type=['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'],
                    accept_multiple_files=True,
                    key="batch_upload"
                )
                
                if batch_files:
                    st.info(f"{len(batch_files)} Dateien ausgewählt")
                    st.session_state['batch_files'] = batch_files
                    
                    # Liste der Dateien anzeigen
                    for f in batch_files:
                        col_name, col_size = st.columns([3, 1])
                        with col_name:
                            st.text(f"📄 {f.name}")
                        with col_size:
                            size_mb = len(f.getvalue()) / (1024 * 1024)
                            st.text(f"{size_mb:.1f} MB")
            
            # Audio-Player
            if uploaded_file:
                st.audio(uploaded_file, format=f'audio/{uploaded_file.name.split(".")[-1]}')
                
                # Audio-Info anzeigen (falls analysiert)
                with st.spinner("Analysiere Audio..."):
                    try:
                        # Temporär speichern für Analyse
                        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{uploaded_file.name.split(".")[-1]}')
                        temp_audio.write(uploaded_file.getvalue())
                        temp_audio.close()
                        
                        analyzer = AudioAnalyzer()
                        features = analyzer.analyze(temp_audio.name, fps=30)
                        
                        st.markdown(f"""
                        <div class="preview-card">
                            <h4>📊 Audio-Analyse</h4>
                            <p>🎵 <strong>Dauer:</strong> {features.duration:.1f} Sekunden</p>
                            <p>⏱️ <strong>Tempo:</strong> {features.tempo:.0f} BPM</p>
                            <p>🎼 <strong>Key:</strong> {features.key or 'Unbekannt'}</p>
                            <p>🎹 <strong>Modus:</strong> {features.mode}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    except Exception as e:
                        st.warning(f"Audio-Analyse fehlgeschlagen: {e}")
        
        with col2:
            st.markdown("### 🎨 Visualizer")
            
            # Config-Preset oder manuelle Auswahl
            use_preset = st.checkbox("Config-Preset verwenden", value=False)
            
            if use_preset:
                presets = get_config_presets()
                selected_preset = st.selectbox(
                    "Config-Preset",
                    list(presets.keys()),
                    format_func=lambda x: f"{x} ({presets[x]['visual']})"
                )
                selected_visualizer = presets[selected_preset]['visual']
                config_path = presets[selected_preset]['file']
            else:
                # Visualizer-Auswahl
                available_visualizers = get_available_visualizers()
                
                selected_visualizer = st.selectbox(
                    "Visualizer auswählen",
                    available_visualizers,
                    format_func=lambda x: f"{get_visualizer_info(x)['emoji']} {x.replace('_', ' ').title()}"
                )
                
                # Visualizer-Info anzeigen
                info = get_visualizer_info(selected_visualizer)
                st.markdown(f"""
                <div class="preview-card" style="border-left: 4px solid {info['color']};">
                    <p style="margin: 0;"><strong>{info['description']}</strong></p>
                    <p style="margin: 5px 0 0 0; color: #888; font-size: 0.9rem;">
                        Best for: {info['best_for']}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                config_path = None
        
        # Render-Bereich
        st.markdown("---")
        
        if uploaded_file:
            col_render1, col_render2, col_render3 = st.columns([1, 2, 1])
            
            with col_render2:
                button_text = "🎬 Vorschau rendern" if mode == "Schnell (Vorschau)" else "🎬 Video rendern"
                
                if st.button(button_text, use_container_width=True):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        # Temporäre Dateien
                        temp_dir = tempfile.mkdtemp()
                        audio_path = os.path.join(temp_dir, uploaded_file.name)
                        
                        with open(audio_path, 'wb') as f:
                            f.write(uploaded_file.getvalue())
                        
                        output_filename = f"visualization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                        output_path = os.path.join(temp_dir, output_filename)
                        
                        status_text.text("Starte Rendering...")
                        
                        # Rendern mit echtem Progress
                        if use_preset and config_path:
                            render_with_config_pipeline(
                                audio_path, config_path, output_path,
                                progress_bar=progress_bar,
                                status_text=status_text
                            )
                        elif mode == "Schnell (Vorschau)":
                            render_with_pipeline(
                                audio_path, selected_visualizer, output_path,
                                resolution=(854, 480),
                                fps=30,
                                preview=True,
                                preview_duration=5.0,
                                progress_bar=progress_bar,
                                status_text=status_text
                            )
                        else:
                            width, height = map(int, resolution.split('x'))
                            render_with_pipeline(
                                audio_path, selected_visualizer, output_path,
                                resolution=(width, height),
                                fps=fps,
                                preview=False,
                                progress_bar=progress_bar,
                                status_text=status_text
                            )
                        
                        if os.path.exists(output_path):
                            st.markdown("""
                            <div class="success-box">
                                <strong>Rendering erfolgreich!</strong><br>
                                Dein Video ist bereit zum Download.
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Video anzeigen
                            with open(output_path, 'rb') as f:
                                video_bytes = f.read()
                                st.video(video_bytes)
                            
                            # Download-Button
                            st.download_button(
                                label="📥 Video herunterladen",
                                data=video_bytes,
                                file_name=output_filename,
                                mime="video/mp4",
                                use_container_width=True
                            )
                            
                            # Aufräumen
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            
                        else:
                            st.error("Rendering fehlgeschlagen. Details siehe Konsole.")
                            
                    except Exception as e:
                        st.error(f"Fehler: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
        else:
            st.info("👆 Lade zuerst eine Audio-Datei hoch, um zu beginnen!")
    
    # Preset-Editor Tab
    with tab_preset_editor:
        render_preset_editor()
    
    # Live-Preview Tab
    with tab_preview:
        st.markdown("### 👁️ Live-Frame-Preview")
        st.markdown("Rendert einzelne Frames direkt in der GUI ohne FFmpeg.")
        
        if uploaded_file:
            col_preview_controls, col_preview_display = st.columns([1, 2])
            
            with col_preview_controls:
                # Preview-Einstellungen
                preview_visualizer = st.selectbox(
                    "Visualizer für Preview",
                    get_available_visualizers(),
                    format_func=lambda x: f"{get_visualizer_info(x)['emoji']} {x.replace('_', ' ').title()}",
                    key="preview_visualizer_select"
                )
                
                preview_frame = st.slider(
                    "Frame",
                    0, 100, 0,
                    help="Zeitpunkt im Audio (approximiert)"
                )
                
                preview_resolution = st.selectbox(
                    "Preview-Auflösung",
                    ["640x360", "854x480", "320x180"],
                    index=0,
                    key="preview_res"
                )
                
                if st.button("🎨 Frame rendern", use_container_width=True):
                    with st.spinner("Rendere Frame..."):
                        try:
                            from src.live_preview import LivePreview
                            
                            # Temp-Datei erstellen
                            temp_dir = tempfile.mkdtemp()
                            audio_path = os.path.join(temp_dir, uploaded_file.name)
                            with open(audio_path, 'wb') as f:
                                f.write(uploaded_file.getvalue())
                            
                            # Preview generieren
                            width, height = map(int, preview_resolution.split('x'))
                            preview = LivePreview(preview_visualizer, (width, height))
                            preview.analyze_audio(audio_path)
                            preview.setup_visualizer()
                            
                            # Frame berechnen
                            frame_idx = int(preview_frame / 100 * preview.features.frame_count)
                            frame = preview.render_frame(frame_idx)
                            
                            # Speichere in Session State
                            st.session_state['preview_frame'] = frame
                            st.session_state['preview_visualizer'] = preview_visualizer
                            
                        except Exception as e:
                            st.error(f"Fehler: {e}")
                            import traceback
                            st.code(traceback.format_exc())
                
                # Vergleichsmodus
                st.markdown("---")
                st.markdown("#### 🔄 Vergleich")
                
                if st.button("Alle Visualizer vergleichen", use_container_width=True):
                    with st.spinner("Rendere alle Visualizer..."):
                        try:
                            from src.live_preview import compare_visualizers
                            
                            temp_dir = tempfile.mkdtemp()
                            audio_path = os.path.join(temp_dir, uploaded_file.name)
                            with open(audio_path, 'wb') as f:
                                f.write(uploaded_file.getvalue())
                            
                            visualizers = get_available_visualizers()
                            width, height = map(int, preview_resolution.split('x'))
                            
                            results = compare_visualizers(
                                audio_path,
                                visualizers[:6],  # Max 6 für Performance
                                frame_idx=0,
                                resolution=(width, height)
                            )
                            
                            st.session_state['compare_results'] = results
                            
                        except Exception as e:
                            st.error(f"Fehler: {e}")
            
            with col_preview_display:
                # Zeige gerenderten Frame
                if 'preview_frame' in st.session_state:
                    from PIL import Image
                    
                    frame = st.session_state['preview_frame']
                    img = Image.fromarray(frame)
                    
                    st.image(
                        img,
                        caption=f"Frame gerendert mit '{st.session_state.get('preview_visualizer', 'unknown')}'",
                        use_column_width=True
                    )
                    
                    # Download-Button für Frame
                    buf = io.BytesIO()
                    img.save(buf, format='PNG')
                    st.download_button(
                        "📥 Frame als PNG",
                        buf.getvalue(),
                        f"frame_{preview_frame}.png",
                        "image/png"
                    )
                
                # Zeige Vergleich
                if 'compare_results' in st.session_state:
                    st.markdown("#### 🎨 Visualizer-Vergleich")
                    
                    results = st.session_state['compare_results']
                    cols = st.columns(3)
                    
                    for idx, (vis_name, frame) in enumerate(results.items()):
                        if frame is not None:
                            with cols[idx % 3]:
                                img = Image.fromarray(frame)
                                st.image(
                                    img,
                                    caption=vis_name.replace('_', ' ').title(),
                                    use_column_width=True
                                )
        else:
            st.info("👆 Lade zuerst eine Audio-Datei hoch, um den Live-Preview zu nutzen!")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p>Made with ❤️ | Audio Visualizer Pro</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
