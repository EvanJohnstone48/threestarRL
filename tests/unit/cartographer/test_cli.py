"""Tests for cartographer.cli."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest


def _make_png(tmp_path: Path) -> Path:
    from PIL import Image

    img = Image.fromarray(np.zeros((64, 64, 3), dtype=np.uint8))
    p = tmp_path / "shot.png"
    img.save(p)
    return p


def _stub_detect(image, *, project_name, dataset_version, confidence_threshold, api_key):
    from cartographer.detect import Detection

    h, w = image.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    half = 40.0
    return [
        Detection(
            class_name="town_hall",
            bbox_xyxy=(cx - half, cy - half, cx + half, cy + half),
            confidence=1.0,
        )
    ], []


def test_cli_ingest_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from cartographer.cli import main

    screenshot = _make_png(tmp_path)
    out = tmp_path / "out.json"
    monkeypatch.setattr(sys, "argv", ["cartographer", "ingest", "--in", str(screenshot), "--out", str(out)])
    with patch("cartographer.detect.run", side_effect=_stub_detect):
        main()
    assert out.exists()
