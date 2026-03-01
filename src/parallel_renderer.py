"""
Parallel Renderer für Audio Visualizer Pro.

Nutzt Multi-Processing für paralleles Frame-Rendering.
Beschleunigt das Rendering erheblich auf Multi-Core-Systemen.
"""

import numpy as np
from multiprocessing import cpu_count
from typing import Callable, Optional, List, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
import tempfile
from pathlib import Path

from .logger import get_logger

logger = get_logger("audio_visualizer.parallel")


def _render_frame_batch(args):
    """
    Hilfsfunktion für einen Batch von Frames (muss außerhalb der Klasse sein für Pickling).

    Args:
        args: Tuple von (visualizer_module, visualizer_class, config_dict, features_dict, frame_indices)
    """
    import importlib

    (
        visualizer_module,
        visualizer_class_name,
        config_dict,
        features_dict,
        frame_indices,
    ) = args

    # Importiere und erstelle Visualizer
    module = importlib.import_module(visualizer_module)
    visualizer_class = getattr(module, visualizer_class_name)

    # Erstelle Dummy-Config und Features (vereinfacht)
    # In der Praxis müssen wir diese serialisieren

    frames = []
    for frame_idx in frame_indices:
        # Hier würde das eigentliche Rendering passieren
        # Für jetzt: Platzhalter
        frames.append((frame_idx, None))

    return frames


class ParallelRenderer:
    """
    Paralleler Renderer für schnelleres Frame-Rendering.

    Nutzt ProcessPoolExecutor für Multi-Core-Rendering.
    Optimal für CPU-intensive Visualizer.
    """

    def __init__(self, num_workers: Optional[int] = None):
        """
        Args:
            num_workers: Anzahl der Worker-Prozesse (default: CPU-Kerne)
        """
        self.num_workers = num_workers or max(1, cpu_count() - 1)
        logger.debug(f"ParallelRenderer initialisiert mit {self.num_workers} Workern")

    def render_frames_parallel(
        self,
        render_func: Callable[[int], np.ndarray],
        frame_indices: List[int],
        chunk_size: int = 10,
    ) -> List[Tuple[int, np.ndarray]]:
        """
        Rendert Frames parallel.

        Args:
            render_func: Funktion die einen Frame rendert (frame_idx -> np.ndarray)
            frame_indices: Liste der zu rendernden Frame-Indizes
            chunk_size: Anzahl der Frames pro Batch

        Returns:
            Liste von (frame_idx, frame_data) Tupeln
        """
        if len(frame_indices) == 0:
            return []

        # Für wenige Frames: Direktes Rendering (Overhead vermeiden)
        if len(frame_indices) < chunk_size * 2 or self.num_workers == 1:
            logger.debug(f"Direktes Rendering für {len(frame_indices)} Frames")
            return [(idx, render_func(idx)) for idx in frame_indices]

        # Teile in Batches auf
        batches = [
            frame_indices[i : i + chunk_size]
            for i in range(0, len(frame_indices), chunk_size)
        ]

        logger.info(
            f"Paralleles Rendering: {len(frame_indices)} Frames in {len(batches)} Batches"
        )

        results = []
        completed = 0

        with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            # Starte alle Batches
            future_to_batch = {
                executor.submit(self._render_batch, render_func, batch): batch
                for batch in batches
            }

            # Sammle Ergebnisse
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    batch_results = future.result()
                    results.extend(batch_results)
                    completed += len(batch)

                    if completed % 50 == 0 and len(frame_indices) > 0:
                        progress = completed / len(frame_indices) * 100
                        logger.info(
                            f"Fortschritt: {progress:.1f}% ({completed}/{len(frame_indices)})"
                        )

                except Exception as e:
                    logger.error(f"Fehler in Batch {batch[0]}-{batch[-1]}: {e}")
                    raise

        # Sortiere nach Frame-Index
        results.sort(key=lambda x: x[0])

        return results

    def _render_batch(
        self, render_func: Callable[[int], np.ndarray], frame_indices: List[int]
    ) -> List[Tuple[int, np.ndarray]]:
        """Rendert einen Batch von Frames."""
        return [(idx, render_func(idx)) for idx in frame_indices]


class StreamingParallelRenderer(ParallelRenderer):
    """
    Paralleler Renderer mit Streaming-Ausgabe.

    Schreibt fertige Frames direkt in eine Datei, um Speicher zu sparen.
    """

    def render_to_file(
        self,
        render_func: Callable[[int], np.ndarray],
        frame_indices: List[int],
        output_path: Path,
        frame_shape: Tuple[int, int, int],
        chunk_size: int = 10,
    ):
        """
        Rendert parallel und schreibt direkt in eine Datei.

        Args:
            render_func: Frame-Render-Funktion
            frame_indices: Zu rendernde Frames
            output_path: Ausgabedatei (raw video)
            frame_shape: (H, W, C) für jeden Frame
            chunk_size: Batch-Größe
        """

        height, width, channels = frame_shape
        frame_size = height * width * channels

        # Temporäre Dateien für jeden Batch
        temp_files = []
        batch_map = {}  # batch_idx -> (start_frame, end_frame)

        batches = [
            frame_indices[i : i + chunk_size]
            for i in range(0, len(frame_indices), chunk_size)
        ]

        logger.info(
            f"Streaming-Rendering: {len(frame_indices)} Frames in {len(batches)} Batches"
        )

        with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            futures = {
                executor.submit(self._render_batch_to_temp, render_func, batch, i): i
                for i, batch in enumerate(batches)
            }

            for future in as_completed(futures):
                batch_idx = futures[future]
                try:
                    temp_path = future.result()
                    temp_files.append((batch_idx, temp_path))
                    logger.debug(f"Batch {batch_idx} fertig: {temp_path}")
                except Exception as e:
                    logger.error(f"Fehler in Batch {batch_idx}: {e}")
                    raise

        # Kombiniere alle Temp-Dateien in Reihenfolge
        temp_files.sort(key=lambda x: x[0])

        logger.info(f"Kombiniere {len(temp_files)} Batch-Dateien...")
        with open(output_path, "wb") as outfile:
            for _, temp_path in temp_files:
                with open(temp_path, "rb") as infile:
                    outfile.write(infile.read())
                Path(temp_path).unlink()  # Lösche Temp-Datei

        logger.info(f"Fertig: {output_path}")

    def _render_batch_to_temp(
        self,
        render_func: Callable[[int], np.ndarray],
        frame_indices: List[int],
        batch_idx: int,
    ) -> str:
        """Rendert Batch in temporäre Datei."""
        temp_file = tempfile.NamedTemporaryFile(
            suffix=f"_batch_{batch_idx}.raw", delete=False
        )
        temp_file.close()

        with open(temp_file.name, "wb") as f:
            for frame_idx in frame_indices:
                frame = render_func(frame_idx)
                f.write(frame.tobytes())

        return temp_file.name


def get_optimal_workers() -> int:
    """Gibt die optimale Anzahl an Workern zurück."""
    cpu_cores = cpu_count()

    # Reserviere einen Kern für FFmpeg/Main
    optimal = max(1, cpu_cores - 1)

    logger.debug(f"CPU-Kerne: {cpu_cores}, Optimale Worker: {optimal}")
    return optimal
