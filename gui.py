"""
Audio Visualizer Pro - Moderne GUI

Eine komplette Web-basierte GUI mit Streamlit.
Alle Funktionen intuitiv bedienbar ohne Kommandozeile.
"""

import streamlit as st
import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any
import numpy as np
from PIL import Image

# Füge src zum Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent))

from src.visuals.registry import VisualizerRegistry
from src.analyzer import AudioAnalyzer
from src.types import ProjectConfig, VisualConfig
from src.pipeline import RenderPipeline, PreviewPipeline
from src.export_profiles import ExportProfile, Platform, get_profile, list_profiles
from src.live_preview import LivePreview, compare_visualizers
from src.settings import get_settings
from src.logger import get_logger

logger = get_logger("audio_visualizer.gui")

# ============================================================================
# KONFIGURATION & STATE MANAGEMENT
# ============================================================================

def init_session_state():
    """Initialisiert Session State Variablen."""
    defaults = {
        'audio_path': None,
        'audio_name': None,
        'features': None,
        'preview_frame': None,
        'compare_results': None,
        'rendering': False,
        'output_path': None,
        'batch_files': [],
        'batch_results': [],
        'config': {
            'visualizer': 'pulsing_core',
            'resolution': (1920, 1080),
            'fps': 60,
            'colors': {
                'primary': '#FF0055',
                'secondary': '#00CCFF',
                'background': '#0A0A0A'
            },
            'params': {
                'intensity': 1.0,
                'speed': 1.0,
                'bar_count': 40,
            },
            'postprocess': {
                'contrast': 1.0,
                'saturation': 1.0,
                'brightness': 1.0,
                'grain': 0.0,
                'vignette': 0.0,
                'chromatic_aberration': 0.0
            }
        }
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ============================================================================
# CSS STYLING
# ============================================================================

def load_css():
    """Lädt custom CSS für modernes Design."""
    st.markdown("""
    <style>
        /* Haupt-Layout */
        .main {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #ffffff;
        }
        
        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a1a2e 0%, #0f0f23 100%);
            border-right: 1px solid rgba(102, 126, 234, 0.3);
        }
        
        /* Buttons */
        .stButton>button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 12px 24px;
            font-weight: 600;
            transition: all 0.3s ease;
            width: 100%;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }
        .stButton>button:disabled {
            background: #444;
            cursor: not-allowed;
            transform: none;
        }
        
        /* Primary Action Button */
        .primary-btn {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
            font-size: 1.1em;
            padding: 16px 32px !important;
        }
        
        /* Cards */
        .card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 20px;
            margin: 10px 0;
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
        }
        
        .card-highlight {
            background: rgba(102, 126, 234, 0.1);
            border: 1px solid rgba(102, 126, 234, 0.3);
        }
        
        /* Upload Box */
        .upload-box {
            border: 3px dashed rgba(102, 126, 234, 0.5);
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            background: rgba(102, 126, 234, 0.05);
            transition: all 0.3s ease;
        }
        .upload-box:hover {
            background: rgba(102, 126, 234, 0.1);
            border-color: #667eea;
        }
        
        /* Progress Bar */
        .stProgress .st-bo {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        }
        
        /* Success/Error Messages */
        .success-msg {
            background: rgba(39, 174, 96, 0.2);
            border-left: 4px solid #27ae60;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
        
        .error-msg {
            background: rgba(231, 76, 60, 0.2);
            border-left: 4px solid #e74c3c;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
        
        .info-msg {
            background: rgba(52, 152, 219, 0.2);
            border-left: 4px solid #3498db;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
        
        /* Visualizer Grid */
        .viz-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 10px;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px 10px 0 0;
            padding: 10px 20px;
            border: none;
        }
        .stTabs [aria-selected="true"] {
            background: rgba(102, 126, 234, 0.3) !important;
        }
        
        /* Selectbox, Slider Styling */
        .stSelectbox, .stSlider {
            background: rgba(255, 255, 255, 0.05);
        }
        
        /* Headers */
        h1, h2, h3 {
            color: #ffffff !important;
            font-weight: 600;
        }
        
        /* Audio Info */
        .audio-info {
            background: rgba(102, 126, 234, 0.1);
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
        }
        
        /* Feature Tags */
        .feature-tag {
            display: inline-block;
            background: rgba(102, 126, 234, 0.3);
            border-radius: 15px;
            padding: 4px 12px;
            margin: 2px;
            font-size: 0.85em;
        }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# HILFSFUNKTIONEN
# ============================================================================

def get_visualizer_info() -> Dict[str, Dict]:
    """Gibt Informationen über alle Visualizer zurück."""
    return {
        'pulsing_core': {
            'emoji': '🔴', 'name': 'Pulsing Core',
            'description': 'Pulsierender Kreis mit Chroma-Farben',
            'best_for': 'EDM, Pop, Dance',
            'color': '#FF0055',
            'category': 'Bass'
        },
        'spectrum_bars': {
            'emoji': '📊', 'name': 'Spectrum Bars',
            'description': '40-Balken Equalizer',
            'best_for': 'Rock, Hip-Hop, Electronic',
            'color': '#00CCFF',
            'category': 'Equalizer'
        },
        'chroma_field': {
            'emoji': '✨', 'name': 'Chroma Field',
            'description': 'Partikel-Feld basierend auf Tonart',
            'best_for': 'Ambient, Jazz, Klassik',
            'color': '#9D4EDD',
            'category': 'Ambient'
        },
        'particle_swarm': {
            'emoji': '🔥', 'name': 'Particle Swarm',
            'description': 'Physik-basierte Partikel-Explosionen',
            'best_for': 'Dubstep, Trap, Bass Music',
            'color': '#FF6B35',
            'category': 'Energetic'
        },
        'typographic': {
            'emoji': '📝', 'name': 'Typographic',
            'description': 'Minimalistisch mit Wellenform',
            'best_for': 'Podcasts, Sprache, Audiobooks',
            'color': '#00F5FF',
            'category': 'Minimal'
        },
        'neon_oscilloscope': {
            'emoji': '💠', 'name': 'Neon Oscilloscope',
            'description': 'Retro-futuristischer Oszilloskop',
            'best_for': 'Synthwave, Cyberpunk, Retro',
            'color': '#00F5FF',
            'category': 'Retro'
        },
        'sacred_mandala': {
            'emoji': '🕉️', 'name': 'Sacred Mandala',
            'description': 'Heilige Geometrie mit rotierenden Mustern',
            'best_for': 'Meditation, Ambient, Yoga',
            'color': '#FF9E00',
            'category': 'Spiritual'
        },
        'liquid_blobs': {
            'emoji': '💧', 'name': 'Liquid Blobs',
            'description': 'Flüssige MetaBall-ähnliche Blobs',
            'best_for': 'House, Techno, Deep House',
            'color': '#00D9FF',
            'category': 'Fluid'
        },
        'neon_wave_circle': {
            'emoji': '⭕', 'name': 'Neon Wave Circle',
            'description': 'Konzentrische Neon-Ringe mit Wellen',
            'best_for': 'EDM, Techno, Trance',
            'color': '#39FF14',
            'category': 'Neon'
        },
        'frequency_flower': {
            'emoji': '🌸', 'name': 'Frequency Flower',
            'description': 'Organische Blumen mit Audio-reaktiven Blütenblättern',
            'best_for': 'Indie, Folk, Pop',
            'color': '#FFB7B2',
            'category': 'Organic'
        },
        'waveform_line': {
            'emoji': '📈', 'name': 'Waveform Line',
            'description': 'Oszilloskop-ähnliche Wellenform-Linie',
            'best_for': 'Podcasts, Sprache, Akustik',
            'color': '#00FF96',
            'category': 'Waveform'
        },
        '3d_spectrum': {
            'emoji': '🏙️', 'name': '3D Spectrum',
            'description': '3D-Balken-Equalizer mit Perspektive',
            'best_for': 'EDM, Techno, Elektronisch',
            'color': '#FF00FF',
            'category': '3D'
        },
        'circular_wave': {
            'emoji': '🌀', 'name': 'Circular Wave',
            'description': 'Kreisförmige, rotierende Wellenform',
            'best_for': 'Ambient, Meditation, Atmosphärisch',
            'color': '#9D4EDD',
            'category': 'Waveform'
        }
    }

def get_resolution_options() -> List[Tuple[str, Tuple[int, int]]]:
    """Gibt verfügbare Auflösungen zurück."""
    return [
        ("4K Ultra HD (3840x2160)", (3840, 2160)),
        ("Full HD (1920x1080)", (1920, 1080)),
        ("HD (1280x720)", (1280, 720)),
        ("Square HD (1080x1080)", (1080, 1080)),
        ("Vertical HD (1080x1920)", (1080, 1920)),
        ("Preview (854x480)", (854, 480)),
        ("Small (640x360)", (640, 360)),
    ]

def get_profile_options() -> List[Tuple[str, str, Any]]:
    """Gibt Export-Profile zurück."""
    return [
        ("🎬 YouTube 1080p", "youtube", Platform.YOUTUBE),
        ("🎬 YouTube 4K", "youtube_4k", "youtube_4k"),
        ("📱 Instagram Feed", "instagram_feed", Platform.INSTAGRAM_FEED),
        ("📱 Instagram Reels", "instagram_reels", Platform.INSTAGRAM_REELS),
        ("🎵 TikTok", "tiktok", Platform.TIKTOK),
        ("🎵 TikTok HD", "tiktok_hd", "tiktok_hd"),
        ("⚙️ Benutzerdefiniert", "custom", Platform.CUSTOM),
    ]

def save_uploaded_file(uploaded_file) -> Optional[str]:
    """Speichert eine hochgeladene Datei temporär."""
    if uploaded_file is None:
        return None
    
    try:
        # Bereinige alte Temp-Dateien zuerst
        _cleanup_old_temp_files()
        
        # Erstelle eindeutigen Temp-Ordner
        temp_dir = tempfile.mkdtemp(prefix="avp_")
        file_path = os.path.join(temp_dir, uploaded_file.name)
        
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.getvalue())
        
        # Speichere Temp-Dir für spätere Bereinigung
        if 'temp_dirs' not in st.session_state:
            st.session_state.temp_dirs = []
        st.session_state.temp_dirs.append(temp_dir)
        
        return file_path
    except Exception as e:
        logger.error(f"Fehler beim Speichern: {e}")
        st.error(f"Fehler beim Speichern der Datei: {e}")
        return None


def _cleanup_old_temp_files():
    """Bereinigt alte Temp-Verzeichnisse."""
    if 'temp_dirs' in st.session_state:
        for temp_dir in st.session_state.temp_dirs[:]:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                st.session_state.temp_dirs.remove(temp_dir)
            except Exception:
                pass  # Ignoriere Bereinigungsfehler

def analyze_audio_file(audio_path: str) -> Optional[Any]:
    """Analysiert eine Audio-Datei."""
    try:
        analyzer = AudioAnalyzer()
        features = analyzer.analyze(audio_path, fps=30)
        return features
    except Exception as e:
        logger.error(f"Analyse-Fehler: {e}")
        st.error(f"Audio-Analyse fehlgeschlagen: {e}")
        return None

def render_live_preview_frame(
    audio_path: str,
    visualizer: str,
    frame_percent: int,
    resolution: Tuple[int, int] = (640, 360)
) -> Optional[np.ndarray]:
    """Rendert einen einzelnen Frame für Live-Preview."""
    try:
        preview = LivePreview(visualizer, resolution)
        preview.analyze_audio(audio_path)
        preview.setup_visualizer(st.session_state.config['colors'])
        
        frame_idx = int(frame_percent / 100 * preview.features.frame_count)
        frame = preview.render_frame(frame_idx)
        return frame
    except Exception as e:
        logger.error(f"Preview-Fehler: {e}")
        return None

def render_video_with_progress(
    audio_path: str,
    visualizer: str,
    output_path: str,
    resolution: Tuple[int, int],
    fps: int,
    colors: Dict[str, str],
    postprocess: Dict[str, float],
    profile_key: str = "custom",
    preview_mode: bool = False,
    preview_duration: float = 5.0
) -> bool:
    """Rendert Video mit Fortschrittsanzeige."""
    
    config = ProjectConfig(
        audio_file=audio_path,
        output_file=output_path,
        visual=VisualConfig(
            type=visualizer,
            resolution=resolution,
            fps=fps,
            colors=colors
        ),
        postprocess=postprocess
    )
    
    # Export-Profil laden
    export_profile = None
    if profile_key != "custom":
        try:
            if profile_key == "youtube_4k":
                export_profile = get_profile("youtube_4k")
            elif profile_key == "tiktok_hd":
                export_profile = get_profile("tiktok_hd")
            else:
                export_profile = get_profile(Platform(profile_key))
        except Exception as e:
            logger.warning(f"Konnte Export-Profil nicht laden: {e}")
    
    # Fortschritt initialisieren
    progress_bar = st.progress(0.0)
    status_text = st.empty()
    
    def progress_callback(progress: float, message: str):
        progress_bar.progress(min(progress, 1.0))
        status_text.text(message)
    
    try:
        if preview_mode:
            pipeline = PreviewPipeline(config)
            pipeline.run(
                preview_mode=True,
                preview_duration=preview_duration,
                progress_callback=progress_callback
            )
        else:
            pipeline = RenderPipeline(config, export_profile=export_profile)
            pipeline.run(
                preview_mode=False,
                progress_callback=progress_callback
            )
        
        progress_bar.empty()
        status_text.empty()
        return True
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        logger.error(f"Render-Fehler: {e}")
        st.error(f"Rendering fehlgeschlagen: {e}")
        return False

# ============================================================================
# SIDEBAR NAVIGATION
# ============================================================================

def render_sidebar():
    """Rendert die Sidebar-Navigation."""
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <h1 style="font-size: 1.8rem; margin: 0;">🎵 Audio Visualizer</h1>
            <p style="color: #888; margin: 5px 0 0 0;">Pro Edition</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Navigation
        st.markdown("### 📍 Navigation")
        
        page = st.radio(
            "Seite wählen:",
            ["🏠 Start", "🎨 Visualizer", "⚙️ Einstellungen", "📚 Hilfe"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Status-Anzeige
        if st.session_state.audio_path:
            st.markdown("### 📊 Status")
            st.markdown(f"""
            <div class="audio-info">
                <p style="margin: 0; font-size: 0.9em;">
                    <strong>🎵 Audio geladen</strong><br>
                    {st.session_state.audio_name}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.session_state.features:
                f = st.session_state.features
                st.markdown(f"""
                <div style="font-size: 0.8em; color: #888;">
                    ⏱️ {f.duration:.1f}s | 🎼 {f.tempo:.0f} BPM
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Keine Audio-Datei geladen")
        
        st.markdown("---")
        
        # System-Info
        st.markdown("<p style='color: #666; font-size: 0.75em; text-align: center;'>v2.0 | KI-optimiert</p>", unsafe_allow_html=True)
        
        return page

# ============================================================================
# HAUPTSEITEN
# ============================================================================

def render_start_page():
    """Rendert die Startseite mit Audio-Upload."""
    st.markdown("""
    <div style="text-align: center; padding: 30px 0;">
        <h1 style="font-size: 3rem; margin-bottom: 10px;">🎵 Audio Visualizer Pro</h1>
        <p style="font-size: 1.2rem; color: #888; max-width: 600px; margin: 0 auto;">
            Erstelle atemberaubende Musikvideos mit KI-optimierten Visualisierungen
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Upload-Bereich
    st.markdown("### 📁 Audio-Datei hochladen")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Wähle eine Audio-Datei",
            type=['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'wma'],
            help="Unterstützte Formate: MP3, WAV, FLAC, AAC, OGG, M4A, WMA"
        )
        
        if uploaded_file:
            with st.spinner("📊 Analysiere Audio..."):
                audio_path = save_uploaded_file(uploaded_file)
                if audio_path:
                    features = analyze_audio_file(audio_path)
                    if features:
                        st.session_state.audio_path = audio_path
                        st.session_state.audio_name = uploaded_file.name
                        st.session_state.features = features
                        st.success("✅ Audio erfolgreich analysiert!")
                        st.rerun()
    
    with col2:
        st.markdown("""
        <div class="card" style="height: 100%;">
            <h4>💡 Tipps</h4>
            <ul style="font-size: 0.9em; padding-left: 20px;">
                <li>Max. 2 GB Dateigröße</li>
                <li>Alle gängigen Formate</li>
                <li>Automatische Analyse</li>
                <li>Smartes Caching</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Batch-Upload
    with st.expander("📂 Batch-Upload (mehrere Dateien)"):
        batch_files = st.file_uploader(
            "Mehrere Audio-Dateien auswählen",
            type=['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'],
            accept_multiple_files=True
        )
        
        if batch_files:
            st.session_state.batch_files = batch_files
            st.info(f"📁 {len(batch_files)} Dateien ausgewählt")
            
            for f in batch_files:
                col_name, col_size = st.columns([3, 1])
                with col_name:
                    st.text(f"📄 {f.name}")
                with col_size:
                    size_mb = len(f.getvalue()) / (1024 * 1024)
                    st.text(f"{size_mb:.1f} MB")
    
    # Audio-Info anzeigen wenn vorhanden
    if st.session_state.features:
        st.markdown("---")
        st.markdown("### 📊 Audio-Informationen")
        
        f = st.session_state.features
        
        cols = st.columns(4)
        with cols[0]:
            st.metric("⏱️ Dauer", f"{f.duration:.1f}s")
        with cols[1]:
            st.metric("🎼 Tempo", f"{f.tempo:.0f} BPM")
        with cols[2]:
            st.metric("🎹 Key", f.key or "Unbekannt")
        with cols[3]:
            st.metric("🎵 Modus", f.mode.title())
        
        # Audio-Player
        if st.session_state.audio_path:
            st.audio(st.session_state.audio_path)

def render_visualizer_page():
    """Rendert die Visualizer-Auswahl und Konfiguration."""
    if not st.session_state.audio_path:
        st.warning("⚠️ Bitte zuerst eine Audio-Datei auf der Startseite laden!")
        return
    
    st.markdown("### 🎨 Visualizer auswählen")
    
    # Visualizer-Kategorien
    viz_info = get_visualizer_info()
    categories = {}
    for key, info in viz_info.items():
        cat = info['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((key, info))
    
    # Kategorie-Auswahl
    selected_category = st.selectbox(
        "Kategorie",
        ["Alle"] + list(categories.keys())
    )
    
    # Visualizer-Grid
    if selected_category == "Alle":
        display_vizs = [(k, v) for k, v in viz_info.items()]
    else:
        display_vizs = categories[selected_category]
    
    # Visualizer als Radio-Buttons mit Icons
    viz_options = {f"{info['emoji']} {info['name']}": key for key, info in display_vizs}
    
    selected_viz_display = st.radio(
        "Visualizer",
        list(viz_options.keys()),
        horizontal=True,
        label_visibility="collapsed"
    )
    
    selected_viz = viz_options[selected_viz_display]
    st.session_state.config['visualizer'] = selected_viz
    
    # Visualizer-Details
    info = viz_info[selected_viz]
    
    st.markdown(f"""
    <div class="card card-highlight">
        <h4>{info['emoji']} {info['name']}</h4>
        <p>{info['description']}</p>
        <p style="color: #888; font-size: 0.9em;">
            <strong>Best for:</strong> {info['best_for']}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Live-Preview
    st.markdown("---")
    st.markdown("### 👁️ Live-Vorschau")
    
    preview_col1, preview_col2 = st.columns([1, 2])
    
    with preview_col1:
        frame_pos = st.slider(
            "Zeitpunkt im Audio",
            0, 100, 50,
            help="Wähle einen Zeitpunkt für die Vorschau"
        )
        
        preview_res = st.selectbox(
            "Vorschau-Qualität",
            ["Schnell (320x180)", "Mittel (640x360)", "Hoch (854x480)"],
            index=1
        )
        
        res_map = {
            "Schnell (320x180)": (320, 180),
            "Mittel (640x360)": (640, 360),
            "Hoch (854x480)": (854, 480)
        }
        
        if st.button("🎨 Vorschau rendern", use_container_width=True):
            with st.spinner("Rendere..."):
                frame = render_live_preview_frame(
                    st.session_state.audio_path,
                    selected_viz,
                    frame_pos,
                    res_map[preview_res]
                )
                if frame is not None:
                    st.session_state.preview_frame = frame
    
    with preview_col2:
        if st.session_state.preview_frame is not None:
            img = Image.fromarray(st.session_state.preview_frame)
            st.image(img, use_column_width=True)
        else:
            st.info("Klicke 'Vorschau rendern' um eine Vorschau zu sehen")
    
    # Visualizer-Vergleich
    with st.expander("🔄 Alle Visualizer vergleichen"):
        if st.button("Alle rendern (max. 6)", use_container_width=True):
            with st.spinner("Rendere alle Visualizer..."):
                try:
                    results = compare_visualizers(
                        st.session_state.audio_path,
                        list(viz_info.keys())[:6],
                        frame_idx=0,
                        resolution=(320, 180)
                    )
                    st.session_state.compare_results = results
                except Exception as e:
                    st.error(f"Fehler: {e}")
        
        if st.session_state.compare_results:
            results = st.session_state.compare_results
            cols = st.columns(3)
            for idx, (vis_name, frame) in enumerate(results.items()):
                if frame is not None:
                    with cols[idx % 3]:
                        img = Image.fromarray(frame)
                        st.image(img, caption=viz_info.get(vis_name, {}).get('name', vis_name))

def render_settings_page():
    """Rendert die Einstellungsseite."""
    st.markdown("### ⚙️ Export-Einstellungen")
    
    # Export-Profil
    st.markdown("#### 📱 Plattform / Export-Profil")
    
    profile_options = get_profile_options()
    profile_display = [p[0] for p in profile_options]
    
    selected_profile_idx = st.selectbox(
        "Profil",
        range(len(profile_display)),
        format_func=lambda i: profile_display[i]
    )
    
    selected_profile = profile_options[selected_profile_idx][1]
    
    # Profil-Details anzeigen
    if selected_profile != "custom":
        try:
            if selected_profile == "youtube_4k":
                profile = get_profile("youtube_4k")
            elif selected_profile == "tiktok_hd":
                profile = get_profile("tiktok_hd")
            else:
                profile = get_profile(Platform(selected_profile))
            
            st.markdown(f"""
            <div class="card" style="font-size: 0.9em;">
                <strong>{profile.name}</strong><br>
                Auflösung: {profile.resolution[0]}x{profile.resolution[1]}<br>
                FPS: {profile.fps} | Seitenverhältnis: {profile.aspect_ratio}
            </div>
            """, unsafe_allow_html=True)
            
            # Übernehme Profil-Einstellungen
            st.session_state.config['resolution'] = profile.resolution
            st.session_state.config['fps'] = profile.fps
        except Exception as e:
            logger.warning(f"Could not load profile: {e}")
            pass
    
    # Manuelle Einstellungen (nur bei Custom)
    if selected_profile == "custom":
        st.markdown("---")
        st.markdown("#### 📐 Manuelle Einstellungen")
        
        col1, col2 = st.columns(2)
        
        with col1:
            res_options = get_resolution_options()
            res_display = [r[0] for r in res_options]
            
            selected_res_idx = st.selectbox(
                "Auflösung",
                range(len(res_display)),
                index=1,
                format_func=lambda i: res_display[i]
            )
            st.session_state.config['resolution'] = res_options[selected_res_idx][1]
        
        with col2:
            fps = st.selectbox(
                "FPS (Bilder pro Sekunde)",
                [24, 30, 60, 120],
                index=2
            )
            st.session_state.config['fps'] = fps
    
    # Farben
    st.markdown("---")
    st.markdown("#### 🎨 Farben")
    
    colors = st.session_state.config['colors']
    
    col_c1, col_c2, col_c3 = st.columns(3)
    
    with col_c1:
        colors['primary'] = st.color_picker(
            "Primärfarbe",
            colors.get('primary', '#FF0055')
        )
    
    with col_c2:
        colors['secondary'] = st.color_picker(
            "Sekundärfarbe",
            colors.get('secondary', '#00CCFF')
        )
    
    with col_c3:
        colors['background'] = st.color_picker(
            "Hintergrund",
            colors.get('background', '#0A0A0A')
        )
    
    # Post-Processing
    st.markdown("---")
    st.markdown("#### ✨ Post-Processing Effekte")
    
    pp = st.session_state.config['postprocess']
    
    col_pp1, col_pp2 = st.columns(2)
    
    with col_pp1:
        pp['contrast'] = st.slider("Kontrast", 0.5, 2.0, pp.get('contrast', 1.0), 0.1)
        pp['saturation'] = st.slider("Sättigung", 0.0, 2.0, pp.get('saturation', 1.0), 0.1)
        pp['brightness'] = st.slider("Helligkeit", 0.5, 2.0, pp.get('brightness', 1.0), 0.1)
    
    with col_pp2:
        pp['grain'] = st.slider("Film Grain", 0.0, 1.0, pp.get('grain', 0.0), 0.05)
        pp['vignette'] = st.slider("Vignette", 0.0, 1.0, pp.get('vignette', 0.0), 0.05)
        pp['chromatic_aberration'] = st.slider("Chromatic Aberration", 0.0, 5.0, pp.get('chromatic_aberration', 0.0), 0.5)
    
    # Rendering
    st.markdown("---")
    st.markdown("### 🎬 Video rendern")
    
    if not st.session_state.audio_path:
        st.warning("⚠️ Keine Audio-Datei geladen")
        return
    
    col_render1, col_render2 = st.columns(2)
    
    with col_render1:
        preview_duration = st.slider("Vorschau-Dauer (Sekunden)", 1, 10, 5)
        
        if st.button("👁️ Vorschau rendern", use_container_width=True):
            with st.spinner("Rendere Vorschau..."):
                temp_dir = tempfile.mkdtemp()
                output_path = os.path.join(temp_dir, "preview.mp4")
                
                success = render_video_with_progress(
                    st.session_state.audio_path,
                    st.session_state.config['visualizer'],
                    output_path,
                    (854, 480),  # Niedrigere Auflösung für Preview
                    30,
                    st.session_state.config['colors'],
                    st.session_state.config['postprocess'],
                    selected_profile,
                    preview_mode=True,
                    preview_duration=preview_duration
                )
                
                if success and os.path.exists(output_path):
                    st.session_state.output_path = output_path
                    st.success("✅ Vorschau fertig!")
                    
                    with open(output_path, 'rb') as f:
                        st.video(f.read())
    
    with col_render2:
        if st.button("🎬 FINALES VIDEO RENDERN", use_container_width=True, type="primary"):
            with st.spinner("Rendere finales Video..."):
                temp_dir = tempfile.mkdtemp()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = os.path.join(temp_dir, f"visualization_{timestamp}.mp4")
                
                success = render_video_with_progress(
                    st.session_state.audio_path,
                    st.session_state.config['visualizer'],
                    output_path,
                    st.session_state.config['resolution'],
                    st.session_state.config['fps'],
                    st.session_state.config['colors'],
                    st.session_state.config['postprocess'],
                    selected_profile,
                    preview_mode=False
                )
                
                if success and os.path.exists(output_path):
                    st.session_state.output_path = output_path
                    st.success("✅ Video fertig!")
                    
                    with open(output_path, 'rb') as f:
                        video_bytes = f.read()
                        st.video(video_bytes)
                        
                        st.download_button(
                            "📥 Video herunterladen",
                            video_bytes,
                            f"visualization_{timestamp}.mp4",
                            "video/mp4",
                            use_container_width=True
                        )

def render_help_page():
    """Rendert die Hilfeseite."""
    st.markdown("### 📚 Hilfe & Dokumentation")
    
    with st.expander("🚀 Schnellstart"):
        st.markdown("""
        1. **Audio hochladen**: Gehe zur Startseite und lade eine Audio-Datei hoch
        2. **Visualizer wählen**: Wähle auf der Visualizer-Seite einen passenden Stil
        3. **Einstellungen**: Passe Farben und Effekte auf der Einstellungsseite an
        4. **Vorschau**: Teste mit der Vorschau-Funktion
        5. **Render**: Erstelle das finale Video
        """)
    
    with st.expander("🎨 Visualizer-Guide"):
        viz_info = get_visualizer_info()
        for key, info in viz_info.items():
            st.markdown(f"**{info['emoji']} {info['name']}** - {info['description']}")
            st.caption(f"Best for: {info['best_for']}")
    
    with st.expander("📱 Export-Profile"):
        st.markdown("""
        - **YouTube 1080p/4K**: Optimiert für YouTube mit bester Qualität
        - **Instagram Feed**: Quadratisches 1:1 Format
        - **Instagram Reels**: Vertikales 9:16 Format
        - **TikTok**: Optimiert für schnelles Uploaden
        - **Benutzerdefiniert**: Eigene Auflösung und FPS wählen
        """)
    
    with st.expander("💡 Tipps für beste Ergebnisse"):
        st.markdown("""
        - **Starte mit Vorschau**: Spart Zeit beim Testen
        - **Wähle den richtigen Visualizer**: Bass-lastige Musik = Spectrum Bars
        - **Farben anpassen**: Primärfarbe für Hauptelemente, Sekundär für Akzente
        - **Post-Processing**: Vignette für Film-Look, Grain für Vintage-Stil
        - **Qualität vs. Geschwindigkeit**: 60 FPS sieht flüssiger aus, braucht aber länger
        """)
    
    with st.expander("⚠️ Fehlerbehebung"):
        st.markdown("""
        **"Audio-Analyse fehlgeschlagen"**
        - Datei zu groß? Versuche eine kürzere Datei oder konvertiere zu MP3
        - Ungültiges Format? Nutze MP3, WAV oder FLAC
        
        **"Rendering fehlgeschlagen"**
        - FFmpeg installiert? Führe `python main.py check` aus
        - Zu wenig Speicher? Schließe andere Programme
        
        **Langsame Performance**
        - Nutze niedrigere Auflösung (720p statt 1080p)
        - Reduziere FPS (30 statt 60)
        - Nutze die Vorschau vor dem finalen Render
        """)
    
    st.markdown("---")
    st.markdown("### 🔧 System-Check")
    
    if st.button("System prüfen", use_container_width=True):
        with st.spinner("Prüfe System..."):
            from src.utils import check_ffmpeg
            
            success, message = check_ffmpeg()
            if success:
                st.success(f"✅ FFmpeg gefunden: {message[:50]}...")
            else:
                st.error(f"❌ FFmpeg nicht gefunden: {message}")
            
            settings = get_settings()
            cache_size = settings.get_cache_size_mb()
            st.info(f"💾 Cache-Größe: {cache_size:.1f} MB")

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """Hauptfunktion der GUI."""
    # Seiten-Config
    st.set_page_config(
        page_title="Audio Visualizer Pro",
        page_icon="🎵",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialisierung
    init_session_state()
    load_css()
    
    # Sidebar
    page = render_sidebar()
    
    # Hauptbereich
    if page == "🏠 Start":
        render_start_page()
    elif page == "🎨 Visualizer":
        render_visualizer_page()
    elif page == "⚙️ Einstellungen":
        render_settings_page()
    elif page == "📚 Hilfe":
        render_help_page()

if __name__ == "__main__":
    main()
