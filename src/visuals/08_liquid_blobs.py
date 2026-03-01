"""
08_liquid_blobs.py - Liquid Blobs / MetaBalls Visualizer

Flüssige, organische Blob-Animation inspiriert von MetaBalls.
Blobs verschmelzen und trennen sich basierend auf Audio-Reaktivität.
"""

import numpy as np
import colorsys
from PIL import Image, ImageDraw
from .base import BaseVisualizer
from .registry import register_visualizer


@register_visualizer("liquid_blobs")
class LiquidBlobsVisualizer(BaseVisualizer):
    """
    Flüssige Blob-Visualisierung mit MetaBall-ähnlichen Effekten.
    Organische Formen, die auf Beats und Lautstärke reagieren.
    Ideal für flüssige, fließende Musik wie House, Techno, Ambient.
    """

    def setup(self):
        """Initialisiere Blob-System."""
        self.num_blobs = 6
        self.blobs = []

        # Initialisiere Blobs mit Position, Geschwindigkeit und Eigenschaften
        for i in range(self.num_blobs):
            blob = {
                "x": np.random.randint(self.width // 4, 3 * self.width // 4),
                "y": np.random.randint(self.height // 4, 3 * self.height // 4),
                "vx": np.random.uniform(-2, 2),
                "vy": np.random.uniform(-2, 2),
                "base_radius": 60 + np.random.randint(40),
                "hue": i / self.num_blobs,
                "phase": np.random.random() * np.pi * 2,
            }
            self.blobs.append(blob)

        self.grid_resolution = 40  # Niedrigere Auflösung für Performance

    def render_frame(self, frame_idx: int) -> np.ndarray:
        # Features holen
        f = self.get_feature_at_frame(frame_idx)
        rms = f["rms"]
        onset = f["onset"]
        chroma = f["chroma"]
        spectral = f["spectral_centroid"]

        # Dominante Farbe aus Chroma
        dominant_note = np.argmax(chroma)
        base_hue = dominant_note / 12.0

        # Hintergrund (dunkel)
        bg_color = self.colors.get("background", (8, 8, 20, 255))
        img = Image.new("RGB", (self.width, self.height), bg_color[:3])
        draw = ImageDraw.Draw(img)

        # Farbpalette
        primary_color = self.colors.get("primary", (100, 200, 255, 255))[:3]
        secondary_color = self.colors.get("secondary", (255, 100, 200, 255))[:3]

        # Aktualisiere Blob-Positionen
        time = frame_idx * 0.02

        for i, blob in enumerate(self.blobs):
            # Bewegung mit Lissajous-Kurven + Audio-Reaktivität
            blob["phase"] += 0.01 + (rms * 0.05)

            # Basis-Bewegung
            base_x = self.width / 2 + np.sin(time + i) * (self.width * 0.3)
            base_y = self.height / 2 + np.cos(time * 0.7 + i * 1.3) * (
                self.height * 0.25
            )

            # Audio-reaktive Störung
            noise_x = np.sin(time * 3 + i * 2) * rms * 100
            noise_y = np.cos(time * 2.5 + i * 1.5) * rms * 100

            blob["x"] = base_x + noise_x
            blob["y"] = base_y + noise_y

            # Radius pulsiert mit Audio
            blob["current_radius"] = blob["base_radius"] * (0.8 + rms * 0.6)

            # Farbe basierend auf Chroma und Position
            hue = (base_hue + i * 0.15) % 1.0
            sat = 0.7 + chroma[(dominant_note + i) % 12] * 0.3
            val = 0.6 + rms * 0.4
            rgb = colorsys.hsv_to_rgb(hue, sat, val)
            blob["color"] = tuple(int(c * 255) for c in rgb)

        # Zeichne Blobs als überlappende Kreise mit Alpha
        # Wir verwenden ein vereinfachtes MetaBall-ähnliches Rendering
        self._draw_metaballs(img, draw, bg_color[:3])

        # Beat-Effekt: Explosions-ähnliche Ringe
        if onset > 0.4:
            self._draw_beat_rings(draw, onset, base_hue, rms)

        # Highlights auf den Blobs
        for blob in self.blobs:
            self._draw_blob_highlight(draw, blob, rms)

        return np.array(img)

    def _draw_metaballs(self, img: Image.Image, draw: ImageDraw.Draw, bg_color: tuple):
        """
        Vereinfachtes MetaBall-Rendering.
        Verwendet überlappende Kreise mit verschiedenen Intensitäten.
        """
        # Für jeden Blob zeichnen wir mehrere konzentrische Kreise
        for blob in self.blobs:
            center_x = int(blob["x"])
            center_y = int(blob["y"])
            base_radius = int(blob["current_radius"])
            color = blob["color"]

            # Äußerer Glow (sehr transparent)
            for i in range(5):
                radius = base_radius + (5 - i) * 15
                alpha = int(30 * (1 - i / 5))
                glow_color = tuple(
                    min(255, c + alpha) if i == 0 else max(0, c - i * 30) for c in color
                )

                # Zeichne als gefüllten Kreis
                draw.ellipse(
                    [
                        center_x - radius,
                        center_y - radius,
                        center_x + radius,
                        center_y + radius,
                    ],
                    fill=glow_color,
                )

            # Haupt-Blob
            draw.ellipse(
                [
                    center_x - base_radius,
                    center_y - base_radius,
                    center_x + base_radius,
                    center_y + base_radius,
                ],
                fill=color,
            )

            # Innerer Highlight
            inner_radius = base_radius // 3
            highlight_color = tuple(min(255, c + 80) for c in color)
            inner_x = center_x - base_radius // 4
            inner_y = center_y - base_radius // 4
            draw.ellipse(
                [
                    inner_x - inner_radius,
                    inner_y - inner_radius,
                    inner_x + inner_radius,
                    inner_y + inner_radius,
                ],
                fill=highlight_color,
            )

        # Verbindungslinien zwischen nahen Blobs
        for i, blob1 in enumerate(self.blobs):
            for j, blob2 in enumerate(self.blobs[i + 1 :], i + 1):
                dist = np.sqrt(
                    (blob1["x"] - blob2["x"]) ** 2 + (blob1["y"] - blob2["y"]) ** 2
                )

                # Wenn Blobs nah beieinander sind, zeichne Verbindung
                threshold = blob1["current_radius"] + blob2["current_radius"]
                if dist < threshold * 1.2:
                    # Verbindungsstärke basierend auf Distanz
                    connection_strength = 1 - (dist / (threshold * 1.2))
                    line_width = int(connection_strength * 8)

                    # Farbe mischen
                    mixed_color = tuple(
                        int((blob1["color"][k] + blob2["color"][k]) / 2)
                        for k in range(3)
                    )

                    draw.line(
                        [(blob1["x"], blob1["y"]), (blob2["x"], blob2["y"])],
                        fill=mixed_color,
                        width=line_width,
                    )

    def _draw_beat_rings(
        self, draw: ImageDraw.Draw, onset: float, base_hue: float, rms: float
    ):
        """Zeichnet expandierende Ringe bei Beats."""
        center_x = self.width // 2
        center_y = self.height // 2

        num_rings = 3
        for i in range(num_rings):
            radius = int(100 + i * 80 + onset * 50)

            # Farbe für jeden Ring
            hue = (base_hue + i * 0.1) % 1.0
            rgb = colorsys.hsv_to_rgb(hue, 0.8, 1.0)
            color = tuple(int(c * 255) for c in rgb)

            # Alpha basierend auf Onset
            intensity = int(onset * 200 * (1 - i / num_rings))
            ring_color = tuple(min(255, c + intensity) for c in color)

            draw.ellipse(
                [
                    center_x - radius,
                    center_y - radius,
                    center_x + radius,
                    center_y + radius,
                ],
                outline=ring_color,
                width=max(1, int(onset * 5)),
            )

    def _draw_blob_highlight(self, draw: ImageDraw.Draw, blob: dict, rms: float):
        """Zeichnet einen Highlight-Glanz auf dem Blob."""
        # Position des Highlights (oben-links verschoben)
        offset = int(blob["current_radius"] * 0.3)
        highlight_x = int(blob["x"]) - offset
        highlight_y = int(blob["y"]) - offset
        highlight_size = int(blob["current_radius"] * 0.25)

        # Sehr heller Klecks
        highlight_color = (255, 255, 255)

        draw.ellipse(
            [
                highlight_x - highlight_size,
                highlight_y - highlight_size,
                highlight_x + highlight_size,
                highlight_y + highlight_size,
            ],
            fill=highlight_color,
        )
