"""Tests for cartographer.cli."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


def _make_png(tmp_path: Path) -> Path:
    from PIL import Image

    img = Image.fromarray(np.zeros((64, 64, 3), dtype=np.uint8))
    p = tmp_path / "shot.png"
    img.save(p)
    return p


def test_cli_ingest_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from cartographer.cli import main

    screenshot = _make_png(tmp_path)
    out = tmp_path / "out.json"
    monkeypatch.setattr(sys, "argv", ["cartographer", "ingest", "--in", str(screenshot), "--out", str(out)])
    main()
    assert out.exists()
