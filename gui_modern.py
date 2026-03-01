"""
Audio Visualizer Pro - Moderne GUI v2.0

Diese Version zeigt eine modernisierte GUI mit:
- Stepper-Navigation statt Sidebar
- Glassmorphism Design
- Verbesserter Visualizer-Galerie
- Wizard für neue Visualizer

Verwendung: streamlit run gui_modern.py
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
from src.export_profiles import ExportProfile, Platform, get_profile, list_profiles
from src.live_preview import LivePreview
from src.settings import get_settings
from src.logger import get_logger
from src.keyboard_shortcuts import (
    KeyboardShortcutManager, UndoRedoManager, ShortcutKey,
    show_shortcut_help, init_keyboard_support
)
from src.auto_save import AutoSaveManager, AutoSaveUI, init_auto_save
from src.preset_manager import PresetManager, PresetUI, init_preset_manager
from src.realtime import render_realtime_page, SOUNDDEVICE_AVAILABLE

logger = get_logger("audio_visualizer.gui_modern")

# ============================================================================
# MODERNES DESIGN SYSTEM
# ============================================================================

MODERN_CSS = """
<style>
    /* Reset & Base */
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #16213e 100%);
    }
    
    /* Glassmorphism Cards */
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
    
    /* Gradient Text */
    .gradient-text {
        background: linear-gradient(135deg, #667eea 0%, #f093fb 50%, #f5576c 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 700;
    }
    
    /* Stepper Navigation */
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
    
    .step {
        display: flex;
        flex-direction: column;
        align-items: center;
        cursor: pointer;
        transition: all 0.3s ease;
        flex: 1;
        position: relative;
    }
    
    .step:not(:last-child)::after {
        content: '';
        position: absolute;
        top: 20px;
        right: -50%;
        width: 100%;
        height: 2px;
        background: rgba(255, 255, 255, 0.1);
        z-index: 0;
    }
    
    .step.completed:not(:last-child)::after {
        background: linear-gradient(90deg, #667eea, #764ba2);
    }
    
    .step-icon {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2em;
        background: rgba(255, 255, 255, 0.05);
        border: 2px solid rgba(255, 255, 255, 0.1);
        transition: all 0.3s ease;
        z-index: 1;
    }
    
    .step.active .step-icon {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-color: transparent;
        box-shadow: 0 0 20px rgba(102, 126, 234, 0.5);
        transform: scale(1.1);
    }
    
    .step.completed .step-icon {
        background: #27ae60;
        border-color: #27ae60;
    }
    
    .step-label {
        margin-top: 8px;
        font-size: 0.85em;
        color: rgba(255, 255, 255, 0.5);
        transition: all 0.3s ease;
    }
    
    .step.active .step-label {
        color: #fff;
        font-weight: 600;
    }
    
    .step.completed .step-label {
        color: #27ae60;
    }
    
    /* Visualizer Gallery Grid */
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
        position: relative;
        overflow: hidden;
    }
    
    .viz-preview::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(135deg, transparent 0%, rgba(255,255,255,0.1) 50%, transparent 100%);
        transform: translateX(-100%);
        transition: transform 0.6s;
    }
    
    .viz-card:hover .viz-preview::before {
        transform: translateX(100%);
    }
    
    .viz-info {
        padding: 16px;
        background: rgba(0, 0, 0, 0.3);
    }
    
    .viz-name {
        font-size: 1.1em;
        font-weight: 600;
        margin-bottom: 4px;
    }
    
    .viz-desc {
        font-size: 0.85em;
        color: rgba(255, 255, 255, 0.6);
        margin-bottom: 8px;
    }
    
    .viz-tags {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
    }
    
    .viz-tag {
        padding: 4px 10px;
        background: rgba(102, 126, 234, 0.2);
        border-radius: 12px;
        font-size: 0.75em;
        color: #667eea;
    }
    
    /* Upload Zone */
    .upload-zone {
        border: 2px dashed rgba(102, 126, 234, 0.3);
        border-radius: 20px;
        padding: 60px 40px;
        text-align: center;
        background: rgba(102, 126, 234, 0.02);
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .upload-zone:hover {
        border-color: #667eea;
        background: rgba(102, 126, 234, 0.05);
    }
    
    .upload-zone.dragover {
        border-color: #f093fb;
        background: rgba(240, 147, 251, 0.1);
        transform: scale(1.02);
    }
    
    .upload-icon {
        font-size: 4em;
        margin-bottom: 16px;
        opacity: 0.8;
    }
    
    /* Primary Button */
    .btn-primary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 16px 32px;
        font-size: 1.1em;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .btn-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.5);
    }
    
    /* Secondary Button */
    .btn-secondary {
        background: rgba(255, 255, 255, 0.1);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 12px;
        padding: 12px 24px;
        font-size: 1em;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .btn-secondary:hover {
        background: rgba(255, 255, 255, 0.15);
        border-color: rgba(255, 255, 255, 0.3);
    }
    
    /* Category Pills */
    .category-pills {
        display: flex;
        gap: 10px;
        overflow-x: auto;
        padding: 10px 0;
        scrollbar-width: none;
    }
    
    .category-pill {
        padding: 10px 20px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 25px;
        cursor: pointer;
        white-space: nowrap;
        transition: all 0.3s ease;
        font-size: 0.9em;
    }
    
    .category-pill:hover {
        background: rgba(255, 255, 255, 0.1);
    }
    
    .category-pill.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-color: transparent;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    /* Timeline */
    .timeline-container {
        background: rgba(0, 0, 0, 0.3);
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
    }
    
    /* Preview Window */
    .preview-window {
        background: rgba(0, 0, 0, 0.5);
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        min-height: 300px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Status Badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.85em;
        font-weight: 500;
    }
    
    .status-badge.success {
        background: rgba(39, 174, 96, 0.2);
        color: #27ae60;
    }
    
    .status-badge.info {
        background: rgba(52, 152, 219, 0.2);
        color: #3498db;
    }
    
    /* Wizard Steps */
    .wizard-step {
        animation: fadeIn 0.5s ease;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Template Cards */
    .template-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 16px;
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
    
    .template-icon {
        font-size: 3em;
        margin-bottom: 12px;
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
        'show_wizard': False,
        'config': {
            'resolution': (1920, 1080),
            'fps': 60,
            'colors': {
                'primary': '#FF0055',
                'secondary': '#00CCFF',
                'background': '#0A0A0A'
            },
            'postprocess': {
                'contrast': 1.0,
                'saturation': 1.0,
                'brightness': 1.0,
                'grain': 0.0,
                'vignette': 0.0,
                'chromatic_aberration': 0.0
            }
        },
        'wizard_step': 1,
        'wizard_template': None,
        'category_filter': 'All',
        # Keyboard & Auto-Save State
        'last_shortcut': None,
        'shortcut_triggered': False,
        'project_name': 'untitled',
        'last_auto_save': None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Initialisiere Keyboard Manager
    if 'keyboard_manager' not in st.session_state:
        st.session_state.keyboard_manager = KeyboardShortcutManager()
    
    # Initialisiere Undo Manager
    if 'undo_manager' not in st.session_state:
        st.session_state.undo_manager = UndoRedoManager()
    
    # Initialisiere Auto-Save
    if 'autosave' not in st.session_state:
        st.session_state.autosave = AutoSaveManager()

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
        
        if 'temp_dirs' not in st.session_state:
            st.session_state.temp_dirs = []
        st.session_state.temp_dirs.append(temp_dir)
        
        return file_path
    except Exception as e:
        logger.exception(f"Fehler beim Speichern: {e}")
        return None

def analyze_audio_file(audio_path: str) -> Optional[Any]:
    """Analysiert eine Audio-Datei."""
    try:
        analyzer = AudioAnalyzer()
        features = analyzer.analyze(audio_path, fps=30)
        return features
    except Exception as e:
        logger.exception(f"Analyse-Fehler: {e}")
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
        {"id": "preview", "label": "Preview", "icon": "👁️"},
        {"id": "export", "label": "Export", "icon": "🎬"}
    ]
    
    current_idx = next(i for i, s in enumerate(steps) if s['id'] == st.session_state.current_step)
    
    st.markdown('<div class="stepper">', unsafe_allow_html=True)
    
    cols = st.columns(len(steps))
    for idx, (col, step) in enumerate(zip(cols, steps)):
        with col:
            is_active = idx == current_idx
            is_completed = idx < current_idx
            
            status_class = "active" if is_active else ("completed" if is_completed else "")
            icon = "✓" if is_completed else step['icon']
            
            if st.button(f"{icon} {step['label']}", key=f"step_{step['id']}", 
                        use_container_width=True,
                        type="primary" if is_active else "secondary"):
                # Nur zu vorherigen Schritten oder aktuellem springen
                if idx <= current_idx + 1:
                    st.session_state.current_step = step['id']
                    st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

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
        # Upload Zone
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader(
            "",
            type=['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'],
            help="Unterstützte Formate: MP3, WAV, FLAC, AAC, OGG, M4A"
        )
        
        if uploaded_file is None:
            st.markdown("""
            <div class="upload-zone">
                <div class="upload-icon">📁</div>
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
                        
                        # Audio Info Card
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
                        
                        # Audio Player
                        st.audio(audio_path)
                        
                        # Continue Button
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
    
    # Category Filter
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
    
    # Filter Visualizer
    if st.session_state.category_filter == 'All':
        display_vizs = viz_info
    else:
        display_vizs = {k: v for k, v in viz_info.items() 
                       if v['category'] == st.session_state.category_filter}
    
    # Visualizer Grid
    st.markdown('<div class="viz-grid">', unsafe_allow_html=True)
    
    cols = st.columns(3)
    for idx, (viz_id, info) in enumerate(display_vizs.items()):
        with cols[idx % 3]:
            is_selected = st.session_state.selected_visualizer == viz_id
            selected_class = "selected" if is_selected else ""
            
            st.markdown(f"""
            <div class="viz-card {selected_class}" id="viz_{viz_id}">
                <div class="viz-preview">
                    {info['emoji']}
                </div>
                <div class="viz-info">
                    <div class="viz-name">{info['name']}</div>
                    <div class="viz-desc">{info['description']}</div>
                    <div class="viz-tags">
                        <span class="viz-tag">{info['category']}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Auswählen", key=f"select_{viz_id}", use_container_width=True):
                st.session_state.selected_visualizer = viz_id
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Selection Info
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
        # Export Profile
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
            format_func=lambda x: next(p[0] for p in profiles if p[1] == x)
        )
        
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
                logger.warning(f"Konnte Profil nicht laden: {e}")
        else:
            # Custom Settings
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
                format_func=lambda i: res_options[i][0]
            )
            st.session_state.config['resolution'] = res_options[res_idx][1]
            
            st.session_state.config['fps'] = st.selectbox(
                "FPS", [24, 30, 60, 120], index=2
            )
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Colors
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 🎨 Farben")
        
        colors = st.session_state.config['colors']
        colors['primary'] = st.color_picker("Primärfarbe", colors['primary'])
        colors['secondary'] = st.color_picker("Sekundärfarbe", colors['secondary'])
        colors['background'] = st.color_picker("Hintergrund", colors['background'])
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col_right:
        # Post-Processing
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### ✨ Post-Processing")
        
        pp = st.session_state.config['postprocess']
        
        col1, col2 = st.columns(2)
        with col1:
            pp['contrast'] = st.slider("Kontrast", 0.5, 2.0, pp.get('contrast', 1.0), 0.1)
            pp['saturation'] = st.slider("Sättigung", 0.0, 2.0, pp.get('saturation', 1.0), 0.1)
            pp['brightness'] = st.slider("Helligkeit", 0.5, 2.0, pp.get('brightness', 1.0), 0.1)
        with col2:
            pp['grain'] = st.slider("Film Grain", 0.0, 1.0, pp.get('grain', 0.0), 0.05)
            pp['vignette'] = st.slider("Vignette", 0.0, 1.0, pp.get('vignette', 0.0), 0.05)
            pp['chromatic_aberration'] = st.slider("Chromatic Aberration", 0.0, 5.0, 
                                                   pp.get('chromatic_aberration', 0.0), 0.5)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Preview
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 👁️ Schnell-Vorschau")
        
        if st.button("🎨 Vorschau rendern", use_container_width=True):
            with st.spinner("Rendere..."):
                try:
                    preview = LivePreview(st.session_state.selected_visualizer, (640, 360))
                    preview.analyze_audio(st.session_state.audio_path)
                    preview.setup_visualizer(st.session_state.config['colors'])
                    
                    frame = preview.render_frame(0)
                    st.session_state.preview_frame = frame
                except Exception as e:
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
    
    # Navigation
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
        st.markdown("Schnelle 5-Sekunden Vorschau in niedriger Qualität")
        
        preview_duration = st.slider("Dauer (Sekunden)", 1, 10, 5)
        
        if st.button("▶️ Vorschau starten", use_container_width=True):
            with st.spinner("Rendere Vorschau..."):
                temp_dir = tempfile.mkdtemp()
                output_path = os.path.join(temp_dir, "preview.mp4")
                
                config = ProjectConfig(
                    audio_file=st.session_state.audio_path,
                    output_file=output_path,
                    visual=VisualConfig(
                        type=st.session_state.selected_visualizer,
                        resolution=(854, 480),
                        fps=30,
                        colors=st.session_state.config['colors']
                    ),
                    postprocess=st.session_state.config['postprocess']
                )
                
                try:
                    pipeline = PreviewPipeline(config)
                    
                    progress_bar = st.progress(0.0)
                    def progress_cb(p, msg):
                        progress_bar.progress(min(p, 1.0))
                    
                    pipeline.run(preview_mode=True, preview_duration=preview_duration,
                               progress_callback=progress_cb)
                    
                    if os.path.exists(output_path):
                        st.session_state.output_path = output_path
                        st.success("✅ Vorschau fertig!")
                        
                        with open(output_path, 'rb') as f:
                            st.video(f.read())
                except Exception as e:
                    st.error(f"Fehler: {e}")
        
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
            with st.spinner("Rendere finales Video..."):
                temp_dir = tempfile.mkdtemp()
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
                
                try:
                    pipeline = RenderPipeline(config)
                    
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
                    st.error(f"Fehler: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# PRESETS PAGE
# ============================================================================

def render_presets_page():
    """Seite für Preset-Verwaltung."""
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <h2 class="gradient-text">🎨 Preset Verwaltung</h2>
        <p style="color: rgba(255,255,255,0.6);">Speichere und verwalte deine Visualizer-Einstellungen</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialisiere Preset Manager
    pm = init_preset_manager()
    
    # Tabs für verschiedene Ansichten
    tab1, tab2, tab3 = st.tabs(["⭐ Favoriten", "🎨 Alle Presets", "💾 Aktuelles Speichern"])
    
    with tab1:
        st.markdown("### Deine Favoriten")
        
        def load_preset(preset):
            st.session_state.selected_visualizer = preset.visual_config.get('type', 'pulsing_core')
            st.session_state.config.update(preset.visual_config)
            st.session_state.config['postprocess'] = preset.postprocess_config
            st.toast(f"Preset '{preset.metadata.name}' geladen!")
        
        def delete_preset(preset_id):
            if pm.delete_preset(preset_id):
                st.success("Preset gelöscht!")
                st.rerun()
        
        PresetUI.render_preset_gallery(pm, load_preset, delete_preset, filter_favorites=True)
    
    with tab2:
        # Such-Filter
        search = st.text_input("🔍 Presets durchsuchen", placeholder="Name oder Beschreibung...")
        
        PresetUI.render_preset_gallery(pm, load_preset, delete_preset, 
                                       filter_favorites=False, search_term=search)
    
    with tab3:
        st.markdown("### Aktuelle Einstellungen speichern")
        
        col1, col2 = st.columns(2)
        
        with col1:
            preset_name = st.text_input("Preset Name", 
                                       value=f"Preset {datetime.now().strftime('%d.%m.%Y')}")
            preset_desc = st.text_area("Beschreibung", max_chars=200)
            preset_tags = st.text_input("Tags (komma-getrennt)")
        
        with col2:
            st.markdown("**Vorschau aktueller Einstellungen:**")
            st.json({
                'visualizer': st.session_state.selected_visualizer,
                'resolution': st.session_state.config.get('resolution'),
                'fps': st.session_state.config.get('fps'),
                'colors': st.session_state.config.get('colors')
            })
        
        if st.button("💾 Als Preset speichern", type="primary", use_container_width=True):
            try:
                preset_id = pm.save_preset(
                    name=preset_name,
                    visual_config={
                        'type': st.session_state.selected_visualizer,
                        'resolution': st.session_state.config.get('resolution'),
                        'fps': st.session_state.config.get('fps'),
                        'colors': st.session_state.config.get('colors'),
                        'params': st.session_state.config.get('params', {})
                    },
                    postprocess_config=st.session_state.config.get('postprocess', {}),
                    description=preset_desc,
                    tags=[t.strip() for t in preset_tags.split(",") if t.strip()]
                )
                
                # Versuche Thumbnail zu generieren
                if st.session_state.preview_frame is not None:
                    pm.generate_thumbnail(preset_id, st.session_state.preview_frame)
                
                st.success(f"✅ Preset '{preset_name}' gespeichert!")
                st.balloons()
                
            except Exception as e:
                st.error(f"❌ Fehler beim Speichern: {e}")
        
        # Import/Export
        st.divider()
        st.markdown("### Import / Export")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Preset importieren**")
            uploaded = st.file_uploader("ZIP-Datei auswählen", type=['zip'])
            if uploaded:
                temp_path = Path(tempfile.gettempdir()) / uploaded.name
                with open(temp_path, 'wb') as f:
                    f.write(uploaded.getvalue())
                
                imported_id = pm.import_preset(str(temp_path))
                if imported_id:
                    st.success(f"✅ Import erfolgreich!")
                else:
                    st.error("❌ Import fehlgeschlagen")
        
        with col2:
            st.markdown("**Preset exportieren**")
            all_presets = pm.list_presets()
            if all_presets:
                export_options = {p.metadata.name: p.id for p in all_presets}
                selected = st.selectbox("Preset wählen", options=list(export_options.keys()))
                
                if st.button("📥 Als ZIP exportieren"):
                    export_path = Path(tempfile.gettempdir()) / f"{selected}_export.zip"
                    if pm.export_preset(export_options[selected], str(export_path)):
                        with open(export_path, 'rb') as f:
                            st.download_button(
                                "⬇️ Download ZIP",
                                f.read(),
                                file_name=f"{selected}_export.zip",
                                mime="application/zip"
                            )

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
                    <div class="template-icon">{template['icon']}</div>
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
        
        st.markdown("""
        <div class="glass-card">
            <h4>🎚️ Audio-Feature Binding</h4>
            <p style="color: rgba(255,255,255,0.6);">Verbinde Audio-Features mit visuellen Parametern</p>
        </div>
        """, unsafe_allow_html=True)
        
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
            code = st.text_area("", template_code, height=400)
        
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
        viz_name = st.text_input("Visualizer Name")
        viz_desc = st.text_area("Beschreibung")
        viz_category = st.selectbox("Kategorie", 
                                   ["Bass", "Equalizer", "Ambient", "Energetic", 
                                    "Minimal", "Retro", "Custom"])
        
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
    templates = {
        "circle": '''
@register_visualizer("my_circle")
class MyCircleVisualizer(BaseVisualizer):
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
        "blank": '''
@register_visualizer("my_visualizer")
class MyVisualizer(BaseVisualizer):
    def setup(self):
        # Initialisierung hier
        pass
    
    def render_frame(self, frame_idx: int) -> np.ndarray:
        f = self.get_feature_at_frame(frame_idx)
        # f enthält: rms, onset, chroma, spectral_centroid, progress
        
        img = Image.new('RGB', (self.width, self.height), (10, 10, 10))
        draw = ImageDraw.Draw(img)
        
        # Deine Zeichen-Logik hier
        
        return np.array(img)
'''
    }
    return templates.get(template_id, templates["blank"])

# ============================================================================
# MAIN APP
# ============================================================================

def register_keyboard_shortcuts():
    """Registriert alle Keyboard Shortcuts."""
    manager = st.session_state.keyboard_manager
    
    def on_open():
        st.session_state.current_step = 'upload'
        st.rerun()
    
    def on_render():
        if st.session_state.audio_path:
            st.session_state.current_step = 'export'
            st.rerun()
    
    def on_save():
        save_project()
    
    def on_undo():
        undo_last_change()
    
    def on_redo():
        redo_last_change()
    
    manager.register(ShortcutKey.OPEN, "Audio öffnen", on_open)
    manager.register(ShortcutKey.SAVE, "Projekt speichern (Ctrl+S)", on_save)
    manager.register(ShortcutKey.RENDER, "Video rendern", on_render)
    manager.register(ShortcutKey.UNDO, "Rückgängig", on_undo)
    manager.register(ShortcutKey.REDO, "Wiederholen", on_redo)


def save_project():
    """Speichert das aktuelle Projekt manuell."""
    autosave = st.session_state.autosave
    config = build_current_config()
    
    if autosave.save(config, force=True):
        st.session_state.last_auto_save = datetime.now()
        st.toast("💾 Projekt gespeichert!", icon="✅")
    else:
        st.toast("❌ Speichern fehlgeschlagen", icon="⚠️")


def build_current_config() -> dict:
    """Baut die aktuelle Config aus Session State."""
    return {
        'project_name': st.session_state.project_name,
        'audio_path': st.session_state.audio_path,
        'audio_name': st.session_state.audio_name,
        'selected_visualizer': st.session_state.selected_visualizer,
        'config': st.session_state.config,
        'current_step': st.session_state.current_step
    }


def undo_last_change():
    """Macht die letzte Änderung rückgängig."""
    undo_mgr = st.session_state.undo_manager
    
    if undo_mgr.can_undo():
        state = undo_mgr.undo()
        if state:
            apply_config_state(state)
            st.toast("↩️ Rückgängig", icon="✅")
            st.rerun()
    else:
        st.toast("Nichts zum Rückgängig machen", icon="ℹ️")


def redo_last_change():
    """Wiederholt die letzte Änderung."""
    undo_mgr = st.session_state.undo_manager
    
    if undo_mgr.can_redo():
        state = undo_mgr.redo()
        if state:
            apply_config_state(state)
            st.toast("↪️ Wiederholt", icon="✅")
            st.rerun()
    else:
        st.toast("Nichts zum Wiederholen", icon="ℹ️")


def apply_config_state(state: dict):
    """Wendet einen gespeicherten Config-State an."""
    if 'audio_path' in state:
        st.session_state.audio_path = state['audio_path']
    if 'audio_name' in state:
        st.session_state.audio_name = state['audio_name']
    if 'selected_visualizer' in state:
        st.session_state.selected_visualizer = state['selected_visualizer']
    if 'config' in state:
        st.session_state.config = state['config']
    if 'current_step' in state:
        st.session_state.current_step = state['current_step']


def check_auto_save():
    """Prüft und führt Auto-Save durch."""
    autosave = st.session_state.autosave
    config = build_current_config()
    
    if autosave.save(config):
        st.session_state.last_auto_save = datetime.now()


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
    
    # Load Visualizer Plugins
    VisualizerRegistry.autoload()
    
    # Register Keyboard Shortcuts
    register_keyboard_shortcuts()
    
    # Check Auto-Save
    check_auto_save()
    
    # Sidebar für Extra-Funktionen
    with st.sidebar:
        st.markdown("## 🎵 Audio Visualizer Pro")
        
        # Schnell-Actions mit Icons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🏠 Home", use_container_width=True):
                st.session_state.current_step = 'upload'
                st.rerun()
        with col2:
            if st.button("💾 Speichern", use_container_width=True):
                save_project()
        
        col3, col4 = st.columns(2)
        with col3:
            if st.button("↩️ Undo", use_container_width=True):
                undo_last_change()
        with col4:
            if st.button("↪️ Redo", use_container_width=True):
                redo_last_change()
        
        if st.button("🎨 Meine Presets", use_container_width=True):
            st.session_state.current_step = 'presets'
            st.rerun()
        
        if SOUNDDEVICE_AVAILABLE:
            if st.button("🎤 Real-Time", use_container_width=True):
                st.session_state.current_step = 'realtime'
                st.rerun()
        
        if st.button("🧙 Visualizer Wizard", use_container_width=True):
            st.session_state.show_wizard = True
            st.rerun()
        
        st.markdown("---")
        
        # Auto-Save Status
        with st.container():
            st.markdown("### 💾 Auto-Save")
            
            autosave = st.session_state.autosave
            save_info = autosave.get_last_save_info()
            
            if save_info:
                age_minutes = int(save_info['age_seconds'] / 60)
                if age_minutes < 1:
                    st.success("✅ Gerade gespeichert")
                elif age_minutes < 5:
                    st.success(f"🟢 Vor {age_minutes} Min.")
                else:
                    st.warning(f"🟡 Vor {age_minutes} Min.")
            else:
                st.info("⚪ Noch nicht gespeichert")
            
            # Manuelles Speichern
            if st.button("🔄 Jetzt speichern", use_container_width=True):
                save_project()
        
        st.markdown("---")
        
        # Keyboard Shortcuts
        with st.expander("⌨️ Shortcuts"):
            st.markdown("""
            **Ctrl+O** - Audio öffnen  
            **Ctrl+S** - Speichern  
            **Ctrl+R** - Render  
            **Ctrl+Z** - Rückgängig  
            **Ctrl+Y** - Wiederholen  
            """)
        
        st.markdown("---")
        
        # Schnell-Info
        if st.session_state.audio_path:
            st.markdown("### 📊 Aktuelles Projekt")
            st.markdown(f"**Audio:** {st.session_state.audio_name}")
            
            viz_info = get_visualizer_info()
            selected = viz_info.get(st.session_state.selected_visualizer, {})
            st.markdown(f"**Visualizer:** {selected.get('name', 'Unknown')}")
        
        st.markdown("---")
        st.markdown("<p style='color: #666; font-size: 0.75em;'>v2.1 mit Shortcuts & Auto-Save</p>", 
                   unsafe_allow_html=True)
    
    # Show Wizard or Main Content
    if st.session_state.get('show_wizard'):
        if st.button("← Zurück zum Editor"):
            st.session_state.show_wizard = False
            st.rerun()
        render_visualizer_wizard()
    else:
        # Main Content with Stepper
        render_stepper()
        
        # Render aktuellen Schritt
        step_pages = {
            'upload': render_upload_page,
            'visualize': render_visualize_page,
            'customize': render_customize_page,
            'preview': render_customize_page,  # Temporär
            'export': render_export_page,
            'presets': render_presets_page,
            'realtime': render_realtime_page
        }
        
        current_page = step_pages.get(st.session_state.current_step, render_upload_page)
        current_page()

if __name__ == "__main__":
    main()
