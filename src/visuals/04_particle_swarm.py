"""
04_particle_swarm.py - Physik-basiertes Partikel-System

Partikel, die auf Beats explodieren und sich physikalisch korrekt bewegen.
"""

import numpy as np
import colorsys
from PIL import Image, ImageDraw
from .base import BaseVisualizer
from .registry import register_visualizer


@register_visualizer("particle_swarm")
class ParticleSwarmVisualizer(BaseVisualizer):
    """
    Physik-basiertes Partikel-System.
    Partikel explodieren bei Beats und schweben langsam zurück.
    """
    
    def setup(self):
        """Initialisiere Partikel-System mit Physik."""
        self.num_particles = 150
        self.center = (self.width // 2, self.height // 2)
        
        # Partikel-Array: [x, y, vx, vy, life, max_life, size, hue]
        self.particles_data = np.zeros((self.num_particles, 8))
        
        # Initialisiere alle Partikel
        for i in range(self.num_particles):
            self._reset_particle(i, random=True)
    
    def _reset_particle(self, idx, random=False, explode=False):
        """Setzt ein Partikel zurück oder explodiert es."""
        if random:
            # Zufällige Startposition
            angle = np.random.random() * np.pi * 2
            dist = np.random.random() * 100
            self.particles_data[idx, 0] = self.center[0] + np.cos(angle) * dist
            self.particles_data[idx, 1] = self.center[1] + np.sin(angle) * dist
            self.particles_data[idx, 2] = np.cos(angle) * np.random.random() * 2
            self.particles_data[idx, 3] = np.sin(angle) * np.random.random() * 2
        elif explode:
            # Explosion vom Zentrum
            angle = np.random.random() * np.pi * 2
            speed = 5 + np.random.random() * 10
            self.particles_data[idx, 0] = self.center[0]
            self.particles_data[idx, 1] = self.center[1]
            self.particles_data[idx, 2] = np.cos(angle) * speed
            self.particles_data[idx, 3] = np.sin(angle) * speed
        
        self.particles_data[idx, 4] = 1.0  # Leben (0-1)
        self.particles_data[idx, 5] = 0.5 + np.random.random() * 1.0  # Max-Leben
        self.particles_data[idx, 6] = 2 + np.random.random() * 6  # Größe
        self.particles_data[idx, 7] = np.random.random()  # Hue
    
    def render_frame(self, frame_idx: int) -> np.ndarray:
        # Hintergrund mit Trail-Effekt (dunkelblau/schwarz)
        bg_color = self.colors.get('background', (2, 2, 8, 255))
        img = Image.new('RGB', (self.width, self.height), bg_color[:3])
        draw = ImageDraw.Draw(img)
        
        # Features holen
        f = self.get_feature_at_frame(frame_idx)
        rms = f['rms']
        onset = f['onset']
        chroma = f['chroma']
        
        # Beat-Explosion
        if onset > 0.4:
            particles_to_explode = int(self.num_particles * onset * 0.3)
            for i in range(particles_to_explode):
                idx = np.random.randint(0, self.num_particles)
                self._reset_particle(idx, explode=True)
                # Farbe basierend auf Chroma
                dominant = np.argmax(chroma)
                self.particles_data[idx, 7] = dominant / 12.0
        
        # Aktualisiere und zeichne alle Partikel
        for i in range(self.num_particles):
            x, y = self.particles_data[i, 0], self.particles_data[i, 1]
            vx, vy = self.particles_data[i, 2], self.particles_data[i, 3]
            life = self.particles_data[i, 4]
            max_life = self.particles_data[i, 5]
            size = self.particles_data[i, 6]
            hue = self.particles_data[i, 7]
            
            # Physik-Update
            x += vx
            y += vy
            
            # Gravitation zum Zentrum
            dx = self.center[0] - x
            dy = self.center[1] - y
            dist = np.sqrt(dx**2 + dy**2) + 1
            
            # Anziehungskraft
            force = 0.05 * rms
            vx += (dx / dist) * force
            vy += (dy / dist) * force
            
            # Reibung
            vx *= 0.98
            vy *= 0.98
            
            # Leben verringern
            life -= 0.005 * (1.0 + rms)
            
            # Reset wenn tot
            if life <= 0:
                self._reset_particle(i, random=True)
                life = self.particles_data[i, 4]
            
            # Speichere aktualisierte Werte
            self.particles_data[i, 0] = x
            self.particles_data[i, 1] = y
            self.particles_data[i, 2] = vx
            self.particles_data[i, 3] = vy
            self.particles_data[i, 4] = life
            
            # Farbe basierend auf Leben und Hue
            life_ratio = life / max_life
            saturation = 0.7 + rms * 0.3
            value = life_ratio * (0.5 + rms * 0.5)
            
            rgb = colorsys.hsv_to_rgb(hue, saturation, value)
            color = tuple(int(c * 255) for c in rgb)
            
            # Fallback
            if 'primary' in self.colors:
                primary = self.colors['primary'][:3]
                color = tuple(int(primary[j] * 0.2 + color[j] * 0.8) for j in range(3))
            
            # Zeichne Partikel
            current_size = int(size * life_ratio * (0.8 + rms * 0.4))
            if current_size > 0:
                ix, iy = int(x), int(y)
                # Glühen
                glow = current_size + 2
                glow_color = tuple(max(0, c - 150) for c in color)
                draw.ellipse([ix-glow, iy-glow, ix+glow, iy+glow], fill=glow_color)
                # Kern
                draw.ellipse([ix-current_size, iy-current_size, 
                             ix+current_size, iy+current_size], fill=color)
        
        # Zentrumspuls
        pulse_radius = int(20 + rms * 30)
        center_color = (255, 255, 255) if 'primary' not in self.colors else self.colors['primary'][:3]
        draw.ellipse([self.center[0]-pulse_radius, self.center[1]-pulse_radius,
                     self.center[0]+pulse_radius, self.center[1]+pulse_radius],
                    outline=center_color, width=2)
        
        return np.array(img)
