"""
05_typographic.py - Text-basierte Visualisierung für Podcasts

Minimalistisches Design mit Wellenform und Text-Overlay.
Ideal für Sprach-Inhalte.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from .base import BaseVisualizer
from .registry import register_visualizer


@register_visualizer("typographic")
class TypographicVisualizer(BaseVisualizer):
    """
    Text-basierte Visualisierung für Podcasts und Sprach-Inhalte.
    Zeigt eine Wellenform und unterstützt Text-Overlay.
    """

    def setup(self):
        """Initialisiere Text- und Wellenform-Parameter."""
        self.waveform_height = int(self.height * 0.3)
        self.waveform_y = int(self.height * 0.5)
        self.bar_width = 3
        self.bar_spacing = 1

        # Versuche größere Fonts zu laden
        try:
            self.title_font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72
            )
            self.subtitle_font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36
            )
        except Exception:
            self.title_font = self.font
            self.subtitle_font = self.font

    def render_frame(self, frame_idx: int) -> np.ndarray:
        # Hintergrund (dunkelgrau/schwarz)
        bg_color = self.colors.get("background", (18, 18, 18, 255))
        img = Image.new("RGB", (self.width, self.height), bg_color[:3])
        draw = ImageDraw.Draw(img)

        # Features holen
        f = self.get_feature_at_frame(frame_idx)
        rms = f["rms"]
        onset = f["onset"]
        zcr = f["zero_crossing_rate"]

        # Farben
        primary = self.colors.get("primary", (0, 200, 255, 255))[:3]
        secondary = self.colors.get("secondary", (255, 100, 100, 255))[:3]

        # --- Wellenform-Zentrum ---
        num_bars = self.width // (self.bar_width + self.bar_spacing)

        for i in range(num_bars):
            # Simuliere Wellenform aus verschiedenen Features
            phase = (i / num_bars) * np.pi * 4
            time_offset = frame_idx * 0.2

            # Kombiniere RMS und ZCR für organische Wellenform
            wave = np.sin(phase + time_offset) * rms
            wave += np.sin(phase * 2.5 + time_offset * 1.3) * zcr * 0.5
            wave = np.clip(wave, -1, 1)

            bar_height = int(abs(wave) * self.waveform_height)

            # Farbverlauf basierend auf Position
            if i < num_bars // 2:
                ratio = i / (num_bars // 2)
                color = tuple(
                    int(primary[j] * ratio + secondary[j] * (1 - ratio))
                    for j in range(3)
                )
            else:
                ratio = (i - num_bars // 2) / (num_bars // 2)
                color = tuple(
                    int(secondary[j] * ratio + primary[j] * (1 - ratio))
                    for j in range(3)
                )

            # Zeichne Balken (symmetrisch um die Mitte)
            x = i * (self.bar_width + self.bar_spacing)

            # Obere Hälfte
            draw.rectangle(
                [x, self.waveform_y - bar_height, x + self.bar_width, self.waveform_y],
                fill=color,
            )

            # Untere Hälfte (gespiegelt)
            draw.rectangle(
                [x, self.waveform_y, x + self.bar_width, self.waveform_y + bar_height],
                fill=color,
            )

        # --- Mittellinie ---
        line_color = tuple(max(0, c - 100) for c in primary)
        draw.line(
            [(0, self.waveform_y), (self.width, self.waveform_y)],
            fill=line_color,
            width=2,
        )

        # --- Beat-Indikator (Kreis) ---
        if onset > 0.3:
            indicator_radius = int(20 + onset * 30)
            draw.ellipse(
                [
                    self.width // 2 - indicator_radius,
                    self.waveform_y - indicator_radius,
                    self.width // 2 + indicator_radius,
                    self.waveform_y + indicator_radius,
                ],
                outline=primary,
                width=3,
            )

        # --- Fortschrittsbalken ---
        progress = f["progress"]
        bar_y = self.height - 30
        bar_width = int(self.width * 0.6)
        bar_x = (self.width - bar_width) // 2

        # Hintergrund-Balken
        draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + 6], fill=(50, 50, 50))

        # Fortschritt
        progress_width = int(bar_width * progress)
        draw.rectangle([bar_x, bar_y, bar_x + progress_width, bar_y + 6], fill=primary)

        # --- Zeit-Anzeige ---
        current_time = int(progress * self.features.duration)
        total_time = int(self.features.duration)
        time_text = f"{current_time // 60:02d}:{current_time % 60:02d} / {total_time // 60:02d}:{total_time % 60:02d}"

        try:
            draw.text(
                (bar_x, bar_y - 30),
                time_text,
                fill=(200, 200, 200),
                font=self.subtitle_font,
            )
        except Exception:
            draw.text((bar_x, bar_y - 30), time_text, fill=(200, 200, 200))

        # --- Mode-Indikator (Musik vs Sprache) ---
        mode_text = f"Mode: {self.features.mode.upper()}"
        if self.features.key:
            mode_text += f" | Key: {self.features.key}"

        try:
            draw.text(
                (bar_x, 30), mode_text, fill=(150, 150, 150), font=self.subtitle_font
            )
        except Exception:
            draw.text((bar_x, 30), mode_text, fill=(150, 150, 150))

        return np.array(img)
