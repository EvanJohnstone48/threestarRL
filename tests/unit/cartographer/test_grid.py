"""Tests for cartographer.grid."""

from __future__ import annotations

import numpy as np


def test_run_returns_pitch_and_origin() -> None:
    from cartographer.grid import run

    image = np.zeros((100, 100, 3), dtype=np.uint8)
    pitch, origin = run(image)
    assert isinstance(pitch, float)
    assert pitch > 0
    assert len(origin) == 2
    assert all(isinstance(v, float) for v in origin)
