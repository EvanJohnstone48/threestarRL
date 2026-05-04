"""Stage 3: derive isometric grid parameters (pitch, origin) from the image."""

from __future__ import annotations

import numpy as np


def run(image: np.ndarray) -> tuple[float, tuple[float, float]]:
    """Stub: returns a fixed pitch and origin.

    Returns (pitch_px, (origin_x, origin_y)).
    """
    _ = image  # production: analyse grass checker pattern
    return 64.0, (100.0, 100.0)
