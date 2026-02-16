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
        }
    }
    return info.get(visualizer_name, {
        'emoji': '🎨',
        'description': 'Visualizer',
        'best_for': 'Alle Genres',
        'color': '#ffffff'
    })


def render_preview(audio_path: str, visualizer: str, duration: float = 5.0):
    """Rendert eine Vorschau."""
    output_path = tempfile.mktemp(suffix='.mp4')
    
    cmd = [
        sys.executable, 'main.py', 'render', audio_path,
        '--visual', visualizer,
        '--output', output_path,
        '--preview',
        '--preview-duration', str(duration)
    ]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    return process, output_path


def render_full(audio_path: str, visualizer: str, output_path: str, 
                resolution: str = "1920x1080", fps: int = 60):
    """Rendert das vollständige Video."""
    cmd = [
        sys.executable, 'main.py', 'render', audio_path,
        '--visual', visualizer,
        '--output', output_path,
        '--resolution', resolution,
        '--fps', str(fps)
    ]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    return process


def render_with_config(audio_path: str, config_path: str, output_path: str):
    """Rendert mit Config-Datei."""
    cmd = [
        sys.executable, 'main.py', 'render', audio_path,
        '--config', config_path,
        '--output', output_path
    ]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    return process


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
        
        # Modus-Auswahl
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
    
    # Hauptbereich
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📁 Audio-Datei")
        
        # Audio-Upload
        uploaded_file = st.file_uploader(
            "Wähle eine Audio-Datei",
            type=['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'],
            help="Unterstützte Formate: MP3, WAV, FLAC, AAC, OGG, M4A"
        )
        
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
                    
                    if use_preset and config_path:
                        process = render_with_config(audio_path, config_path, output_path)
                    elif mode == "Schnell (Vorschau)":
                        process, output_path = render_preview(audio_path, selected_visualizer)
                    else:
                        process = render_full(audio_path, selected_visualizer, output_path, resolution, fps)
                    
                    # Fortschritt simulieren (da wir keine direkte Rückmeldung vom Prozess haben)
                    import time
                    for i in range(100):
                        time.sleep(0.1)
                        progress_bar.progress(i + 1)
                        
                        # Versuche Output zu lesen
                        if process.poll() is not None:
                            progress_bar.progress(100)
                            break
                    
                    # Warte auf Prozess
                    stdout, stderr = process.communicate()
                    
                    if process.returncode == 0 and os.path.exists(output_path):
                        st.markdown(f"""
                        <div class="success-box">
                            <strong>✅ Rendering erfolgreich!</strong><br>
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
                        st.error(f"Rendering fehlgeschlagen:\n{stderr}")
                        
                except Exception as e:
                    st.error(f"Fehler: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
    else:
        st.info("👆 Lade zuerst eine Audio-Datei hoch, um zu beginnen!")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p>Made with ❤️ | Audio Visualizer Pro</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
