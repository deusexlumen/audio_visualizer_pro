"""
01_pulsing_core.py - Pulsing Circle Visualizer

Dein originaler Kreis - aber als Plugin und mit Chroma-Color-Mapping.

KI-Agent: Dies ist das Template für neue Visualizer:
1. @register_visualizer("einzigartiger_name")
2. Erbe von BaseVisualizer
3. Implementiere setup() und render_frame()
"""

import numpy as np
import colorsys
from PIL import Image, ImageDraw
from .base import BaseVisualizer
from .registry import register_visualizer


@register_visualizer("pulsing_core")
class PulsingCoreVisualizer(BaseVisualizer):
    """
    Pulsierender Kreis mit Chroma-basiertem Farb-Mapping.
    Reagiert auf RMS (Lautstärke) und Onset (Beats).
    """

    def setup(self):
        """Precalculate statische Elemente."""
        self.center = (self.width // 2, self.height // 2)
        self.base_radius = min(self.width, self.height) // 6

    def render_frame(self, frame_idx: int) -> np.ndarray:
        # Schwarzer Hintergrund
        bg_color = self.colors.get("background", (10, 10, 10, 255))
        img = Image.new("RGB", (self.width, self.height), bg_color[:3])
        draw = ImageDraw.Draw(img)

        # Features holen
        f = self.get_feature_at_frame(frame_idx)
        rms = f["rms"]
        onset = f["onset"]
        chroma = f["chroma"]  # 12 Werte für jeden Halbton

        # --- Kreative Logik: Chroma-Color Mapping ---
        # Finde dominante Note
        dominant_note = np.argmax(chroma)
        hue = dominant_note / 12.0  # 0.0 - 1.0

        # Konvertiere HSV zu RGB für lebendige Farben
        rgb = colorsys.hsv_to_rgb(hue, 0.8, 1.0)
        main_color = tuple(int(c * 255) for c in rgb)
        secondary_color = tuple(int(c * 200) for c in rgb)

        # Fallback auf Config-Farben wenn vorhanden
        if "primary" in self.colors:
            main_color = self.colors["primary"][:3]
        if "secondary" in self.colors:
            secondary_color = self.colors["secondary"][:3]

        # --- Pulsing Circle ---
        # Radius basiert auf RMS (Lautstärke)
        pulse = 1.0 + (rms * 0.8)  # Max 80% Größenzuwachs
        radius = int(self.base_radius * pulse)

        # Glühen-Effekt (mehrere Kreise)
        for i in range(3):
            offset = i * 20
            alpha_factor = int(100 * (1 - i / 3) * rms)
            # Zeichne nur wenn sichtbar
            if alpha_factor > 10:
                draw.ellipse(
                    [
                        self.center[0] - radius - offset,
                        self.center[1] - radius - offset,
                        self.center[0] + radius + offset,
                        self.center[1] + radius + offset,
                    ],
                    outline=main_color,
                    width=max(1, 3 - i),
                )

        # Hauptkreis (gefüllt)
        draw.ellipse(
            [
                self.center[0] - radius,
                self.center[1] - radius,
                self.center[0] + radius,
                self.center[1] + radius,
            ],
            fill=main_color,
        )

        # --- Partikel-Ring (Onset-getrieben) ---
        if onset > 0.3:  # Beat erkannt
            ring_radius = int(self.base_radius * 1.8)
            arc_start = (frame_idx * 2) % 360
            arc_end = (arc_start + 60) % 360
            draw.arc(
                [
                    self.center[0] - ring_radius,
                    self.center[1] - ring_radius,
                    self.center[0] + ring_radius,
                    self.center[1] + ring_radius,
                ],
                start=arc_start,
                end=arc_end,
                fill=secondary_color,
                width=4,
            )

        # --- Spektrale Morphing-Spur ---
        # Zeichne "Schweif" basierend auf spectral_centroid
        trail_length = 20
        for i in range(trail_length):
            past_frame = max(0, frame_idx - i)
            past_idx = min(past_frame, len(self.features.spectral_centroid) - 1)
            spect = self.features.spectral_centroid[past_idx]

            x = self.center[0] + int((i - trail_length / 2) * 30)
            y = self.height - 100 - int(spect * 200)
            size = int(10 * (1 - i / trail_length))

            if size > 0:
                draw.ellipse([x - size, y - size, x + size, y + size], fill=main_color)

        # --- BPM-Anzeige (optional) ---
        bpm_text = f"{int(self.features.tempo)} BPM"
        try:
            draw.text((20, 20), bpm_text, fill=(255, 255, 255))
        except Exception:
            pass

        return np.array(img)
