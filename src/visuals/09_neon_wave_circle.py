"""
09_neon_wave_circle.py - Neon Wave Circle Visualizer

Kreisförmige Wellenvisualisierung mit Neon-Effekten.
Mehrere konzentrische Ringe reagieren auf verschiedene Frequenzbänder.
"""

import numpy as np
import colorsys
import math
from PIL import Image, ImageDraw
from .base import BaseVisualizer
from .registry import register_visualizer


@register_visualizer("neon_wave_circle")
class NeonWaveCircleVisualizer(BaseVisualizer):
    """
    Neon Wave Circle Visualisierung.
    Konzentrische Ringe, die auf RMS und Frequenzen reagieren.
    Ideal für EDM, Techno, Synthwave.
    """
    
    def setup(self):
        """Initialisiere Ring-Parameter."""
        self.center = (self.width // 2, self.height // 2)
        self.max_radius = min(self.width, self.height) // 2 - 50
        self.num_rings = 5
        self.ring_data = []
        
        # Initialisiere Ring-Daten
        for i in range(self.num_rings):
            self.ring_data.append({
                'base_radius': (i + 1) * (self.max_radius / self.num_rings),
                'amplitude': 10 + i * 5,
                'frequency': 0.1 + i * 0.02,
                'phase': i * np.pi / 3,
                'wave_count': 6 + i * 2
            })
        
        self.waveform_history = []
        self.max_history = 20
        
    def render_frame(self, frame_idx: int) -> np.ndarray:
        # Features holen
        f = self.get_feature_at_frame(frame_idx)
        rms = f['rms']
        onset = f['onset']
        chroma = f['chroma']
        spectral = f['spectral_centroid']
        
        # Hintergrund (tiefes Schwarz)
        bg_color = self.colors.get('background', (5, 5, 10, 255))
        img = Image.new('RGB', (self.width, self.height), bg_color[:3])
        draw = ImageDraw.Draw(img)
        
        # Farben basierend auf Chroma
        dominant_note = np.argmax(chroma)
        base_hue = dominant_note / 12.0
        
        primary_rgb = colorsys.hsv_to_rgb(base_hue, 0.9, 1.0)
        primary_color = tuple(int(c * 255) for c in primary_rgb)
        
        secondary_hue = (base_hue + 0.33) % 1.0
        secondary_rgb = colorsys.hsv_to_rgb(secondary_hue, 0.8, 1.0)
        secondary_color = tuple(int(c * 255) for c in secondary_rgb)
        
        # Fallback auf Config-Farben
        if 'primary' in self.colors:
            primary_color = self.colors['primary'][:3]
        if 'secondary' in self.colors:
            secondary_color = self.colors['secondary'][:3]
        
        # Zeit-Parameter
        time = frame_idx * 0.03
        
        # Zeichne von außen nach innen für Layering
        for i in range(self.num_rings - 1, -1, -1):
            ring = self.ring_data[i]
            
            # Audio-reaktive Parameter
            audio_boost = 1.0 + rms * 0.5
            if onset > 0.3:
                audio_boost += onset * 0.5
            
            # Radius pulsiert
            current_radius = ring['base_radius'] * audio_boost
            
            # Amplitude reagiert auf Audio
            current_amplitude = ring['amplitude'] * (0.5 + rms * 1.5)
            
            # Farbe für diesen Ring
            ring_hue = (base_hue + i * 0.1) % 1.0
            ring_sat = 0.8 + spectral * 0.2
            ring_val = 0.5 + rms * 0.5
            
            # Verwende Primär- oder Sekundärfarbe abwechselnd
            if i % 2 == 0:
                ring_color = tuple(int(primary_color[j] * (0.5 + ring_val * 0.5)) 
                                  for j in range(3))
            else:
                ring_color = tuple(int(secondary_color[j] * (0.5 + ring_val * 0.5)) 
                                  for j in range(3))
            
            # Zeichne den wellenförmigen Ring
            self._draw_wavy_ring(draw, self.center, current_radius, 
                                current_amplitude, ring['wave_count'],
                                time + ring['phase'], ring_color, rms)
            
            # Glow-Effekt für äußere Ringe
            if i < 2:
                glow_color = tuple(int(c * 0.3) for c in ring_color)
                self._draw_wavy_ring(draw, self.center, current_radius + 4,
                                    current_amplitude, ring['wave_count'],
                                    time + ring['phase'], glow_color, rms, width=3)
        
        # Zentrale Spule/Core
        core_radius = int(30 + rms * 40)
        core_color = primary_color
        
        # Pulsierender Kern
        draw.ellipse([self.center[0] - core_radius, self.center[1] - core_radius,
                      self.center[0] + core_radius, self.center[1] + core_radius],
                     fill=core_color)
        
        # Innerer Glow
        inner_glow_radius = core_radius // 2
        inner_glow_color = tuple(min(255, c + 100) for c in core_color)
        draw.ellipse([self.center[0] - inner_glow_radius, self.center[1] - inner_glow_radius,
                      self.center[0] + inner_glow_radius, self.center[1] + inner_glow_radius],
                     fill=inner_glow_color)
        
        # Partikel-Strahlen bei Beats
        if onset > 0.4:
            self._draw_particle_rays(draw, self.center, self.max_radius, 
                                    primary_color, onset, rms, time)
        
        # Frequenz-Balken als äußerer Ring (simuliert)
        self._draw_frequency_ring(draw, self.center, self.max_radius + 20, 
                                 chroma, time, rms)
        
        return np.array(img)
    
    def _draw_wavy_ring(self, draw: ImageDraw.Draw, center: tuple, radius: float,
                        amplitude: float, wave_count: int, phase: float, 
                        color: tuple, rms: float, width: int = 2):
        """Zeichnet einen wellenförmigen Ring."""
        points = []
        num_points = 100
        
        for i in range(num_points + 1):
            angle = (i / num_points) * 2 * math.pi
            
            # Welle berechnen
            wave = np.sin(angle * wave_count + phase) * amplitude
            
            # Zusätzliche harmonische Wellen für Komplexität
            wave += np.sin(angle * wave_count * 2 + phase * 1.5) * amplitude * 0.3
            
            current_radius = radius + wave
            
            x = center[0] + math.cos(angle) * current_radius
            y = center[1] + math.sin(angle) * current_radius
            points.append((x, y))
        
        # Zeichne als verbundene Linien
        line_width = max(1, int(width + rms * 3))
        for i in range(len(points) - 1):
            draw.line([points[i], points[i + 1]], fill=color, width=line_width)
    
    def _draw_particle_rays(self, draw: ImageDraw.Draw, center: tuple, max_radius: float,
                           color: tuple, onset: float, rms: float, time: float):
        """Zeichnet Strahlen von der Mitte aus bei Beats."""
        num_rays = 12
        ray_length = max_radius * (0.3 + onset * 0.5)
        
        for i in range(num_rays):
            angle = (i / num_rays) * 2 * math.pi + time * 0.5
            
            # Start am Kern
            start_x = center[0] + math.cos(angle) * (30 + rms * 40)
            start_y = center[1] + math.sin(angle) * (30 + rms * 40)
            
            # Ende der Strahlen
            end_x = center[0] + math.cos(angle) * (max_radius + ray_length)
            end_y = center[1] + math.sin(angle) * (max_radius + ray_length)
            
            # Strahlen zeichnen mit abnehmender Dicke
            for j in range(3):
                offset_angle = j * 0.02
                ox = center[0] + math.cos(angle + offset_angle) * (max_radius + ray_length * 0.8)
                oy = center[1] + math.sin(angle + offset_angle) * (max_radius + ray_length * 0.8)
                
                ray_color = tuple(int(c * (1 - j * 0.3)) for c in color)
                draw.line([(start_x, start_y), (ox, oy)], fill=ray_color, 
                         width=max(1, int(4 - j + onset * 3)))
    
    def _draw_frequency_ring(self, draw: ImageDraw.Draw, center: tuple, radius: float,
                            chroma: np.ndarray, time: float, rms: float):
        """Zeichnet einen Ring mit Balken für jeden Chroma-Wert."""
        num_bars = 12
        bar_width = 15
        max_bar_height = 40
        
        for i in range(num_bars):
            angle = (i / num_bars) * 2 * math.pi - math.pi / 2
            
            # Höhe basierend auf Chroma-Stärke
            bar_height = max_bar_height * chroma[i] * (0.5 + rms)
            
            # Position des Balkens
            bar_x = center[0] + math.cos(angle) * radius
            bar_y = center[1] + math.sin(angle) * radius
            
            # Farbe basierend auf Ton
            hue = i / 12.0
            rgb = colorsys.hsv_to_rgb(hue, 0.9, 0.8 + chroma[i] * 0.2)
            bar_color = tuple(int(c * 255) for c in rgb)
            
            # Balken zeichnen (Rechteck)
            bar_end_x = center[0] + math.cos(angle) * (radius + bar_height)
            bar_end_y = center[1] + math.sin(angle) * (radius + bar_height)
            
            draw.line([(bar_x, bar_y), (bar_end_x, bar_end_y)], 
                     fill=bar_color, width=bar_width)
