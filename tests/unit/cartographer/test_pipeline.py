"""Tests for cartographer.pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest


def _make_png(tmp_path: Path, w: int = 64, h: int = 64) -> Path:
    from PIL import Image

    img = Image.fromarray(np.zeros((h, w, 3), dtype=np.uint8))
    p = tmp_path / "screenshot.png"
    img.save(p)
    return p


def test_run_produces_json_and_diag_png(tmp_path: Path) -> None:
    from cartographer.pipeline import run
    from sandbox_core.schemas import BaseLayout

    screenshot = _make_png(tmp_path)
    out = tmp_path / "out.json"
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
    run(screenshot, out)

    data = json.loads(out.read_text())
    layout = BaseLayout.model_validate(data)
    assert layout.schema_version == 3
    assert layout.provenance is not None
