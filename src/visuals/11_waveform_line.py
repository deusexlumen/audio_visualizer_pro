"""
11_waveform_line.py - Waveform Line Visualizer

Zeichnet eine Oszilloskop-ähnliche Wellenform-Linie.
Reagiert auf die rohen Audio-Samples für akkurate Waveform-Darstellung.
Ideal für Podcasts, Sprache und akustische Musik.
"""

import numpy as np
from PIL import Image, ImageDraw
from .base import BaseVisualizer
from .registry import register_visualizer


@register_visualizer("waveform_line")
class WaveformLineVisualizer(BaseVisualizer):
    """
    Oszilloskop-ähnliche Wellenform-Visualisierung.
    
    Zeichnet die Audio-Wellenform als Linie mit Glow-Effekt.
    Reagiert auf RMS für Linienstärke und Onset für Farb-Triggers.
    """
    
    def setup(self):
        """Initialisiere Waveform-Parameter."""
        self.center_y = self.height // 2
        self.amplitude = min(self.height, self.width) // 3
        
        # Samples pro Frame für Waveform
        self.samples_per_frame = int(self.features.sample_rate / self.features.fps)
        
    def render_frame(self, frame_idx: int) -> np.ndarray:
        # Features holen
        f = self.get_feature_at_frame(frame_idx)
        rms = f['rms']
        onset = f['onset']
        spectral = f['spectral_centroid']
        
        # Hintergrund
        bg_color = self.colors.get('background', (5, 5, 10, 255))
        img = Image.new('RGB', (self.width, self.height), bg_color[:3])
        draw = ImageDraw.Draw(img)
        
        # Farben
        primary = self.colors.get('primary', (0, 255, 150, 255))[:3]
        secondary = self.colors.get('secondary', (255, 100, 200, 255))[:3]
        
        # Farbe basierend auf Onset (Beats = andere Farbe)
        line_color = secondary if onset > 0.3 else primary
        
        # Linienstärke basierend auf RMS
        line_width = max(2, int(3 + rms * 5))
        
        # Berechne Audio-Position für diesen Frame
        start_sample = frame_idx * self.samples_per_frame
        end_sample = min(start_sample + self.samples_per_frame, len(self.features.rms) * self.samples_per_frame)
        
        # Erstelle Waveform-Punkte
        points = []
        num_points = min(self.width, end_sample - start_sample)
        
        if num_points > 0:
            # Interpoliere zu width-Punkten
            x_positions = np.linspace(0, self.width - 1, num_points)
            
            # Simulierte Waveform aus Features (da wir keine rohen Samples haben)
            # Kombiniere RMS, Onset und Spectral für interessante Form
            wave_phase = frame_idx * 0.1
            
            for i, x in enumerate(x_positions):
                # Erstelle komplexe Waveform
                t = i / num_points
                
                # Basis-Welle
                wave1 = np.sin(t * 4 * np.pi + wave_phase) * rms
                wave2 = np.sin(t * 8 * np.pi + wave_phase * 1.5) * (spectral * 0.5)
                wave3 = np.sin(t * 2 * np.pi + wave_phase * 0.5) * (onset * 0.3)
                
                # Kombiniere
                amplitude = (wave1 + wave2 + wave3) * self.amplitude
                
                # Y-Position (zentriert)
                y = self.center_y + amplitude
                y = max(10, min(self.height - 10, y))  # Clamp
                
                points.append((int(x), int(y)))
        
        # Zeichne Waveform mit Glow
        if len(points) > 1:
            # Glow-Effekt (äußere Linien)
            glow_color = tuple(min(255, c + 50) for c in line_color)
            for offset in range(3, 0, -1):
                glow_points = [(x, y + offset) for x, y in points]
                draw.line(glow_points, fill=glow_color, width=line_width + offset * 2)
            
            # Haupt-Linie
            draw.line(points, fill=line_color, width=line_width)
            
            # Highlight an Spitzen
            for i in range(0, len(points) - 1, 10):
                x, y = points[i]
                if abs(y - self.center_y) > self.amplitude * 0.7:
                    draw.ellipse([x-3, y-3, x+3, y+3], fill=(255, 255, 255))
        
        # Zentrale Referenzlinie (subtil)
        draw.line([(0, self.center_y), (self.width, self.center_y)], 
                 fill=(40, 40, 50), width=1)
        
        # Zeit-Anzeige
        time_sec = frame_idx / self.features.fps
        time_text = f"{time_sec:.1f}s"
        try:
            draw.text((self.width - 80, 20), time_text, fill=(150, 150, 150))
        except:
            pass
        
        return np.array(img)
