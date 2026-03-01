"""
Audio Visualizer Pro - Moderne GUI v2.0 (FIXED)

Diese Version zeigt eine modernisierte GUI mit:
- Stepper-Navigation statt Sidebar
- Glassmorphism Design
- Verbesserter Visualizer-Galerie
- Wizard für neue Visualizer

BUGFIXES:
- Syntax Error in Wizard behoben
- Session State Initialisierung korrigiert
- VisualizerRegistry.autoload() hinzugefügt
- PostProcess Parameter vervollständigt
- Temp-Datei Cleanup implementiert
- Exception Handling verbessert

Verwendung: streamlit run gui_modern_fixed.py
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

sys.path.insert(0, str(Path(__file__).parent))

from src.visuals.registry import VisualizerRegistry
from src.analyzer import AudioAnalyzer
from src.types import ProjectConfig, VisualConfig
from src.pipeline import RenderPipeline, PreviewPipeline
from src.export_profiles import Platform, get_profile
from src.live_preview import LivePreview
from src.settings import get_settings
from src.logger import get_logger

logger = get_logger("audio_visualizer.gui_modern")

# ============================================================================
# MODERNES DESIGN SYSTEM
# ============================================================================

MODERN_CSS = """
<style>
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #16213e 100%);
    }
    
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 24px;
        margin: 12px 0;
        box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.05);
        transition: all 0.3s ease;
    }
    
    .glass-card:hover {
        background: rgba(255, 255, 255, 0.05);
        border-color: rgba(102, 126, 234, 0.3);
        transform: translateY(-2px);
        box-shadow: 
            0 12px 40px rgba(0, 0, 0, 0.4),
            0 0 20px rgba(102, 126, 234, 0.1);
    }
    
    .gradient-text {
        background: linear-gradient(135deg, #667eea 0%, #f093fb 50%, #f5576c 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 700;
    }
    
    .stepper {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px 40px;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 16px;
        margin-bottom: 30px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .category-pills {
        display: flex;
        gap: 10px;
        overflow-x: auto;
        padding: 10px 0;
        scrollbar-width: none;
    }
    
    .viz-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
        gap: 20px;
        padding: 10px 0;
    }
    
    .viz-card {
        position: relative;
        border-radius: 16px;
        overflow: hidden;
        cursor: pointer;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        background: rgba(255, 255, 255, 0.03);
        border: 2px solid transparent;
    }
    
    .viz-card:hover {
        transform: translateY(-8px) scale(1.02);
        border-color: rgba(102, 126, 234, 0.5);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4), 0 0 30px rgba(102, 126, 234, 0.2);
    }
    
    .viz-card.selected {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.3), 0 20px 40px rgba(0, 0, 0, 0.4);
    }
    
    .viz-preview {
        height: 150px;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(240, 147, 251, 0.2));
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 3em;
    }
    
    .viz-info {
        padding: 16px;
        background: rgba(0, 0, 0, 0.3);
    }
    
    .viz-tag {
        padding: 4px 10px;
        background: rgba(102, 126, 234, 0.2);
        border-radius: 12px;
        font-size: 0.75em;
        color: #667eea;
    }
    
    .upload-zone {
        border: 2px dashed rgba(102, 126, 234, 0.3);
        border-radius: 20px;
        padding: 60px 40px;
        text-align: center;
        background: rgba(102, 126, 234, 0.02);
    }
    
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.85em;
        font-weight: 500;
    }
    
    .status-badge.info {
        background: rgba(52, 152, 219, 0.2);
        color: #3498db;
    }
    
    .template-card {
        background: rgba(255, 255, 255, 0.03);
        border: 2px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .template-card:hover {
        background: rgba(102, 126, 234, 0.1);
        border-color: rgba(102, 126, 234, 0.5);
        transform: translateY(-4px);
    }
    
    .template-card.selected {
        background: rgba(102, 126, 234, 0.15);
        border-color: #667eea;
    }
</style>
"""

# ============================================================================
# STATE MANAGEMENT
# ============================================================================

def init_session_state():
    """Initialisiert alle Session State Variablen."""
    defaults = {
        'current_step': 'upload',
        'audio_path': None,
        'audio_name': None,
        'features': None,
        'selected_visualizer': 'pulsing_core',
        'preview_frame': None,
        'output_path': None,
        'show_wizard': False,  # BUGFIX #2: Initialisiert
        'wizard_step': 1,
        'wizard_template': None,
        'category_filter': 'All',
        'temp_dirs': [],  # BUGFIX #6: Für Cleanup
        'config': {
            'resolution': (1920, 1080),
            'fps': 60,
            'colors': {
                'primary': '#FF0055',
                'secondary': '#00CCFF',
                'background': '#0A0A0A'
            },
            # BUGFIX #4: Vollständige PostProcess Parameter
            'postprocess': {
                'contrast': 1.0,
                'saturation': 1.0,
                'brightness': 1.0,  # Hinzugefügt
                'grain': 0.0,
                'vignette': 0.0,
                'chromatic_aberration': 0.0  # Hinzugefügt
            }
        }
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ============================================================================
# TEMP FILE MANAGEMENT
# ============================================================================

def cleanup_temp_dirs():
    """Bereinigt temporäre Verzeichnisse."""
    if 'temp_dirs' in st.session_state:
        for temp_dir in st.session_state.temp_dirs[:]:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                st.session_state.temp_dirs.remove(temp_dir)
            except Exception as e:
                logger.warning(f"Konnte Temp-Dir nicht löschen: {e}")

def register_temp_dir(temp_dir: str):
    """Registriert ein Temp-Verzeichnis für spätere Bereinigung."""
    if temp_dir not in st.session_state.temp_dirs:
        st.session_state.temp_dirs.append(temp_dir)

# ============================================================================
# DATA & HELPERS
# ============================================================================

def get_visualizer_info() -> Dict[str, Dict]:
    """Gibt Informationen über alle Visualizer zurück."""
    return {
        'pulsing_core': {
            'emoji': '🔴', 'name': 'Pulsing Core',
            'description': 'Pulsierender Kreis mit Chroma-Farben',
            'best_for': 'EDM, Pop, Dance',
            'category': 'Bass'
        },
        'spectrum_bars': {
            'emoji': '📊', 'name': 'Spectrum Bars',
            'description': '40-Balken Equalizer',
            'best_for': 'Rock, Hip-Hop, Electronic',
            'category': 'Equalizer'
        },
        'chroma_field': {
            'emoji': '✨', 'name': 'Chroma Field',
            'description': 'Partikel-Feld basierend auf Tonart',
            'best_for': 'Ambient, Jazz, Klassik',
            'category': 'Ambient'
        },
        'particle_swarm': {
            'emoji': '🔥', 'name': 'Particle Swarm',
            'description': 'Physik-basierte Partikel-Explosionen',
            'best_for': 'Dubstep, Trap, Bass Music',
            'category': 'Energetic'
        },
        'typographic': {
            'emoji': '📝', 'name': 'Typographic',
            'description': 'Minimalistisch mit Wellenform',
            'best_for': 'Podcasts, Sprache, Audiobooks',
            'category': 'Minimal'
        },
        'neon_oscilloscope': {
            'emoji': '💠', 'name': 'Neon Oscilloscope',
            'description': 'Retro-futuristischer Oszilloskop',
            'best_for': 'Synthwave, Cyberpunk, Retro',
            'category': 'Retro'
        },
        'sacred_mandala': {
            'emoji': '🕉️', 'name': 'Sacred Mandala',
            'description': 'Heilige Geometrie mit rotierenden Mustern',
            'best_for': 'Meditation, Ambient, Yoga',
            'category': 'Spiritual'
        },
        'liquid_blobs': {
            'emoji': '💧', 'name': 'Liquid Blobs',
            'description': 'Flüssige MetaBall-ähnliche Blobs',
            'best_for': 'House, Techno, Deep House',
            'category': 'Fluid'
        },
        'neon_wave_circle': {
            'emoji': '⭕', 'name': 'Neon Wave Circle',
            'description': 'Konzentrische Neon-Ringe mit Wellen',
            'best_for': 'EDM, Techno, Trance',
            'category': 'Neon'
        },
        'frequency_flower': {
            'emoji': '🌸', 'name': 'Frequency Flower',
            'description': 'Organische Blumen mit Audio-reaktiven Blütenblättern',
            'best_for': 'Indie, Folk, Pop',
            'category': 'Organic'
        },
        'waveform_line': {
            'emoji': '📈', 'name': 'Waveform Line',
            'description': 'Oszilloskop-ähnliche Wellenform-Linie',
            'best_for': 'Podcasts, Sprache, Akustik',
            'category': 'Waveform'
        },
        '3d_spectrum': {
            'emoji': '🏙️', 'name': '3D Spectrum',
            'description': '3D-Balken-Equalizer mit Perspektive',
            'best_for': 'EDM, Techno, Elektronisch',
            'category': '3D'
        },
        'circular_wave': {
            'emoji': '🌀', 'name': 'Circular Wave',
            'description': 'Kreisförmige, rotierende Wellenform',
            'best_for': 'Ambient, Meditation, Atmosphärisch',
            'category': 'Waveform'
        }
    }

def save_uploaded_file(uploaded_file) -> Optional[str]:
    """Speichert eine hochgeladene Datei temporär."""
    if uploaded_file is None:
        return None
    
    try:
        temp_dir = tempfile.mkdtemp(prefix="avp_")
        file_path = os.path.join(temp_dir, uploaded_file.name)
        
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.getvalue())
        
        register_temp_dir(temp_dir)
        return file_path
    except Exception as e:
        logger.error(f"Fehler beim Speichern: {e}")
        st.error(f"Fehler beim Speichern der Datei: {e}")
        return None

def analyze_audio_file(audio_path: str) -> Optional[Any]:
    """Analysiert eine Audio-Datei."""
    try:
        # BUGFIX #7: Validierung der Datei-Existenz
        if not os.path.exists(audio_path):
            st.error("Audio-Datei nicht mehr verfügbar. Bitte lade sie erneut hoch.")
            return None
            
        analyzer = AudioAnalyzer()
        features = analyzer.analyze(audio_path, fps=30)
        return features
    except Exception as e:
        logger.exception("Audio-Analyse fehlgeschlagen")
        st.error(f"Audio-Analyse fehlgeschlagen: {e}")
        return None

# ============================================================================
# NAVIGATION COMPONENTS
# ============================================================================

def render_stepper():
    """Rendert die moderne Stepper-Navigation."""
    steps = [
        {"id": "upload", "label": "Upload", "icon": "📁"},
        {"id": "visualize", "label": "Visualize", "icon": "🎨"},
        {"id": "customize", "label": "Customize", "icon": "⚙️"},
        {"id": "export", "label": "Export", "icon": "🎬"}
    ]
    
    current_idx = next(i for i, s in enumerate(steps) if s['id'] == st.session_state.current_step)
    
    cols = st.columns(len(steps))
    for idx, (col, step) in enumerate(zip(cols, steps)):
        with col:
            is_active = idx == current_idx
            is_completed = idx < current_idx
            
            icon = "✓" if is_completed else step['icon']
            
            # BUGFIX #10: Bessere Navigation-Logik
            can_navigate = idx <= current_idx  # Nur zu aktuellem oder vorherigen
            
            if st.button(f"{icon} {step['label']}", key=f"step_{step['id']}", 
                        use_container_width=True,
                        type="primary" if is_active else "secondary",
                        disabled=not can_navigate and idx > current_idx + 1):
                if can_navigate:
                    st.session_state.current_step = step['id']
                    st.rerun()

# ============================================================================
# PAGE COMPONENTS
# ============================================================================

def render_upload_page():
    """Rendert die moderne Upload-Seite."""
    st.markdown("""
    <div style="text-align: center; padding: 40px 0;">
        <h1 class="gradient-text" style="font-size: 3rem; margin-bottom: 16px;">
            🎵 Audio Visualizer Pro
        </h1>
        <p style="font-size: 1.2rem; color: rgba(255,255,255,0.6); max-width: 500px; margin: 0 auto;">
            Transformiere deine Musik in atemberaubende Visualisierungen
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader(
            "",
            type=['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'],
            help="Unterstützte Formate: MP3, WAV, FLAC, AAC, OGG, M4A"
        )
        
        if uploaded_file is None:
            st.markdown("""
            <div class="upload-zone">
                <div style="font-size: 4em; margin-bottom: 16px;">📁</div>
                <h3>Audio-Datei hierhin ziehen</h3>
                <p style="color: rgba(255,255,255,0.5);">oder klicke zum Durchsuchen</p>
                <p style="font-size: 0.85em; color: rgba(255,255,255,0.4); margin-top: 20px;">
                    Max. 2 GB • MP3, WAV, FLAC, AAC, OGG, M4A
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if uploaded_file:
            with st.spinner("🔍 Analysiere Audio..."):
                audio_path = save_uploaded_file(uploaded_file)
                if audio_path:
                    features = analyze_audio_file(audio_path)
                    if features:
                        st.session_state.audio_path = audio_path
                        st.session_state.audio_name = uploaded_file.name
                        st.session_state.features = features
                        
                        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                        cols = st.columns(4)
                        with cols[0]:
                            st.metric("⏱️ Dauer", f"{features.duration:.1f}s")
                        with cols[1]:
                            st.metric("🎼 Tempo", f"{features.tempo:.0f} BPM")
                        with cols[2]:
                            st.metric("🎹 Key", features.key or "Unknown")
                        with cols[3]:
                            st.metric("🎵 Modus", features.mode.title())
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        st.audio(audio_path)
                        
                        if st.button("🎨 Weiter zu Visualizer →", type="primary", use_container_width=True):
                            st.session_state.current_step = 'visualize'
                            st.rerun()

def render_visualize_page():
    """Rendert die Visualizer-Auswahl mit moderner Galerie."""
    if not st.session_state.audio_path:
        st.warning("⚠️ Bitte zuerst eine Audio-Datei laden")
        return
    
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <h2 class="gradient-text">Wähle deinen Visualizer</h2>
        <p style="color: rgba(255,255,255,0.6);">Finde den perfekten Stil für deine Musik</p>
    </div>
    """, unsafe_allow_html=True)
    
    viz_info = get_visualizer_info()
    categories = ['All'] + sorted(list(set(v['category'] for v in viz_info.values())))
    
    st.markdown('<div class="category-pills">', unsafe_allow_html=True)
    cat_cols = st.columns(len(categories))
    for col, cat in zip(cat_cols, categories):
        with col:
            is_active = st.session_state.category_filter == cat
            btn_type = "primary" if is_active else "secondary"
            if st.button(cat, key=f"cat_{cat}", use_container_width=True, type=btn_type):
                st.session_state.category_filter = cat
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.session_state.category_filter == 'All':
        display_vizs = viz_info
    else:
        display_vizs = {k: v for k, v in viz_info.items() 
                       if v['category'] == st.session_state.category_filter}
    
    st.markdown('<div class="viz-grid">', unsafe_allow_html=True)
    
    cols = st.columns(3)
    for idx, (viz_id, info) in enumerate(display_vizs.items()):
        with cols[idx % 3]:
            is_selected = st.session_state.selected_visualizer == viz_id
            selected_class = "selected" if is_selected else ""
            
            st.markdown(f"""
            <div class="viz-card {selected_class}">
                <div class="viz-preview">
                    {info['emoji']}
                </div>
                <div class="viz-info">
                    <div style="font-weight: 600; margin-bottom: 4px;">{info['name']}</div>
                    <div style="font-size: 0.85em; color: rgba(255,255,255,0.6); margin-bottom: 8px;">{info['description']}</div>
                    <div class="viz-tags">
                        <span class="viz-tag">{info['category']}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Auswählen", key=f"select_{viz_id}", use_container_width=True):
                st.session_state.selected_visualizer = viz_id
                st.session_state.preview_frame = None  # BUGFIX #8: Reset preview
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    selected_info = viz_info.get(st.session_state.selected_visualizer, {})
    st.markdown(f"""
    <div style="margin-top: 30px; text-align: center;">
        <span class="status-badge info">
            🎨 Ausgewählt: {selected_info.get('name', 'Unknown')}
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("⚙️ Weiter zu Einstellungen →", type="primary", use_container_width=True):
            st.session_state.current_step = 'customize'
            st.rerun()

def render_customize_page():
    """Rendert die Anpassungs-Seite."""
    if not st.session_state.audio_path:
        st.warning("⚠️ Bitte zuerst eine Audio-Datei laden")
        return
    
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <h2 class="gradient-text">Passe deinen Visualizer an</h2>
        <p style="color: rgba(255,255,255,0.6);">Farben, Effekte und Export-Einstellungen</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_left, col_right = st.columns([2, 3])
    
    with col_left:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 📱 Export-Profil")
        
        profiles = [
            ("🎬 YouTube 1080p", "youtube"),
            ("🎬 YouTube 4K", "youtube_4k"),
            ("📱 Instagram Feed", "instagram_feed"),
            ("📱 Instagram Reels", "instagram_reels"),
            ("🎵 TikTok", "tiktok"),
            ("⚙️ Benutzerdefiniert", "custom")
        ]
        
        selected_profile = st.selectbox(
            "Plattform",
            options=[p[1] for p in profiles],
            format_func=lambda x: next(p[0] for p in profiles if p[1] == x),
            key="export_profile_select"
        )
        
        st.session_state.selected_profile = selected_profile
        
        if selected_profile != "custom":
            try:
                if selected_profile == "youtube_4k":
                    profile = get_profile("youtube_4k")
                elif selected_profile == "tiktok_hd":
                    profile = get_profile("tiktok_hd")
                else:
                    profile = get_profile(Platform(selected_profile))
                
                st.session_state.config['resolution'] = profile.resolution
                st.session_state.config['fps'] = profile.fps
                
                st.info(f"📐 {profile.resolution[0]}×{profile.resolution[1]} @ {profile.fps}fps")
            except Exception as e:
                logger.warning(f"Konnte Export-Profil nicht laden: {e}")
        else:
            res_options = [
                ("4K (3840×2160)", (3840, 2160)),
                ("Full HD (1920×1080)", (1920, 1080)),
                ("HD (1280×720)", (1280, 720)),
                ("Square (1080×1080)", (1080, 1080)),
                ("Vertical (1080×1920)", (1080, 1920))
            ]
            
            res_idx = st.selectbox(
                "Auflösung",
                range(len(res_options)),
                format_func=lambda i: res_options[i][0],
                key="resolution_select"
            )
            st.session_state.config['resolution'] = res_options[res_idx][1]
            
            st.session_state.config['fps'] = st.selectbox(
                "FPS", [24, 30, 60, 120], index=2, key="fps_select"
            )
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 🎨 Farben")
        
        colors = st.session_state.config['colors']
        colors['primary'] = st.color_picker("Primärfarbe", colors['primary'], key="color_primary")
        colors['secondary'] = st.color_picker("Sekundärfarbe", colors['secondary'], key="color_secondary")
        colors['background'] = st.color_picker("Hintergrund", colors['background'], key="color_bg")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col_right:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### ✨ Post-Processing")
        
        pp = st.session_state.config['postprocess']
        
        col1, col2 = st.columns(2)
        with col1:
            pp['contrast'] = st.slider("Kontrast", 0.5, 2.0, pp.get('contrast', 1.0), 0.1, key="pp_contrast")
            pp['saturation'] = st.slider("Sättigung", 0.0, 2.0, pp.get('saturation', 1.0), 0.1, key="pp_sat")
            pp['brightness'] = st.slider("Helligkeit", 0.5, 2.0, pp.get('brightness', 1.0), 0.1, key="pp_bright")
        with col2:
            pp['grain'] = st.slider("Film Grain", 0.0, 1.0, pp.get('grain', 0.0), 0.05, key="pp_grain")
            pp['vignette'] = st.slider("Vignette", 0.0, 1.0, pp.get('vignette', 0.0), 0.05, key="pp_vignette")
            pp['chromatic_aberration'] = st.slider("Chromatic Aberration", 0.0, 5.0, 
                                                   pp.get('chromatic_aberration', 0.0), 0.5, key="pp_chroma")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 👁️ Schnell-Vorschau")
        
        # BUGFIX #7: Validierung vor Preview
        if st.button("🎨 Vorschau rendern", use_container_width=True):
            if not st.session_state.audio_path or not os.path.exists(st.session_state.audio_path):
                st.error("Audio-Datei nicht verfügbar. Bitte lade sie erneut hoch.")
            else:
                with st.spinner("Rendere..."):
                    try:
                        preview = LivePreview(st.session_state.selected_visualizer, (640, 360))
                        preview.analyze_audio(st.session_state.audio_path)
                        preview.setup_visualizer(st.session_state.config['colors'])
                        
                        frame = preview.render_frame(0)
                        st.session_state.preview_frame = frame
                    except Exception as e:
                        logger.exception("Preview rendering failed")
                        st.error(f"Fehler: {e}")
        
        if st.session_state.preview_frame is not None:
            st.image(Image.fromarray(st.session_state.preview_frame), use_column_width=True)
        else:
            st.markdown("""
            <div style="text-align: center; padding: 60px; color: rgba(255,255,255,0.4);">
                <div style="font-size: 3em; margin-bottom: 16px;">🎨</div>
                <p>Klicke "Vorschau rendern" um eine Vorschau zu sehen</p>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("← Zurück", use_container_width=True):
            st.session_state.current_step = 'visualize'
            st.rerun()
    with col3:
        if st.button("🎬 Zum Export →", type="primary", use_container_width=True):
            st.session_state.current_step = 'export'
            st.rerun()

def render_export_page():
    """Rendert die Export-Seite."""
    if not st.session_state.audio_path:
        st.warning("⚠️ Bitte zuerst eine Audio-Datei laden")
        return
    
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <h2 class="gradient-text">Exportiere dein Video</h2>
        <p style="color: rgba(255,255,255,0.6);">Wähle zwischen Vorschau oder finalem Render</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 👁️ Vorschau rendern")
        st.markdown("Schnelle Vorschau in niedriger Qualität")
        
        preview_duration = st.slider("Dauer (Sekunden)", 1, 10, 5, key="preview_duration")
        
        if st.button("▶️ Vorschau starten", use_container_width=True):
            temp_dir = None
            try:
                with st.spinner("Rendere Vorschau..."):
                    temp_dir = tempfile.mkdtemp()
                    register_temp_dir(temp_dir)
                    output_path = os.path.join(temp_dir, "preview.mp4")
                    
                    # BUGFIX #13: Settings verwenden statt hardcoded
                    settings = get_settings()
                    
                    config = ProjectConfig(
                        audio_file=st.session_state.audio_path,
                        output_file=output_path,
                        visual=VisualConfig(
                            type=st.session_state.selected_visualizer,
                            resolution=settings.preview_resolution,  # BUGFIX #13
                            fps=settings.preview_fps,  # BUGFIX #13
                            colors=st.session_state.config['colors']
                        ),
                        postprocess=st.session_state.config['postprocess']
                    )
                    
                    pipeline = PreviewPipeline(config)
                    
                    progress_bar = st.progress(0.0)
                    def progress_cb(p, msg):
                        progress_bar.progress(min(p, 1.0))
                    
                    pipeline.run(preview_duration=preview_duration, progress_callback=progress_cb)
                    
                    if os.path.exists(output_path):
                        st.session_state.output_path = output_path
                        st.success("✅ Vorschau fertig!")
                        
                        with open(output_path, 'rb') as f:
                            st.video(f.read())
            except Exception as e:
                logger.exception("Preview rendering failed")
                st.error(f"Fehler beim Rendern: {e}")
                st.info("Prüfe die Logs für Details")
                if temp_dir and os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception as e:
                        logger.warning(f"Failed to cleanup temp dir: {e}")
                        pass
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="glass-card" style="border-color: #667eea;">', unsafe_allow_html=True)
        st.markdown("### 🎬 Finales Video")
        st.markdown("Rendere das finale Video in voller Qualität")
        
        viz_info = get_visualizer_info()
        selected_name = viz_info.get(st.session_state.selected_visualizer, {}).get('name', 'Unknown')
        
        st.markdown(f"""
        <div style="background: rgba(102,126,234,0.1); padding: 16px; border-radius: 12px; margin: 16px 0;">
            <div style="font-size: 0.85em; color: rgba(255,255,255,0.6);">Visualizer</div>
            <div style="font-weight: 600;">{selected_name}</div>
            <div style="font-size: 0.85em; color: rgba(255,255,255,0.6); margin-top: 8px;">Auflösung</div>
            <div style="font-weight: 600;">{st.session_state.config['resolution'][0]}×{st.session_state.config['resolution'][1]} @ {st.session_state.config['fps']}fps</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 FINALES VIDEO RENDERN", type="primary", use_container_width=True):
            temp_dir = None
            try:
                with st.spinner("Rendere finales Video..."):
                    temp_dir = tempfile.mkdtemp()
                    register_temp_dir(temp_dir)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = os.path.join(temp_dir, f"visualization_{timestamp}.mp4")
                    
                    config = ProjectConfig(
                        audio_file=st.session_state.audio_path,
                        output_file=output_path,
                        visual=VisualConfig(
                            type=st.session_state.selected_visualizer,
                            resolution=st.session_state.config['resolution'],
                            fps=st.session_state.config['fps'],
                            colors=st.session_state.config['colors']
                        ),
                        postprocess=st.session_state.config['postprocess']
                    )
                    
                    # BUGFIX #9: Export Profile an Pipeline übergeben
                    export_profile = None
                    selected_profile = st.session_state.get('selected_profile', 'custom')
                    if selected_profile != 'custom':
                        try:
                            if selected_profile == "youtube_4k":
                                export_profile = get_profile("youtube_4k")
                            elif selected_profile == "tiktok_hd":
                                export_profile = get_profile("tiktok_hd")
                            else:
                                export_profile = get_profile(Platform(selected_profile))
                        except Exception as e:
                            logger.warning(f"Konnte Export-Profil nicht laden: {e}")
                    
                    pipeline = RenderPipeline(config, export_profile=export_profile)
                    
                    progress_bar = st.progress(0.0)
                    status_text = st.empty()
                    
                    def progress_cb(p, msg):
                        progress_bar.progress(min(p, 1.0))
                        status_text.text(msg)
                    
                    pipeline.run(progress_callback=progress_cb)
                    
                    if os.path.exists(output_path):
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
            except Exception as e:
                logger.exception("Final rendering failed")
                st.error(f"Fehler beim Rendern: {e}")
                st.info("Prüfe die Logs für Details")
            finally:
                # Cleanup wird beim nächsten Run oder beim Schließen gemacht
                pass
        
        st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# VISUALIZER CREATION WIZARD
# ============================================================================

def render_visualizer_wizard():
    """Wizard zum Erstellen neuer Visualizer."""
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <h2 class="gradient-text">🧙 Visualizer Wizard</h2>
        <p style="color: rgba(255,255,255,0.6);">Erstelle deinen eigenen Visualizer Schritt für Schritt</p>
    </div>
    """, unsafe_allow_html=True)
    
    wizard_step = st.session_state.get('wizard_step', 1)
    st.progress(wizard_step / 4)
    
    if wizard_step == 1:
        st.markdown("### Schritt 1: Wähle ein Template")
        
        templates = [
            {"id": "circle", "name": "Circle Visualizer", "icon": "🔴",
             "desc": "Pulsierende Kreise für Bass-Visualisierungen"},
            {"id": "bars", "name": "Bar Equalizer", "icon": "📊",
             "desc": "Frequenzbalken-Equalizer"},
            {"id": "particles", "name": "Particle System", "icon": "✨",
             "desc": "Partikel-Effekte mit Physik"},
            {"id": "waveform", "name": "Waveform", "icon": "〰️",
             "desc": "Oszilloskop-ähnliche Waveform"},
            {"id": "blank", "name": "Blank Canvas", "icon": "🎨",
             "desc": "Starte von Grund auf"},
        ]
        
        cols = st.columns(len(templates))
        for col, template in zip(cols, templates):
            with col:
                is_selected = st.session_state.get('wizard_template') == template['id']
                selected_class = "selected" if is_selected else ""
                
                st.markdown(f"""
                <div class="template-card {selected_class}">
                    <div style="font-size: 3em; margin-bottom: 12px;">{template['icon']}</div>
                    <h4>{template['name']}</h4>
                    <p style="font-size: 0.85em; color: rgba(255,255,255,0.6);">{template['desc']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("Auswählen", key=f"tpl_{template['id']}", use_container_width=True):
                    st.session_state.wizard_template = template['id']
                    st.rerun()
        
        if st.session_state.get('wizard_template'):
            if st.button("Weiter →", type="primary"):
                st.session_state.wizard_step = 2
                st.rerun()
    
    elif wizard_step == 2:
        st.markdown("### Schritt 2: Konfiguriere Parameter")
        
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("#### 🎚️ Audio-Feature Binding")
        st.markdown("Verbinde Audio-Features mit visuellen Parametern")
        st.markdown('</div>', unsafe_allow_html=True)
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("**Verfügbare Features**")
            features = [
                ("rms", "Lautstärke (RMS)", "🔊"),
                ("onset", "Beat/Onset", "🥁"),
                ("chroma", "Tonart/Farbe", "🎨"),
                ("spectral_centroid", "Helligkeit", "💡"),
                ("progress", "Zeit", "⏱️"),
            ]
            # BUGFIX #1: Korrekte String-Quotes verwendet
            for key, label, icon in features:
                st.markdown(f'<div class="glass-card">{icon} {label}</div>', 
                          unsafe_allow_html=True)
        
        with col_right:
            st.markdown("**Visuelle Parameter**")
            params = [
                ("radius", "Radius/Größe"),
                ("color", "Farbton"),
                ("opacity", "Transparenz"),
                ("position", "Position"),
            ]
            for key, label in params:
                st.selectbox(label, ["-"] + [f[0] for f in features], key=f"bind_{key}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Zurück"):
                st.session_state.wizard_step = 1
                st.rerun()
        with col2:
            if st.button("Weiter →", type="primary"):
                st.session_state.wizard_step = 3
                st.rerun()
    
    elif wizard_step == 3:
        st.markdown("### Schritt 3: Code & Preview")
        
        template_code = generate_template_code(st.session_state.wizard_template)
        
        col_editor, col_preview = st.columns([3, 2])
        
        with col_editor:
            st.markdown("**Code Editor**")
            code = st.text_area("", template_code, height=400, key="wizard_code")
        
        with col_preview:
            st.markdown("**Live Preview**")
            if st.button("▶️ Aktualisieren", use_container_width=True):
                st.info("Kompiliere...")
            
            st.markdown("""
            <div style="background: rgba(0,0,0,0.5); border-radius: 12px; height: 300px; display: flex; align-items: center; justify-content: center;">
                <p style="color: rgba(255,255,255,0.4);">Preview wird hier angezeigt</p>
            </div>
            """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Zurück"):
                st.session_state.wizard_step = 2
                st.rerun()
        with col2:
            if st.button("Weiter →", type="primary"):
                st.session_state.wizard_step = 4
                st.rerun()
    
    elif wizard_step == 4:
        st.markdown("### Schritt 4: Speichern & Veröffentlichen")
        
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        viz_name = st.text_input("Visualizer Name", key="wiz_name")
        viz_desc = st.text_area("Beschreibung", key="wiz_desc")
        viz_category = st.selectbox("Kategorie", 
                                   ["Bass", "Equalizer", "Ambient", "Energetic", 
                                    "Minimal", "Retro", "Custom"], key="wiz_cat")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Verwerfen"):
                st.session_state.wizard_step = 1
                st.session_state.wizard_template = None
                st.rerun()
        with col2:
            if st.button("💾 Speichern", type="primary", use_container_width=True):
                if viz_name:
                    st.success(f"✅ Visualizer '{viz_name}' wurde erstellt!")
                else:
                    st.error("Bitte gib einen Namen ein")
        st.markdown('</div>', unsafe_allow_html=True)

def generate_template_code(template_id: str) -> str:
    """Generiert Template-Code basierend auf Auswahl."""
    # BUGFIX #5: Vollständiger Code mit Imports
    common_imports = '''"""
Mein Visualizer - Erstellt mit dem Audio Visualizer Pro Wizard
"""
import numpy as np
from PIL import Image, ImageDraw
from .base import BaseVisualizer
from .registry import register_visualizer

'''
    
    templates = {
        "circle": common_imports + '''
@register_visualizer("my_circle")
class MyCircleVisualizer(BaseVisualizer):
    """Pulsierender Kreis Visualizer."""
    
    def setup(self):
        self.center = (self.width // 2, self.height // 2)
        self.base_radius = min(self.width, self.height) // 6
    
    def render_frame(self, frame_idx: int) -> np.ndarray:
        f = self.get_feature_at_frame(frame_idx)
        rms = f['rms']  # Lautstärke
        onset = f['onset']  # Beat
        
        img = Image.new('RGB', (self.width, self.height), (10, 10, 10))
        draw = ImageDraw.Draw(img)
        
        # Pulsierender Kreis
        radius = int(self.base_radius * (1 + rms))
        draw.ellipse([
            self.center[0] - radius, self.center[1] - radius,
            self.center[0] + radius, self.center[1] + radius
        ], fill=self.colors['primary'][:3])
        
        return np.array(img)
''',
        "bars": common_imports + '''
@register_visualizer("my_bars")
class MyBarsVisualizer(BaseVisualizer):
    """Balken Equalizer Visualizer."""
    
    def setup(self):
        self.num_bars = 20
        self.bar_width = self.width // self.num_bars
    
    def render_frame(self, frame_idx: int) -> np.ndarray:
        f = self.get_feature_at_frame(frame_idx)
        rms = f['rms']
        
        img = Image.new('RGB', (self.width, self.height), (10, 10, 10))
        draw = ImageDraw.Draw(img)
        
        # Zeichne Balken
        for i in range(self.num_bars):
            bar_height = int(self.height * rms * (0.5 + 0.5 * np.sin(i + frame_idx * 0.1)))
            x = i * self.bar_width
            y = self.height - bar_height
            draw.rectangle([x, y, x + self.bar_width - 2, self.height], 
                          fill=self.colors['primary'][:3])
        
        return np.array(img)
''',
        "particles": common_imports + '''
@register_visualizer("my_particles")
class MyParticlesVisualizer(BaseVisualizer):
    """Partikel-System Visualizer."""
    
    def setup(self):
        self.particles = []
        self.num_particles = 50
    
    def render_frame(self, frame_idx: int) -> np.ndarray:
        f = self.get_feature_at_frame(frame_idx)
        onset = f['onset']
        
        img = Image.new('RGB', (self.width, self.height), (10, 10, 10))
        draw = ImageDraw.Draw(img)
        
        # Bei Beat neue Partikel erzeugen
        if onset > 0.5:
            center = (self.width // 2, self.height // 2)
            draw.ellipse([center[0]-50, center[1]-50, center[0]+50, center[1]+50],
                        fill=self.colors['secondary'][:3])
        
        return np.array(img)
''',
        "waveform": common_imports + '''
@register_visualizer("my_waveform")
class MyWaveformVisualizer(BaseVisualizer):
    """Wellenform-Oszilloskop Visualizer."""
    
    def setup(self):
        self.center_y = self.height // 2
    
    def render_frame(self, frame_idx: int) -> np.ndarray:
        f = self.get_feature_at_frame(frame_idx)
        rms = f['rms']
        
        img = Image.new('RGB', (self.width, self.height), (10, 10, 10))
        draw = ImageDraw.Draw(img)
        
        # Zeichne Wellenform-Linie
        points = []
        for x in range(0, self.width, 10):
            y = self.center_y + int(np.sin(x * 0.02 + frame_idx * 0.1) * rms * 100)
            points.append((x, y))
        
        if len(points) > 1:
            draw.line(points, fill=self.colors['primary'][:3], width=3)
        
        return np.array(img)
''',
        "blank": common_imports + '''
@register_visualizer("my_visualizer")
class MyVisualizer(BaseVisualizer):
    """Mein eigener Visualizer."""
    
    def setup(self):
        """Einmalige Initialisierung vor dem Rendering."""
        self.center = (self.width // 2, self.height // 2)
    
    def render_frame(self, frame_idx: int) -> np.ndarray:
        """
        Rendert EINEN Frame als RGB-Array.
        
        Verfügbare Features in f:
        - rms: Lautstärke (0.0-1.0)
        - onset: Beat-Trigger (0.0-1.0)
        - chroma: 12-Ton Farb-Array
        - spectral_centroid: Helligkeit (0.0-1.0)
        - progress: Zeitfortschritt (0.0-1.0)
        """
        f = self.get_feature_at_frame(frame_idx)
        rms = f['rms']
        
        img = Image.new('RGB', (self.width, self.height), (10, 10, 10))
        draw = ImageDraw.Draw(img)
        
        # Deine Zeichen-Logik hier:
        # Beispiel: Kreis basierend auf Lautstärke
        radius = int(50 + rms * 100)
        draw.ellipse([
            self.center[0] - radius, self.center[1] - radius,
            self.center[0] + radius, self.center[1] + radius
        ], fill=self.colors['primary'][:3])
        
        return np.array(img)
'''
    }
    return templates.get(template_id, templates["blank"])

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """Hauptfunktion der modernen GUI."""
    st.set_page_config(
        page_title="Audio Visualizer Pro",
        page_icon="🎵",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Load CSS
    st.markdown(MODERN_CSS, unsafe_allow_html=True)
    
    # Initialize State
    init_session_state()
    
    # BUGFIX #3: VisualizerRegistry laden
    VisualizerRegistry.autoload()
    
    # Cleanup alte Temp-Dateien beim Start
    cleanup_temp_dirs()
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 🎵 Audio Visualizer Pro")
        
        if st.button("🏠 Hauptmenü", key="nav_home"):
            st.session_state.show_wizard = False
            st.session_state.current_step = 'upload'
            st.rerun()
        
        if st.button("🧙 Visualizer Wizard", key="nav_wizard"):
            st.session_state.show_wizard = True
            st.rerun()
        
        st.markdown("---")
        
        if st.session_state.audio_path:
            st.markdown("### 📊 Aktuelles Projekt")
            st.markdown(f"**Audio:** {st.session_state.audio_name}")
            
            viz_info = get_visualizer_info()
            selected = viz_info.get(st.session_state.selected_visualizer, {})
            st.markdown(f"**Visualizer:** {selected.get('name', 'Unknown')}")
        
        st.markdown("---")
        st.markdown("<p style='color: #666; font-size: 0.75em;'>v2.0 Modern Edition (Fixed)</p>", 
                   unsafe_allow_html=True)
    
    # Show Wizard or Main Content
    if st.session_state.get('show_wizard'):
        if st.button("← Zurück zum Editor", key="wizard_back"):
            st.session_state.show_wizard = False
            st.rerun()
        render_visualizer_wizard()
    else:
        render_stepper()
        
        step_pages = {
            'upload': render_upload_page,
            'visualize': render_visualize_page,
            'customize': render_customize_page,
            'export': render_export_page
        }
        
        current_page = step_pages.get(st.session_state.current_step, render_upload_page)
        current_page()

if __name__ == "__main__":
    main()
