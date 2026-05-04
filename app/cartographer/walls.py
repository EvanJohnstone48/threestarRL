"""Stage 5: classify wall tiles by stone-vs-grass colour matching."""

from __future__ import annotations

import numpy as np


def run(
    image: np.ndarray,
    pitch: float,
    origin: tuple[float, float],
) -> list[tuple[int, int]]:
    """Stub: returns an empty wall list.

    Production: samples each candidate tile and compares to stone colour profile.
    """
    _ = image, pitch, origin
    return []
