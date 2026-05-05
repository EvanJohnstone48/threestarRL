"""Tests for cartographer.pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import numpy as np


def _make_png(tmp_path: Path, w: int = 64, h: int = 64) -> Path:
    from PIL import Image

    img = Image.fromarray(np.zeros((h, w, 3), dtype=np.uint8))
    p = tmp_path / "screenshot.png"
    img.save(p)
    return p


def _stub_detect(image, *, project_name, dataset_version, confidence_threshold, api_key):
    from cartographer.detect import Detection

    h, w = image.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    half = 40.0
    accepted = [
        Detection(
            class_name="town_hall",
            bbox_xyxy=(cx - half, cy - half, cx + half, cy + half),
            confidence=1.0,
        )
    ]
    return accepted, []


def test_run_produces_json_and_diag_png(tmp_path: Path) -> None:
    from cartographer.pipeline import run
    from sandbox_core.schemas import BaseLayout

    screenshot = _make_png(tmp_path)
    out = tmp_path / "out.json"
    with patch("cartographer.detect.run", side_effect=_stub_detect):
        layout = run(screenshot, out)

    assert isinstance(layout, BaseLayout)
    assert out.exists()
    diag = out.with_name("out.diag.png")
    assert diag.exists()


def test_run_json_validates_against_v3_schema(tmp_path: Path) -> None:
    from cartographer.pipeline import run
    from sandbox_core.schemas import BaseLayout

    screenshot = _make_png(tmp_path)
    out = tmp_path / "result.json"
    with patch("cartographer.detect.run", side_effect=_stub_detect):
        run(screenshot, out)

    data = json.loads(out.read_text())
    layout = BaseLayout.model_validate(data)
    assert layout.schema_version == 3
    assert layout.provenance is not None
