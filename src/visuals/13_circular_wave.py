"""
13_circular_wave.py - Circular Wave Visualizer

Kreisförmige Wellenform, die sich um einen Mittelpunkt dreht.
Ideal für meditative und atmosphärische Musik.
"""

import numpy as np
import colorsys
from PIL import Image, ImageDraw
from .base import BaseVisualizer
from .registry import register_visualizer


@register_visualizer("circular_wave")
class CircularWaveVisualizer(BaseVisualizer):
    """
    Kreisförmige Wellenform-Visualisierung.

    Zeichnet eine rotierende Spirale, die auf Audio reagiert.
    Erzeugt hypnotische, meditative Effekte.
    """

    def setup(self):
        """Initialisiere kreisförmige Parameter."""
        self.center = (self.width // 2, self.height // 2)
        self.max_radius = min(self.width, self.height) // 2 - 50
        self.num_points = 180  # Punkte pro Kreis

    def render_frame(self, frame_idx: int) -> np.ndarray:
        # Features holen
        f = self.get_feature_at_frame(frame_idx)
        rms = f["rms"]
        onset = f["onset"]
        chroma = f["chroma"]
        progress = f["progress"]

        # Hintergrund (dunkel mit subtilem Gradient)
        bg_color = self.colors.get("background", (8, 8, 16, 255))
        img = Image.new("RGB", (self.width, self.height), bg_color[:3])
        draw = ImageDraw.Draw(img)

        # Dominante Farbe
        dominant_note = np.argmax(chroma)
        base_hue = dominant_note / 12.0

        # Rotation basierend auf Zeit
        rotation = frame_idx * 0.02 + progress * np.pi * 4

        # Mehrere konzentrische Wellen
        num_waves = 3

        for wave_idx in range(num_waves):
            wave_offset = wave_idx * (np.pi * 2 / num_waves)
            wave_phase = rotation + wave_offset

            # Radius für diese Welle
            base_radius = self.max_radius * (0.3 + wave_idx * 0.35)

            # Farbe für diese Welle
            hue = (base_hue + wave_idx * 0.1) % 1.0

            # Onset = Farbwechsel
            if onset > 0.3:
                hue = (hue + 0.5) % 1.0

            rgb = colorsys.hsv_to_rgb(hue, 0.8, 0.9)
            color = tuple(int(c * 255) for c in rgb)

            # Berechne Punkte für diese Welle
            points = []
            for i in range(self.num_points):
                angle = (i / self.num_points) * np.pi * 2 + wave_phase

                # Audio-Reaktivität
                freq_idx = int((i / self.num_points) * 12) % 12
                freq_mod = chroma[freq_idx]

                # Radius-Modulation
                r_mod = np.sin(angle * 4 + frame_idx * 0.05) * rms * 30
                r_mod += np.cos(angle * 8) * onset * 20
                r_mod += freq_mod * 15

                radius = base_radius + r_mod

                # Zu Kartesisch
                x = self.center[0] + np.cos(angle) * radius
                y = self.center[1] + np.sin(angle) * radius

                points.append((int(x), int(y)))

            # Zeichne geschlossene Kurve
            if len(points) > 2:
                # Dicke basierend auf RMS
                line_width = max(2, int(3 + rms * 4 - wave_idx))

                # Zeichne als Linie
                draw.line(points + [points[0]], fill=color, width=line_width)

                # Glow-Effekt für erste Welle
                if wave_idx == 0:
                    glow_color = tuple(min(255, c + 30) for c in color)
                    for offset in [2, 4]:
                        draw.line(
                            points + [points[0]],
                            fill=glow_color,
                            width=line_width + offset,
                        )

        # Zentrale Partikel bei Onset
        if onset > 0.4:
            num_particles = int(20 * onset)
            for _ in range(num_particles):
                angle = np.random.random() * np.pi * 2
                dist = np.random.random() * 30 * onset
                px = self.center[0] + np.cos(angle) * dist
                py = self.center[1] + np.sin(angle) * dist
                size = int(2 + np.random.random() * 3)

                hue = (base_hue + np.random.random() * 0.2) % 1.0
                rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                color = tuple(int(c * 255) for c in rgb)

                draw.ellipse([px - size, py - size, px + size, py + size], fill=color)

        # Zentrum-Punkt
        center_size = int(5 + rms * 10)
        draw.ellipse(
            [
                self.center[0] - center_size,
                self.center[1] - center_size,
                self.center[0] + center_size,
                self.center[1] + center_size,
            ],
            fill=(255, 255, 255),
        )

        return np.array(img)
