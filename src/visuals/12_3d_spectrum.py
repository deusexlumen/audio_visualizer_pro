"""
12_3d_spectrum.py - 3D Spectrum Visualizer

3D-Balken-Equalizer mit Perspektive.
Balken reagieren auf Frequenzbänder und haben Tiefe.
Ideal für EDM, Techno und elektronische Musik.
"""

import numpy as np
import colorsys
from PIL import Image, ImageDraw
from .base import BaseVisualizer
from .registry import register_visualizer


@register_visualizer("3d_spectrum")
class Spectrum3DVisualizer(BaseVisualizer):
    """
    3D-Spektrum-Visualisierung mit perspektivischen Balken.
    
    Simulierte 3D-Tiefe durch Schatten und Perspektive.
    Nutzt Chroma-Frequenzen für Farbgebung.
    """
    
    def setup(self):
        """Initialisiere 3D-Parameter."""
        self.num_bars = 32
        self.bar_width = self.width // (self.num_bars * 2)
        
        # Perspektive
        self.horizon_y = self.height // 3
        self.floor_y = self.height - 50
        
        # Balken-Positionen (x in der Tiefe)
        self.bar_positions = np.linspace(-1, 1, self.num_bars)
        
    def project_3d(self, x: float, z: float, height: float) -> tuple:
        """
        Projiziert 3D-Koordinaten zu 2D.
        
        Args:
            x: Position links/rechts (-1 bis 1)
            z: Tiefe (0 = vorne, 1 = hinten)
            height: Balkenhöhe
            
        Returns:
            (screen_x, screen_y, scale)
        """
        # Perspektivische Skalierung
        scale = 1 - z * 0.6  # Hinten kleiner
        
        # Bildschirm-Position
        screen_x = self.width // 2 + x * (self.width // 2) * scale
        
        # Boden-Position (y)
        ground_y = self.floor_y - z * (self.floor_y - self.horizon_y) * 0.5
        
        # Balken-Top (von Boden nach oben)
        bar_height = height * scale * (self.floor_y - self.horizon_y)
        screen_y = ground_y - bar_height
        
        return int(screen_x), int(screen_y), scale
    
    def render_frame(self, frame_idx: int) -> np.ndarray:
        # Features holen
        f = self.get_feature_at_frame(frame_idx)
        rms = f['rms']
        onset = f['onset']
        chroma = f['chroma']
        spectral = f['spectral_centroid']
        
        # Hintergrund (Gradient von oben nach unten)
        img = Image.new('RGB', (self.width, self.height), (5, 5, 15))
        draw = ImageDraw.Draw(img)
        
        # Himmel-Gradient
        for y in range(self.horizon_y):
            t = y / self.horizon_y
            color = tuple(int(5 + t * 15) for _ in range(3))
            draw.line([(0, y), (self.width, y)], fill=color)
        
        # Boden-Gradient
        for y in range(self.horizon_y, self.height):
            t = (y - self.horizon_y) / (self.height - self.horizon_y)
            color = (int(10 + t * 5), int(10 + t * 5), int(20 + t * 10))
            draw.line([(0, y), (self.width, y)], fill=color)
        
        # Dominante Farbe aus Chroma
        dominant_note = np.argmax(chroma)
        base_hue = dominant_note / 12.0
        
        # Rendere Balken von hinten nach vorne (Painter's Algorithm)
        for i, z in enumerate(np.linspace(0.9, 0, self.num_bars)):
            # Frequenz-Wert für diesen Balken (simuliert aus verschiedenen Features)
            freq_idx = int(i / self.num_bars * 12) % 12
            freq_value = chroma[freq_idx] * (0.5 + spectral * 0.5)
            
            # Höhe mit Animation
            anim = np.sin(frame_idx * 0.05 + i * 0.2) * 0.1
            height = max(0.1, min(1.0, freq_value + anim + rms * 0.2))
            
            # Boost bei Onset
            if onset > 0.4:
                height *= 1.3
            
            x = self.bar_positions[i]
            
            # Projiziere zu 2D
            cx, cy, scale = self.project_3d(x, z, height)
            
            # Balken-Abmessungen
            bar_w = int(self.bar_width * scale)
            bar_bottom = int(self.floor_y - z * (self.floor_y - self.horizon_y) * 0.5)
            bar_top = cy
            
            # Farbe basierend auf Position und Höhe
            hue = (base_hue + i * 0.03) % 1.0
            saturation = 0.7 + height * 0.3
            value = 0.5 + height * 0.5
            
            rgb = colorsys.hsv_to_rgb(hue, saturation, value)
            color = tuple(int(c * 255) for c in rgb)
            
            # Dunklere Farbe für Seiten (3D-Effekt)
            shadow_color = tuple(int(c * 0.6) for c in color)
            highlight_color = tuple(min(255, int(c * 1.3)) for c in color)
            
            # Zeichne Balken (von hinten)
            left = cx - bar_w // 2
            right = cx + bar_w // 2
            
            # Tiefe-Offset für 3D-Effekt
            depth_offset = int(10 * scale)
            
            # Seiten (3D-Tiefe)
            draw.polygon([
                (right, bar_top),
                (right + depth_offset, bar_top - depth_offset),
                (right + depth_offset, bar_bottom - depth_offset),
                (right, bar_bottom)
            ], fill=shadow_color)
            
            # Oben (3D-Dach)
            draw.polygon([
                (left, bar_top),
                (left + depth_offset, bar_top - depth_offset),
                (right + depth_offset, bar_top - depth_offset),
                (right, bar_top)
            ], fill=highlight_color)
            
            # Front (Hauptfläche)
            draw.rectangle([left, bar_top, right, bar_bottom], fill=color)
            
            # Glanz oben
            if height > 0.7:
                glow_h = int(bar_w * 0.3)
                draw.rectangle([left + 2, bar_top, right - 2, bar_top + glow_h], 
                             fill=highlight_color)
        
        # Horizont-Linie
        draw.line([(0, self.horizon_y), (self.width, self.horizon_y)], 
                 fill=(40, 40, 60), width=1)
        
        return np.array(img)
