"""
03_chroma_field.py - Chroma-basiertes Partikel-Feld

Partikel, die sich basierend auf den 12 Halbtönen bewegen und farblich anpassen.
"""

import numpy as np
import colorsys
from PIL import Image, ImageDraw
from .base import BaseVisualizer
from .registry import register_visualizer


@register_visualizer("chroma_field")
class ChromaFieldVisualizer(BaseVisualizer):
    """
    Partikel-Feld, das auf die 12 Halbtöne reagiert.
    Jedes Partikel repräsentiert einen Ton und pulsiert entsprechend.
    """
    
    def setup(self):
        """Initialisiere Partikel-System."""
        self.num_particles = 100
        self.particles = []
        
        # Initialisiere Partikel mit zufälligen Positionen
        np.random.seed(42)  # Für reproduzierbare Ergebnisse
        for i in range(self.num_particles):
            particle = {
                'x': np.random.randint(50, self.width - 50),
                'y': np.random.randint(50, self.height - 50),
                'base_x': np.random.randint(50, self.width - 50),
                'base_y': np.random.randint(50, self.height - 50),
                'size': np.random.randint(3, 12),
                'note': i % 12,  # Jeder Tonart zugeordnet
                'phase': np.random.random() * np.pi * 2,
                'speed': 0.5 + np.random.random() * 1.5
            }
            self.particles.append(particle)
    
    def render_frame(self, frame_idx: int) -> np.ndarray:
        # Hintergrund mit leichtem Trail-Effekt
        bg_color = self.colors.get('background', (5, 5, 10, 255))
        img = Image.new('RGB', (self.width, self.height), bg_color[:3])
        draw = ImageDraw.Draw(img)
        
        # Features holen
        f = self.get_feature_at_frame(frame_idx)
        rms = f['rms']
        onset = f['onset']
        chroma = f['chroma']
        spectral = f['spectral_centroid']
        
        # Zeichne Verbindungslinien zwischen nahen Partikeln
        for i, p1 in enumerate(self.particles):
            # Aktualisiere Position basierend auf Chroma-Wert der zugeordneten Note
            note_strength = chroma[p1['note']]
            
            # Bewegung basierend auf Audio
            time = frame_idx * 0.05
            p1['x'] = p1['base_x'] + np.sin(time * p1['speed'] + p1['phase']) * 30 * note_strength
            p1['y'] = p1['base_y'] + np.cos(time * p1['speed'] * 0.7 + p1['phase']) * 20 * note_strength
            
            # Beat-Puls
            if onset > 0.3:
                pulse = 1.0 + onset * 0.5
                p1['x'] += np.sin(frame_idx * 0.5) * 10 * pulse
            
            # Farbe basierend auf Note
            hue = p1['note'] / 12.0
            saturation = 0.6 + note_strength * 0.4
            value = 0.4 + note_strength * 0.6
            
            rgb = colorsys.hsv_to_rgb(hue, saturation, value)
            color = tuple(int(c * 255) for c in rgb)
            
            # Fallback
            if 'primary' in self.colors:
                primary = self.colors['primary'][:3]
                color = tuple(int(primary[j] * 0.3 + color[j] * 0.7) for j in range(3))
            
            # Zeichne Partikel
            size = int(p1['size'] * (0.8 + rms * 0.4))
            x, y = int(p1['x']), int(p1['y'])
            
            # Glühen
            glow = size + 4
            glow_color = tuple(max(0, c - 100) for c in color)
            draw.ellipse([x-glow, y-glow, x+glow, y+glow], fill=glow_color)
            
            # Kern
            draw.ellipse([x-size, y-size, x+size, y+size], fill=color)
            
            # Verbindungslinien zu nahen Partikeln
            for j in range(i + 1, min(i + 5, len(self.particles))):
                p2 = self.particles[j]
                dist = np.sqrt((p1['x'] - p2['x'])**2 + (p1['y'] - p2['y'])**2)
                
                if dist < 100:
                    line_alpha = int((1 - dist / 100) * 80 * note_strength)
                    line_color = tuple(min(255, c + line_alpha) for c in color)
                    draw.line([(x, y), (int(p2['x']), int(p2['y']))], 
                             fill=line_color, width=1)
        
        # Chroma-Ring in der Mitte
        center_x, center_y = self.width // 2, self.height // 2
        ring_radius = 80 + int(rms * 40)
        
        for note in range(12):
            angle = (note / 12.0) * np.pi * 2 - np.pi / 2
            note_strength = chroma[note]
            
            x = center_x + np.cos(angle) * ring_radius
            y = center_y + np.sin(angle) * ring_radius
            
            hue = note / 12.0
            rgb = colorsys.hsv_to_rgb(hue, 0.9, 0.5 + note_strength * 0.5)
            color = tuple(int(c * 255) for c in rgb)
            
            dot_size = int(8 + note_strength * 12)
            draw.ellipse([x-dot_size, y-dot_size, x+dot_size, y+dot_size], fill=color)
        
        return np.array(img)
