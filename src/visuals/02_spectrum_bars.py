"""
02_spectrum_bars.py - Equalizer-Style Spectrum Bars

Klassischer 40-Balken Equalizer-Look mit Chroma-basierten Farbverläufen.
"""

import numpy as np
import colorsys
from PIL import Image, ImageDraw
from .base import BaseVisualizer
from .registry import register_visualizer


@register_visualizer("spectrum_bars")
class SpectrumBarsVisualizer(BaseVisualizer):
    """
    40-Balken Equalizer mit dynamischen Farbverläufen.
    Reagiert auf RMS und spektrale Features.
    """
    
    def setup(self):
        """Initialisiere Balken-Parameter."""
        self.num_bars = 40
        self.bar_width = self.width // (self.num_bars + 4)
        self.bar_spacing = self.bar_width // 4
        self.max_bar_height = int(self.height * 0.7)
        self.base_y = int(self.height * 0.85)
        
    def render_frame(self, frame_idx: int) -> np.ndarray:
        # Hintergrund
        bg_color = self.colors.get('background', (5, 5, 15, 255))
        img = Image.new('RGB', (self.width, self.height), bg_color[:3])
        draw = ImageDraw.Draw(img)
        
        # Features holen
        f = self.get_feature_at_frame(frame_idx)
        rms = f['rms']
        onset = f['onset']
        chroma = f['chroma']
        spectral = f['spectral_centroid']
        
        # Farbschema basierend auf Chroma
        dominant_note = np.argmax(chroma)
        base_hue = dominant_note / 12.0
        
        # Gesamte Breite aller Balken
        total_width = self.num_bars * (self.bar_width + self.bar_spacing)
        start_x = (self.width - total_width) // 2
        
        # Zeichne Balken
        for i in range(self.num_bars):
            # Berechne Balkenhöhe basierend auf verschiedenen Features
            # Simuliere Frequenzbänder durch verschiedene Phasenverschiebungen
            phase = (i / self.num_bars) * np.pi * 2
            time_offset = frame_idx * 0.1
            
            # Kombiniere mehrere Wellenformen
            wave1 = np.sin(phase + time_offset + rms * np.pi) * 0.5 + 0.5
            wave2 = np.sin(phase * 2 + time_offset * 1.5) * 0.3 + 0.3
            wave3 = onset * np.sin(phase * 3 + time_offset * 2) * 0.2
            
            height_factor = (wave1 + wave2 + wave3) / 1.5
            height_factor = np.clip(height_factor * rms * 1.5, 0.1, 1.0)
            
            bar_height = int(self.max_bar_height * height_factor)
            
            # Farbverlauf für diesen Balken
            hue = (base_hue + (i / self.num_bars) * 0.3) % 1.0
            saturation = 0.7 + spectral * 0.3
            value = 0.5 + height_factor * 0.5
            
            rgb = colorsys.hsv_to_rgb(hue, saturation, value)
            color = tuple(int(c * 255) for c in rgb)
            
            # Fallback auf Config-Farben
            if 'primary' in self.colors:
                primary = self.colors['primary'][:3]
                # Interpoliere zwischen Primary und berechneter Farbe
                color = tuple(int(primary[j] * 0.5 + color[j] * 0.5) for j in range(3))
            
            # Balken-Position
            x = start_x + i * (self.bar_width + self.bar_spacing)
            y_top = self.base_y - bar_height
            
            # Zeichne Balken mit abgerundeten Ecken (simuliert)
            draw.rectangle(
                [x, y_top, x + self.bar_width, self.base_y],
                fill=color
            )
            
            # Glühen-Effekt oben
            glow_size = 3
            glow_color = tuple(min(255, c + 50) for c in color)
            draw.rectangle(
                [x, y_top - glow_size, x + self.bar_width, y_top + glow_size],
                fill=glow_color
            )
        
        # Reflexion/Boden-Effekt
        reflection_height = self.max_bar_height // 4
        for y in range(reflection_height):
            alpha = 1.0 - (y / reflection_height)
            line_color = tuple(int(20 + 30 * alpha * rms) for _ in range(3))
            draw.line(
                [(0, self.base_y + y), (self.width, self.base_y + y)],
                fill=line_color
            )
        
        # Beat-Indikator
        if onset > 0.4:
            flash_alpha = int(onset * 30)
            draw.rectangle([0, 0, self.width, self.height], 
                          fill=(flash_alpha, flash_alpha, flash_alpha))
        
        return np.array(img)
