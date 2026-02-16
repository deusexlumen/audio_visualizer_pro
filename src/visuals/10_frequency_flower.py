"""
10_frequency_flower.py - Frequency Flower Visualizer

Blumen-artige Visualisierung mit Frequenzbändern als Blütenblätter.
Blütenblätter reagieren auf verschiedene Audio-Features.
"""

import numpy as np
import colorsys
import math
from PIL import Image, ImageDraw
from .base import BaseVisualizer
from .registry import register_visualizer


@register_visualizer("frequency_flower")
class FrequencyFlowerVisualizer(BaseVisualizer):
    """
    Frequency Flower Visualisierung.
    Organische Blumen-Form mit Audio-reaktiven Blütenblättern.
    Ideal für Indie, Folk, Pop, akustische Musik.
    """
    
    def setup(self):
        """Initialisiere Blumen-Parameter."""
        self.center = (self.width // 2, self.height // 2)
        self.num_petals = 8
        self.base_petal_length = min(self.width, self.height) // 3
        self.rotation = 0.0
        
        # Verschiedene Blütenblatt-Größen (wie bei einer echten Blume)
        self.petal_layers = 3
        
    def render_frame(self, frame_idx: int) -> np.ndarray:
        # Features holen
        f = self.get_feature_at_frame(frame_idx)
        rms = f['rms']
        onset = f['onset']
        chroma = f['chroma']
        spectral = f['spectral_centroid']
        progress = f['progress']
        
        # Hintergrund (sanfter Farbverlauf)
        dominant_note = np.argmax(chroma)
        base_hue = dominant_note / 12.0
        
        # Hintergrundfarbe (sehr gedämpft)
        bg_hsv = (base_hue, 0.15, 0.12)
        bg_rgb = colorsys.hsv_to_rgb(*bg_hsv)
        bg_color = tuple(int(c * 255) for c in bg_rgb)
        
        # Fallback
        if 'background' in self.colors:
            bg_color = self.colors['background'][:3]
        
        img = Image.new('RGB', (self.width, self.height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Farbpalette für Blütenblätter
        petal_colors = []
        for i in range(self.num_petals):
            hue = (base_hue + i / self.num_petals * 0.3) % 1.0
            chroma_idx = (dominant_note + i) % 12
            strength = chroma[chroma_idx]
            
            sat = 0.5 + strength * 0.4
            val = 0.6 + rms * 0.3
            
            rgb = colorsys.hsv_to_rgb(hue, sat, val)
            color = tuple(int(c * 255) for c in rgb)
            petal_colors.append(color)
        
        # Rotation aktualisieren
        self.rotation += 0.003 + (rms * 0.02)
        if onset > 0.4:
            self.rotation += 0.08  # Sprung bei Beat
        
        # Zeichne Blütenblätter von hinten nach vorne
        for layer in range(self.petal_layers - 1, -1, -1):
            layer_scale = 1.0 - (layer * 0.25)
            layer_rotation = self.rotation + (layer * np.pi / self.num_petals)
            
            for i in range(self.num_petals):
                angle = (i / self.num_petals) * 2 * math.pi + layer_rotation
                
                # Länge des Blütenblatts reagiert auf Chroma
                chroma_idx = (dominant_note + i + layer * 2) % 12
                petal_length = self.base_petal_length * layer_scale * \
                              (0.6 + chroma[chroma_idx] * 0.5 + rms * 0.3)
                
                # Breite des Blütenblatts
                petal_width = 30 * layer_scale * (1 + rms * 0.5)
                
                # Farbe mit Layer-Variation
                base_color = petal_colors[(i + layer) % self.num_petals]
                if layer > 0:
                    # Äußere Schichten etwas dunkler
                    layer_color = tuple(int(c * (1 - layer * 0.15)) for c in base_color)
                else:
                    layer_color = base_color
                
                self._draw_petal(draw, self.center, angle, petal_length, 
                               petal_width, layer_color, rms)
        
        # Zeichne Blütenmitte (Stempel)
        center_radius = int(25 + rms * 30)
        center_color = self.colors.get('primary', (255, 200, 100, 255))[:3]
        
        # Alternierende Farbe basierend auf Chroma
        center_hue = (base_hue + 0.5) % 1.0
        center_rgb = colorsys.hsv_to_rgb(center_hue, 0.8, 1.0)
        center_color = tuple(int(c * 255) for c in center_rgb)
        
        if 'secondary' in self.colors:
            center_color = self.colors['secondary'][:3]
        
        draw.ellipse([self.center[0] - center_radius, self.center[1] - center_radius,
                      self.center[0] + center_radius, self.center[1] + center_radius],
                     fill=center_color)
        
        # Stempel-Details (kleine Punkte)
        self._draw_stamen(draw, self.center, center_radius, rms, base_hue)
        
        # Pollen/Partikel bei Beats
        if onset > 0.3 or rms > 0.7:
            self._draw_pollen(draw, self.center, self.base_petal_length, 
                             petal_colors, rms, onset, frame_idx)
        
        # Wachsende Ranke/Stengel
        self._draw_stem(draw, self.center, progress, base_hue, rms)
        
        return np.array(img)
    
    def _draw_petal(self, draw: ImageDraw.Draw, center: tuple, angle: float,
                   length: float, width: float, color: tuple, rms: float):
        """Zeichnet ein einzelnes Blütenblatt als organische Form."""
        # Spitze des Blütenblatts
        tip_x = center[0] + math.cos(angle) * length
        tip_y = center[1] + math.sin(angle) * length
        
        # Seitenpunkte des Blütenblatts (für geschwungene Form)
        side_angle1 = angle - math.pi / 6
        side_angle2 = angle + math.pi / 6
        
        side_length = width * 0.8
        side1_x = center[0] + math.cos(angle) * (length * 0.5) + \
                 math.cos(side_angle1) * side_length
        side1_y = center[1] + math.sin(angle) * (length * 0.5) + \
                 math.sin(side_angle1) * side_length
        
        side2_x = center[0] + math.cos(angle) * (length * 0.5) + \
                 math.cos(side_angle2) * side_length
        side2_y = center[1] + math.sin(angle) * (length * 0.5) + \
                 math.sin(side_angle2) * side_length
        
        # Basispunkte
        base_width = width * 0.4
        base_angle1 = angle - math.pi / 4
        base_angle2 = angle + math.pi / 4
        
        base1_x = center[0] + math.cos(base_angle1) * base_width
        base1_y = center[1] + math.sin(base_angle1) * base_width
        
        base2_x = center[0] + math.cos(base_angle2) * base_width
        base2_y = center[1] + math.sin(base_angle2) * base_width
        
        # Zeichne Blütenblatt als Polygon
        points = [
            (base1_x, base1_y),
            (side1_x, side1_y),
            (tip_x, tip_y),
            (side2_x, side2_y),
            (base2_x, base2_y)
        ]
        
        draw.polygon(points, fill=color)
        
        # Zeichne Umriss
        outline_color = tuple(max(0, c - 40) for c in color)
        for i in range(len(points)):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % len(points)]
            draw.line([(x1, y1), (x2, y2)], fill=outline_color, width=max(1, int(rms * 2)))
        
        # Highlight in der Mitte
        mid_x = (center[0] + tip_x) / 2
        mid_y = (center[1] + tip_y) / 2
        highlight_radius = int(width * 0.15)
        highlight_color = tuple(min(255, c + 60) for c in color)
        
        draw.ellipse([mid_x - highlight_radius, mid_y - highlight_radius,
                     mid_x + highlight_radius, mid_y + highlight_radius],
                    fill=highlight_color)
    
    def _draw_stamen(self, draw: ImageDraw.Draw, center: tuple, radius: float, 
                    rms: float, base_hue: float):
        """Zeichnet Stempel-Details in der Blütenmitte."""
        num_stamens = 5
        
        for i in range(num_stamens):
            angle = (i / num_stamens) * 2 * math.pi
            
            # Position des Staubgefäßes
            dist = radius * 0.5
            x = center[0] + math.cos(angle) * dist
            y = center[1] + math.sin(angle) * dist
            
            # Größe pulsiert mit RMS
            stamen_size = int(5 + rms * 8)
            
            # Farbe
            hue = (base_hue + i * 0.1) % 1.0
            rgb = colorsys.hsv_to_rgb(hue, 0.9, 1.0)
            color = tuple(int(c * 255) for c in rgb)
            
            draw.ellipse([x - stamen_size, y - stamen_size,
                         x + stamen_size, y + stamen_size],
                        fill=color)
    
    def _draw_pollen(self, draw: ImageDraw.Draw, center: tuple, petal_length: float,
                    colors: list, rms: float, onset: float, frame_idx: int):
        """Zeichnet schwebende Pollen/Partikel um die Blume."""
        np.random.seed(frame_idx // 5)
        num_particles = int(10 + rms * 20)
        
        for i in range(num_particles):
            # Zufällige Position im Bereich der Blütenblätter
            angle = np.random.random() * 2 * math.pi
            dist = np.random.uniform(petal_length * 0.3, petal_length * 1.2)
            
            x = center[0] + math.cos(angle) * dist
            y = center[1] + math.sin(angle) * dist
            
            # Partikel-Größe
            size = int(2 + rms * 4 + onset * 3)
            
            # Farbe
            color_idx = i % len(colors)
            color = colors[color_idx]
            
            # Zeichne mit Glow-Effekt
            for j in range(3):
                glow_size = size + j * 2
                glow_intensity = 1 - j * 0.3
                glow_color = tuple(int(c * glow_intensity) for c in color)
                
                if j == 0:
                    draw.ellipse([x - glow_size, y - glow_size,
                                 x + glow_size, y + glow_size],
                                fill=glow_color)
                else:
                    draw.ellipse([x - glow_size, y - glow_size,
                                 x + glow_size, y + glow_size],
                                outline=glow_color, width=1)
    
    def _draw_stem(self, draw: ImageDraw.Draw, center: tuple, progress: float,
                  base_hue: float, rms: float):
        """Zeichnet einen wachsenden Stängel/Stiel."""
        # Stängel wächst während des Songs
        stem_length = int(self.height * 0.4 * progress)
        
        if stem_length < 10:
            return
        
        # Stängel-Position (von der Mitte nach unten)
        stem_top = center[1] + 20
        stem_bottom = stem_top + stem_length
        stem_x = center[0]
        
        # Organische Krümmung
        bend = np.sin(progress * 10) * 20
        
        # Stängel-Farbe (grünlich)
        stem_hue = (base_hue + 0.3) % 1.0  # Verschiebe zu Grün
        rgb = colorsys.hsv_to_rgb(stem_hue, 0.6, 0.4)
        stem_color = tuple(int(c * 255) for c in rgb)
        
        # Zeichne gekrümmten Stängel
        points_left = []
        points_right = []
        
        stem_width = 8
        
        for i in range(stem_length):
            y = stem_top + i
            # Sinusförmige Krümmung
            x_offset = math.sin(i * 0.02 + progress * 5) * bend
            x = stem_x + x_offset
            
            width_at_y = stem_width * (1 - i / stem_length * 0.3)  # Wird dünner
            points_left.append((x - width_at_y / 2, y))
            points_right.append((x + width_at_y / 2, y))
        
        # Kombiniere Punkte für Polygon
        if len(points_left) > 1:
            all_points = points_left + points_right[::-1]
            draw.polygon(all_points, fill=stem_color)
