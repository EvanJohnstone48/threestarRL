"""Tests for cartographer.preprocess."""

from __future__ import annotations

import numpy as np
import pytest
from pathlib import Path


def _make_png(tmp_path: Path, w: int = 16, h: int = 16) -> Path:
    from PIL import Image

    img = Image.fromarray(np.zeros((h, w, 3), dtype=np.uint8))
    p = tmp_path / "test.png"
    img.save(p)
    return p


def test_load_returns_ndarray(tmp_path: Path) -> None:
    from cartographer.preprocess import load

    path = _make_png(tmp_path)
    arr = load(path)
    assert isinstance(arr, np.ndarray)
    assert arr.shape == (16, 16, 3)
    assert arr.dtype == np.uint8
