"""
3D WebGL Visualizer mit Three.js

Erstellt interaktive 3D-Visualisierungen im Browser.
Exportiert als eigenständige HTML-Datei.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import numpy as np

from ..types import AudioFeatures
from ..logger import get_logger
from .base import BaseVisualizer
from .registry import register_visualizer

logger = get_logger("audio_visualizer.webgl_3d")


@dataclass
class WebGLConfig:
    """Konfiguration für WebGL-Export."""

    width: int = 1920
    height: int = 1080
    fps: int = 60

    # 3D-Szene
    camera_fov: float = 75
    camera_position: List[float] = None
    background_color: str = "#0a0a0f"

    # Partikel
    particle_count: int = 5000
    particle_size: float = 2.0
    particle_color: str = "#00ccff"

    def __post_init__(self):
        if self.camera_position is None:
            self.camera_position = [0, 0, 50]


class WebGL3DRenderer:
    """
    Renderer für 3D-WebGL-Visualisierungen.

    Erstellt eine vollständige HTML-Datei mit Three.js,
    die Audio-Daten als 3D-Partikel visualisiert.
    """

    # Three.js Template
    HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            background: {bg_color};
            overflow: hidden;
            font-family: 'Segoe UI', sans-serif;
        }}
        #canvas-container {{
            width: 100vw;
            height: 100vh;
        }}
        #info {{
            position: absolute;
            top: 20px;
            left: 20px;
            color: rgba(255,255,255,0.8);
            pointer-events: none;
            z-index: 100;
        }}
        #controls {{
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 10px;
            z-index: 100;
        }}
        button {{
            padding: 10px 20px;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            color: white;
            cursor: pointer;
            border-radius: 4px;
            transition: all 0.3s;
        }}
        button:hover {{
            background: rgba(255,255,255,0.2);
        }}
        #loading {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: white;
            font-size: 1.5em;
        }}
    </style>
</head>
<body>
    <div id="info">
        <h2>{title}</h2>
        <p>FPS: <span id="fps">0</span></p>
        <p>Frame: <span id="frame">0</span> / <span id="total">{total_frames}</span></p>
    </div>
    
    <div id="loading">Loading...</div>
    <div id="canvas-container"></div>
    
    <div id="controls">
        <button id="playBtn">▶️ Play</button>
        <button id="pauseBtn">⏸️ Pause</button>
        <button id="fullscreenBtn">⛶ Fullscreen</button>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script>
        // Audio-Daten
        const audioData = {audio_data};
        
        // Konfiguration
        const config = {config};
        
        // Three.js Setup
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(config.background_color);
        
        const camera = new THREE.PerspectiveCamera(
            config.camera_fov,
            window.innerWidth / window.innerHeight,
            0.1,
            1000
        );
        camera.position.set(...config.camera_position);
        
        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        document.getElementById('canvas-container').appendChild(renderer.domElement);
        
        // Beleuchtung
        const ambientLight = new THREE.AmbientLight(0x404040, 2);
        scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight.position.set(10, 10, 10);
        scene.add(directionalLight);
        
        const pointLight = new THREE.PointLight(config.particle_color, 1, 100);
        pointLight.position.set(0, 0, 0);
        scene.add(pointLight);
        
        // Partikel-System
        const particleCount = config.particle_count;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        const colors = new Float32Array(particleCount * 3);
        const sizes = new Float32Array(particleCount);
        
        const color1 = new THREE.Color(config.particle_color);
        const color2 = new THREE.Color(config.secondary_color || '#ff0055');
        
        for (let i = 0; i < particleCount; i++) {{
            positions[i * 3] = (Math.random() - 0.5) * 100;
            positions[i * 3 + 1] = (Math.random() - 0.5) * 100;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 100;
            
            const mixedColor = color1.clone().lerp(color2, Math.random());
            colors[i * 3] = mixedColor.r;
            colors[i * 3 + 1] = mixedColor.g;
            colors[i * 3 + 2] = mixedColor.b;
            
            sizes[i] = Math.random() * config.particle_size;
        }}
        
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
        
        const material = new THREE.PointsMaterial({{
            size: config.particle_size,
            vertexColors: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
            transparent: true,
            opacity: 0.8
        }});
        
        const particles = new THREE.Points(geometry, material);
        scene.add(particles);
        
        // Zusätzliche Geometrien basierend auf Visualizer-Typ
        {additional_geometry}
        
        // Animation
        let currentFrame = 0;
        let isPlaying = true;
        let lastTime = 0;
        const fpsInterval = 1000 / config.fps;
        
        function animate(currentTime) {{
            requestAnimationFrame(animate);
            
            if (!isPlaying) return;
            
            const elapsed = currentTime - lastTime;
            if (elapsed < fpsInterval) return;
            lastTime = currentTime - (elapsed % fpsInterval);
            
            // Audio-Daten für aktuellen Frame
            if (currentFrame < audioData.rms.length) {{
                const rms = audioData.rms[currentFrame];
                const onset = audioData.onset[currentFrame];
                const centroid = audioData.spectral_centroid[currentFrame];
                
                // Partikel-Animation
                const positions = particles.geometry.attributes.position.array;
                
                for (let i = 0; i < particleCount; i++) {{
                    const idx = i * 3;
                    const audioFactor = rms * 20 + onset * 30;
                    
                    // Wellen-Bewegung
                    const waveX = Math.sin(currentFrame * 0.05 + i * 0.01) * audioFactor;
                    const waveY = Math.cos(currentFrame * 0.03 + i * 0.02) * audioFactor;
                    const waveZ = Math.sin(currentFrame * 0.07 + i * 0.015) * audioFactor;
                    
                    positions[idx] += waveX * 0.01;
                    positions[idx + 1] += waveY * 0.01;
                    positions[idx + 2] += waveZ * 0.01;
                    
                    // Zurück zur Ursprungsposition
                    positions[idx] *= 0.98;
                    positions[idx + 1] *= 0.98;
                    positions[idx + 2] *= 0.98;
                }}
                
                particles.geometry.attributes.position.needsUpdate = true;
                
                // Kamera-Bewegung
                camera.position.x = Math.sin(currentFrame * 0.005) * 50;
                camera.position.z = Math.cos(currentFrame * 0.005) * 50;
                camera.lookAt(0, 0, 0);
                
                // Licht-Animation
                pointLight.intensity = 0.5 + rms * 2;
                
                currentFrame++;
                
                // Loop
                if (currentFrame >= audioData.rms.length) {{
                    currentFrame = 0;
                }}
                
                // Update Info
                document.getElementById('frame').textContent = currentFrame;
                document.getElementById('fps').textContent = Math.round(1000 / elapsed);
            }}
            
            renderer.render(scene, camera);
        }}
        
        // Controls
        document.getElementById('playBtn').addEventListener('click', () => {{
            isPlaying = true;
        }});
        
        document.getElementById('pauseBtn').addEventListener('click', () => {{
            isPlaying = false;
        }});
        
        document.getElementById('fullscreenBtn').addEventListener('click', () => {{
            if (!document.fullscreenElement) {{
                document.documentElement.requestFullscreen();
            }} else {{
                document.exitFullscreen();
            }}
        }});
        
        // Resize Handler
        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }});
        
        // Mouse Interaction
        let mouseX = 0;
        let mouseY = 0;
        
        document.addEventListener('mousemove', (e) => {{
            mouseX = (e.clientX / window.innerWidth) * 2 - 1;
            mouseY = -(e.clientY / window.innerHeight) * 2 + 1;
        }});
        
        // Start
        document.getElementById('loading').style.display = 'none';
        animate(0);
    </script>
</body>
</html>"""

    def __init__(self, config: WebGLConfig):
        self.config = config

    def export(
        self,
        audio_features: AudioFeatures,
        output_path: str,
        title: str = "3D Audio Visualizer",
    ) -> bool:
        """
        Exportiert Audio-Features als interaktive HTML-Datei.

        Args:
            audio_features: Audio-Features für Visualisierung
            output_path: Pfad zur Ausgabe-HTML
            title: Titel der Seite
        """
        try:
            # Konvertiere Audio-Daten für JS
            audio_data = self._prepare_audio_data(audio_features)

            # Erstelle Konfiguration
            config = {
                "width": self.config.width,
                "height": self.config.height,
                "fps": self.config.fps,
                "camera_fov": self.config.camera_fov,
                "camera_position": self.config.camera_position,
                "background_color": self.config.background_color,
                "particle_count": self.config.particle_count,
                "particle_size": self.config.particle_size,
                "particle_color": self.config.particle_color,
                "secondary_color": "#ff0055",
            }

            # Zusätzliche Geometrie (überschreibbar in Subklassen)
            additional_geometry = self._get_additional_geometry()

            # Generiere HTML
            html = self.HTML_TEMPLATE.format(
                title=title,
                total_frames=len(audio_features.rms),
                bg_color=self.config.background_color,
                audio_data=json.dumps(audio_data),
                config=json.dumps(config),
                additional_geometry=additional_geometry,
            )

            # Schreibe Datei
            output_path = Path(output_path)
            output_path.write_text(html, encoding="utf-8")

            logger.info(f"3D WebGL exportiert: {output_path}")
            return True

        except Exception as e:
            logger.error(f"WebGL Export fehlgeschlagen: {e}")
            return False

    def _prepare_audio_data(self, features: AudioFeatures) -> Dict:
        """Bereitet Audio-Daten für JavaScript vor."""
        # Downsample für bessere Performance
        target_frames = min(len(features.rms), 3000)  # Max 3000 Frames
        step = max(1, len(features.rms) // target_frames)

        return {
            "rms": features.rms[::step].tolist(),
            "onset": features.onset[::step].tolist(),
            "spectral_centroid": features.spectral_centroid[::step].tolist(),
            "chroma": (
                features.chroma[:, ::step].tolist()
                if hasattr(features.chroma, "tolist")
                else []
            ),
            "frame_count": target_frames,
        }

    def _get_additional_geometry(self) -> str:
        """Zusätzliche Three.js Geometrie (kann überschrieben werden)."""
        return "// Keine zusätzliche Geometrie"


@register_visualizer("webgl_particles_3d")
class WebGLParticles3DVisualizer(BaseVisualizer):
    """
    3D Partikel-Visualizer mit WebGL-Export.

    Rendert auch Preview-Frames (PIL-basiert) für die GUI.
    Exportiert finale Version als interaktive HTML.
    """

    def setup(self):
        """Setup für 3D-Visualisierung."""
        self.center_x = self.width // 2
        self.center_y = self.height // 2
        self.particles = self._init_particles()

        # WebGL Renderer für Export
        self.webgl_config = WebGLConfig(
            width=self.width,
            height=self.height,
            fps=self.config.fps,
            particle_count=min(2000, self.width * self.height // 1000),
            particle_size=max(2, self.width // 500),
        )
        self.webgl_renderer = WebGL3DRenderer(self.webgl_config)

    def _init_particles(self) -> List[Dict]:
        """Initialisiert Partikel für Preview."""
        import random

        particles = []
        num_particles = min(1000, self.width * self.height // 2000)

        for _ in range(num_particles):
            particles.append(
                {
                    "x": random.uniform(-1, 1),
                    "y": random.uniform(-1, 1),
                    "z": random.uniform(-1, 1),
                    "vx": 0,
                    "vy": 0,
                    "vz": 0,
                    "size": random.uniform(1, 3),
                    "color_phase": random.uniform(0, 1),
                }
            )

        return particles

    def render_frame(self, frame_idx: int) -> np.ndarray:
        """Rendert einen Preview-Frame (2D für GUI)."""
        from PIL import Image, ImageDraw

        # Audio-Daten
        f = self.get_feature_at_frame(frame_idx)
        rms = f["rms"]
        onset = f["onset"]
        chroma = f["chroma"]

        # Erstelle Bild
        img = Image.new("RGB", (self.width, self.height), (10, 10, 15))
        draw = ImageDraw.Draw(img)

        # Background gradient simulation
        for y in range(0, self.height, 4):
            alpha = int(20 + rms * 30)
            color = (alpha, alpha, alpha + 5)
            draw.line([(0, y), (self.width, y)], fill=color, width=2)

        # Partikel rendern (2D Projektion)
        center_x = self.center_x
        center_y = self.center_y
        scale = min(self.width, self.height) * 0.4

        # Audio-Reaktivität
        audio_factor = rms * 100 + onset * 200

        for p in self.particles:
            # 3D Rotation
            angle = frame_idx * 0.02 + audio_factor * 0.001

            # Rotiere um Y-Achse
            x = p["x"] * np.cos(angle) - p["z"] * np.sin(angle)
            z = p["x"] * np.sin(angle) + p["z"] * np.cos(angle)
            y = p["y"]

            # Rotiere um X-Achse
            y_rot = y * np.cos(angle * 0.5) - z * np.sin(angle * 0.5)
            z_rot = y * np.sin(angle * 0.5) + z * np.cos(angle * 0.5)

            # Perspektivische Projektion
            fov = 500
            distance = 2 + z_rot
            if distance > 0:
                proj_x = center_x + (x * fov / distance) * scale * 0.5
                proj_y = center_y + (y_rot * fov / distance) * scale * 0.5

                # Größe basierend auf Z und Audio
                size = p["size"] * (1 + rms * 2) * (fov / distance) * 0.01
                size = max(1, min(size, 20))

                # Farbe basierend auf Chroma
                hue = (p["color_phase"] + chroma.argmax() / 12) % 1
                r, g, b = self._hsv_to_rgb(hue, 0.8, 0.9)
                color = (int(r * 255), int(g * 255), int(b * 255))

                # Alpha basierend auf Distanz
                alpha = int(255 * (1 - (z_rot + 1) / 3))
                if alpha > 50:
                    # Zeichne Partikel
                    draw.ellipse(
                        [proj_x - size, proj_y - size, proj_x + size, proj_y + size],
                        fill=color,
                    )

        # Zentrales Licht/Glow
        glow_size = int(50 + rms * 100)
        for r in range(glow_size, 0, -5):
            alpha = int(30 * (1 - r / glow_size) * rms)
            color = (0, int(200 * rms), int(255 * rms))
            draw.ellipse(
                [center_x - r, center_y - r, center_x + r, center_y + r],
                outline=color,
                width=2,
            )

        return np.array(img)

    def _hsv_to_rgb(self, h: float, s: float, v: float) -> tuple:
        """Konvertiert HSV zu RGB."""
        import colorsys

        return colorsys.hsv_to_rgb(h, s, v)

    def export_webgl(
        self, output_path: str, title: str = "3D Audio Visualizer"
    ) -> bool:
        """Exportiert als interaktive WebGL-HTML."""
        return self.webgl_renderer.export(self.features, output_path, title)


# Zusätzliche 3D-Visualizer-Varianten
@register_visualizer("webgl_bars_3d")
class WebGLBars3DVisualizer(BaseVisualizer):
    """3D Balken-Equalizer mit WebGL-Export."""

    def setup(self):
        """Setup für 3D Balken."""
        self.num_bars = 64
        self.bar_width = self.width / (self.num_bars * 1.5)
        self.center_x = self.width // 2
        self.center_y = self.height // 2

    def render_frame(self, frame_idx: int) -> np.ndarray:
        """Rendert 3D Balken."""
        from PIL import Image, ImageDraw

        f = self.get_feature_at_frame(frame_idx)
        rms = f["rms"]
        onset = f["onset"]
        chroma = f["chroma"]

        img = Image.new("RGB", (self.width, self.height), (10, 10, 15))
        draw = ImageDraw.Draw(img)

        # 3D-Perspektive
        center_x = self.center_x
        base_y = self.height * 0.8

        for i in range(self.num_bars):
            # Frequenz-Band
            freq_idx = int((i / self.num_bars) * 12)
            height = chroma[freq_idx % 12] * self.height * 0.6 * (1 + rms)
            height *= 1 + onset * 2

            # 3D-Effekt mit Perspektive
            x = center_x + (i - self.num_bars / 2) * self.bar_width * 1.5

            # Tiefe basierend auf Position (3D-Effekt)
            depth = 1 - abs(i - self.num_bars / 2) / (self.num_bars / 2)
            depth = max(0.5, depth)

            # Farbe
            hue = (i / self.num_bars + frame_idx * 0.001) % 1
            r, g, b = self._hsv_to_rgb(hue, 0.8, 0.9)
            color = (int(r * 255), int(g * 255), int(b * 255))

            # Schatten für 3D-Effekt
            shadow_offset = 10 * depth
            shadow_color = (int(r * 100), int(g * 100), int(b * 100))

            # Zeichne Balken (mit 3D-Effekt)
            bar_top = base_y - height * depth

            # Seite/Tiefe
            draw.rectangle(
                [
                    x + shadow_offset,
                    bar_top + shadow_offset,
                    x + self.bar_width + shadow_offset,
                    base_y + shadow_offset,
                ],
                fill=shadow_color,
            )

            # Front
            draw.rectangle(
                [x, bar_top, x + self.bar_width, base_y],
                fill=color,
                outline=(255, 255, 255),
                width=1,
            )

            # Top (für 3D-Effekt)
            draw.polygon(
                [
                    (x, bar_top),
                    (x + self.bar_width, bar_top),
                    (x + self.bar_width + shadow_offset, bar_top + shadow_offset),
                    (x + shadow_offset, bar_top + shadow_offset),
                ],
                fill=(int(r * 200), int(g * 200), int(b * 200)),
            )

        return np.array(img)

    def _hsv_to_rgb(self, h: float, s: float, v: float) -> tuple:
        """Konvertiert HSV zu RGB."""
        import colorsys

        return colorsys.hsv_to_rgb(h, s, v)
