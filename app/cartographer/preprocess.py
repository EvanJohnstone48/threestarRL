"""Stage 1: image load and colour-space conversion."""

from __future__ import annotations

from pathlib import Path

import numpy as np


def load(path: Path) -> np.ndarray:
    """Load *path* as an HxWx3 uint8 RGB array."""
    from PIL import Image

    img = Image.open(path).convert("RGB")
    return np.array(img, dtype=np.uint8)
