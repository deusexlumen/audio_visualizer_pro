"""
07_sacred_mandala.py - Sacred Geometry Mandala Visualizer

Inspiriert von heiliger Geometrie und Mandalas.
Erzeugt rotierende, audio-reaktive geometrische Muster.
"""

import numpy as np
import colorsys
import math
from PIL import Image, ImageDraw
from .base import BaseVisualizer
from .registry import register_visualizer


@register_visualizer("sacred_mandala")
class SacredMandalaVisualizer(BaseVisualizer):
    """
    Sacred Geometry Mandala Visualisierung.
    Rotierende geometrische Muster, die auf Chroma und RMS reagieren.
    Ideal für Ambient, Meditation, spirituelle Musik.
    """
    
    def setup(self):
        """Initialisiere Mandala-Parameter."""
        self.center = (self.width // 2, self.height // 2)
        self.base_radius = min(self.width, self.height) // 3
        self.rotation = 0.0
        self.layers = []
        
        # Verschiedene heilige Geometrie-Formen
        self.shapes = [
            {'sides': 6, 'name': 'flower_of_life'},
            {'sides': 8, 'name': 'octagon'},
            {'sides': 12, 'name': 'zodiac'},
            {'sides': 3, 'name': 'trinity'},
        ]
        
    def render_frame(self, frame_idx: int) -> np.ndarray:
        # Features holen
        f = self.get_feature_at_frame(frame_idx)
        rms = f['rms']
        onset = f['onset']
        chroma = f['chroma']
        spectral = f['spectral_centroid']
        
        # Hintergrund (dunkel mit leichtem Farbton)
        dominant_note = np.argmax(chroma)
        base_hue = dominant_note / 12.0
        bg_hsv = (base_hue, 0.3, 0.08)
        bg_rgb = colorsys.hsv_to_rgb(*bg_hsv)
        bg_color = tuple(int(c * 255) for c in bg_rgb)
        
        # Fallback
        if 'background' in self.colors:
            bg_color = self.colors['background'][:3]
        
        img = Image.new('RGB', (self.width, self.height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Farbpalette basierend auf Chroma
        colors = []
        for i, strength in enumerate(chroma):
            hue = i / 12.0
            sat = 0.6 + strength * 0.4
            val = 0.5 + strength * 0.5
            rgb = colorsys.hsv_to_rgb(hue, sat, val)
            color = tuple(int(c * 255) for c in rgb)
            colors.append(color)
        
        # Fallback auf Config-Farben
        if 'primary' in self.colors:
            colors[dominant_note] = self.colors['primary'][:3]
        
        # Rotation basierend auf Zeit und Beat
        self.rotation += 0.005 + (rms * 0.02)
        if onset > 0.4:
            self.rotation += 0.1  # Sprung bei Beat
        
        # Verschiedene Mandala-Schichten zeichnen
        # 1. Äußerer Ring (Blume des Lebens - überlappende Kreise)
        self._draw_flower_of_life(draw, self.center, self.base_radius, 
                                   colors[dominant_note], rms, chroma)
        
        # 2. Sechseck-Muster
        hex_color = colors[(dominant_note + 2) % 12]
        self._draw_polygon_ring(draw, self.center, self.base_radius * 0.75, 
                                6, hex_color, self.rotation, rms)
        
        # 3. Stern-Muster (12-spitzig)
        star_color = colors[(dominant_note + 4) % 12]
        self._draw_star(draw, self.center, self.base_radius * 0.5, 
                       12, star_color, self.rotation * -1.5, rms)
        
        # 4. Inneres Dreieck
        tri_color = colors[(dominant_note + 6) % 12]
        self._draw_polygon_ring(draw, self.center, self.base_radius * 0.3, 
                                3, tri_color, self.rotation * 2, rms)
        
        # 5. Zentrumspuls
        pulse_radius = int(20 + rms * 60)
        center_color = colors[dominant_note]
        draw.ellipse([self.center[0] - pulse_radius, self.center[1] - pulse_radius,
                      self.center[0] + pulse_radius, self.center[1] + pulse_radius],
                     outline=center_color, width=3)
        
        # Verbindungslinien zwischen den Schichten bei starkem Beat
        if onset > 0.3:
            self._draw_connection_lines(draw, self.center, self.base_radius, 
                                       colors[dominant_note], onset)
        
        # Partikel/Spuren bei hohem RMS
        if rms > 0.6:
            self._draw_energy_particles(draw, self.center, self.base_radius, 
                                       colors, rms, frame_idx)
        
        return np.array(img)
    
    def _draw_flower_of_life(self, draw: ImageDraw.Draw, center: tuple, radius: float, 
                             color: tuple, rms: float, chroma: np.ndarray):
        """Zeichnet das Muster der Blume des Lebens (überlappende Kreise)."""
        num_circles = 6
        circle_radius = radius * 0.3
        
        for i in range(num_circles):
            angle = (i / num_circles) * 2 * math.pi + self.rotation
            # Position auf einem Kreis
            x = center[0] + math.cos(angle) * (radius * 0.5)
            y = center[1] + math.sin(angle) * (radius * 0.5)
            
            # Farbe basierend auf Chroma-Position
            color_idx = i % 12
            hue = color_idx / 12.0
            chroma_strength = chroma[color_idx]
            rgb = colorsys.hsv_to_rgb(hue, 0.7 + chroma_strength * 0.3, 
                                      0.5 + chroma_strength * 0.5)
            circle_color = tuple(int(c * 255) for c in rgb)
            
            # Radius pulsiert mit RMS
            pulsed_radius = int(circle_radius * (1 + rms * 0.3))
            
            draw.ellipse([x - pulsed_radius, y - pulsed_radius,
                         x + pulsed_radius, y + pulsed_radius],
                        outline=circle_color, width=2)
        
        # Zentraler Kreis
        center_radius = int(circle_radius * (1 + rms * 0.5))
        draw.ellipse([center[0] - center_radius, center[1] - center_radius,
                     center[0] + center_radius, center[1] + center_radius],
                    outline=color, width=3)
    
    def _draw_polygon_ring(self, draw: ImageDraw.Draw, center: tuple, radius: float,
                           sides: int, color: tuple, rotation: float, rms: float):
        """Zeichnet einen Ring aus Polygonen."""
        points = []
        for i in range(sides):
            angle = (i / sides) * 2 * math.pi + rotation
            x = center[0] + math.cos(angle) * radius
            y = center[1] + math.sin(angle) * radius
            points.append((x, y))
        
        # Verbinde die Punkte
        for i in range(sides):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % sides]
            line_width = max(1, int(2 + rms * 3))
            draw.line([(x1, y1), (x2, y2)], fill=color, width=line_width)
        
        # Zeichne auch Linien zum Zentrum bei hohem RMS
        if rms > 0.5:
            for x, y in points:
                draw.line([(x, y), center], fill=color, width=1)
    
    def _draw_star(self, draw: ImageDraw.Draw, center: tuple, radius: float,
                  points_count: int, color: tuple, rotation: float, rms: float):
        """Zeichnet einen Stern."""
        outer_points = []
        inner_points = []
        
        for i in range(points_count):
            # Äußere Punkte
            angle = (i / points_count) * 2 * math.pi + rotation
            outer_x = center[0] + math.cos(angle) * radius
            outer_y = center[1] + math.sin(angle) * radius
            outer_points.append((outer_x, outer_y))
            
            # Innere Punkte (zwischen den äußeren)
            inner_angle = ((i + 0.5) / points_count) * 2 * math.pi + rotation
            inner_radius = radius * 0.4 * (1 + rms * 0.3)
            inner_x = center[0] + math.cos(inner_angle) * inner_radius
            inner_y = center[1] + math.sin(inner_angle) * inner_radius
            inner_points.append((inner_x, inner_y))
        
        # Verbinde äußere und innere Punkte abwechselnd
        all_points = []
        for i in range(points_count):
            all_points.append(outer_points[i])
            all_points.append(inner_points[i])
        
        # Zeichne den Stern
        for i in range(len(all_points)):
            x1, y1 = all_points[i]
            x2, y2 = all_points[(i + 1) % len(all_points)]
            draw.line([(x1, y1), (x2, y2)], fill=color, width=max(1, int(2 + rms * 2)))
    
    def _draw_connection_lines(self, draw: ImageDraw.Draw, center: tuple, radius: float,
                               color: tuple, intensity: float):
        """Zeichnet radiale Linien bei Beats."""
        num_lines = 12
        line_length = radius * 0.2 * intensity
        
        for i in range(num_lines):
            angle = (i / num_lines) * 2 * math.pi + self.rotation
            x1 = center[0] + math.cos(angle) * radius
            y1 = center[1] + math.sin(angle) * radius
            x2 = center[0] + math.cos(angle) * (radius + line_length)
            y2 = center[1] + math.sin(angle) * (radius + line_length)
            
            draw.line([(x1, y1), (x2, y2)], fill=color, width=max(1, int(intensity * 4)))
    
    def _draw_energy_particles(self, draw: ImageDraw.Draw, center: tuple, radius: float,
                               colors: list, rms: float, frame_idx: int):
        """Zeichnet Energie-Partikel, die aus dem Zentrum strahlen."""
        np.random.seed(frame_idx // 10)  # Ändere alle 10 Frames
        num_particles = int(rms * 20)
        
        for i in range(num_particles):
            angle = np.random.random() * 2 * math.pi
            distance = radius * (0.8 + np.random.random() * 0.5)
            
            x = center[0] + math.cos(angle) * distance
            y = center[1] + math.sin(angle) * distance
            
            particle_size = int(2 + rms * 4)
            color_idx = i % len(colors)
            
            draw.ellipse([x - particle_size, y - particle_size,
                         x + particle_size, y + particle_size],
                        fill=colors[color_idx])
