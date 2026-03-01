"""
06_neon_oscilloscope.py - Retro-Futuristischer Neon Oscilloscope Visualizer

Inspiriert von Cyberpunk-Ästhetik und klassischen Oszilloskopen.
Zeichnet Waveform-Daten mit leuchtenden Neon-Effekten und Glow.
"""

import numpy as np
import colorsys
from PIL import Image, ImageDraw
from .base import BaseVisualizer
from .registry import register_visualizer


@register_visualizer("neon_oscilloscope")
class NeonOscilloscopeVisualizer(BaseVisualizer):
    """
    Retro-futuristischer Oscilloscope mit Neon-Effekten.
    Reagiert auf RMS (Amplitude) und zeichnet Wellenformen.
    Ideal für Synthwave, Cyberpunk, elektronische Musik.
    """

    def setup(self):
        """Initialisiere Oscilloscope-Parameter."""
        self.waveform_history = []  # Speichere vergangene Waveforms für Trail-Effekt
        self.max_history = 8
        self.center_y = self.height // 2

    def render_frame(self, frame_idx: int) -> np.ndarray:
        # Features holen
        f = self.get_feature_at_frame(frame_idx)
        rms = f["rms"]
        onset = f["onset"]
        spectral = f["spectral_centroid"]
        chroma = f["chroma"]

        # Hintergrund (tiefes Schwarz mit leichtem Blau-Stich)
        bg_color = self.colors.get("background", (5, 5, 15, 255))
        img = Image.new("RGB", (self.width, self.height), bg_color[:3])
        draw = ImageDraw.Draw(img)

        # Farben bestimmen basierend auf dominantem Chroma
        dominant_note = np.argmax(chroma)
        base_hue = dominant_note / 12.0

        # Neon-Farben berechnen
        neon_rgb = colorsys.hsv_to_rgb(base_hue, 0.9, 1.0)
        neon_color = tuple(int(c * 255) for c in neon_rgb)
        secondary_hue = (base_hue + 0.5) % 1.0
        secondary_rgb = colorsys.hsv_to_rgb(secondary_hue, 0.8, 1.0)
        secondary_color = tuple(int(c * 255) for c in secondary_rgb)

        # Fallback auf Config-Farben
        if "primary" in self.colors:
            neon_color = self.colors["primary"][:3]
        if "secondary" in self.colors:
            secondary_color = self.colors["secondary"][:3]

        # Grid zeichnen (wie ein Oszilloskop)
        grid_color = (20, 20, 40)
        grid_spacing = 50
        for x in range(0, self.width, grid_spacing):
            draw.line([(x, 0), (x, self.height)], fill=grid_color, width=1)
        for y in range(0, self.height, grid_spacing):
            draw.line([(0, y), (self.width, y)], fill=grid_color, width=1)

        # Aktuelle Wellenform generieren (simuliert aus Features)
        waveform = self._generate_waveform(frame_idx, rms, spectral)

        # History aktualisieren
        self.waveform_history.append(waveform)
        if len(self.waveform_history) > self.max_history:
            self.waveform_history.pop(0)

        # Trail-Effekt zeichnen (ältere Wellenformen mit abnehmender Opazität)
        for i, hist_wave in enumerate(self.waveform_history):
            alpha_factor = (i + 1) / len(self.waveform_history)
            trail_color = tuple(int(c * alpha_factor * 0.5) for c in secondary_color)
            self._draw_waveform(draw, hist_wave, trail_color, width=2)

        # Haupt-Wellenform zeichnen (helle Neon-Linie)
        self._draw_waveform(draw, waveform, neon_color, width=4)

        # Glow-Effekt hinzufügen (mehrere Linien mit abnehmender Intensität)
        for glow_offset in [6, 10, 14]:
            glow_intensity = 1.0 - (glow_offset / 20)
            glow_color = tuple(int(c * glow_intensity * 0.3) for c in neon_color)
            self._draw_waveform(
                draw, waveform, glow_color, width=glow_offset, offset=glow_offset // 4
            )

        # Beat-Indikator (Blitz auf dem Bildschirm bei starkem Beat)
        if onset > 0.5:
            flash_intensity = int((onset - 0.5) * 40)
            overlay = Image.new("RGB", (self.width, self.height), (0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle(
                [0, 0, self.width, self.height],
                fill=(neon_color[0] // 8, neon_color[1] // 8, neon_color[2] // 8),
            )
            img = Image.blend(img, overlay, 0.3)
            draw = ImageDraw.Draw(img)

        # Rahmen wie ein altes Oszilloskop
        border_color = tuple(max(0, c - 50) for c in neon_color)
        draw.rectangle(
            [2, 2, self.width - 3, self.height - 3], outline=border_color, width=2
        )

        # UI-Elemente (Scan-Linie)
        scan_x = int((frame_idx % self.width))
        draw.line(
            [(scan_x, 0), (scan_x, self.height)],
            fill=(neon_color[0] // 4, neon_color[1] // 4, neon_color[2] // 4),
            width=2,
        )

        return np.array(img)

    def _generate_waveform(self, frame_idx: float, rms: float, spectral: float) -> list:
        """Generiert eine simulierte Wellenform basierend auf Audio-Features."""
        points = []
        num_points = 200

        for i in range(num_points):
            x = (i / num_points) * self.width

            # Kombiniere mehrere Sinus-Wellen für organischen Look
            phase = frame_idx * 0.1
            freq1 = 0.02 * (1 + spectral)
            freq2 = 0.05 * (1 + rms)

            wave1 = np.sin(i * freq1 + phase) * rms * self.height * 0.25
            wave2 = np.sin(i * freq2 + phase * 1.5) * rms * self.height * 0.15
            wave3 = np.sin(i * 0.01 + phase * 0.5) * spectral * self.height * 0.1

            y = self.center_y + wave1 + wave2 + wave3
            y = np.clip(y, 50, self.height - 50)
            points.append((x, y))

        return points

    def _draw_waveform(
        self,
        draw: ImageDraw.Draw,
        points: list,
        color: tuple,
        width: int = 2,
        offset: int = 0,
    ):
        """Zeichnet die Wellenform als verbundene Linien."""
        if len(points) < 2:
            return

        # Zeichne Linien zwischen Punkten
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]

            # Offset anwenden (für Glow-Effekt)
            if offset > 0:
                y1 += offset
                y2 += offset

            draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
