"""Tests for cartographer.detect — includes AC-C8 class-name parity."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def test_run_returns_detection() -> None:
    from cartographer.detect import Detection, run

    image = np.zeros((100, 100, 3), dtype=np.uint8)
    result = run(image)
    assert len(result) == 1
    assert isinstance(result[0], Detection)
    assert result[0].class_name == "town_hall"
    assert result[0].confidence == 1.0


def test_detection_bbox_at_centre() -> None:
    from cartographer.detect import run

    image = np.zeros((200, 300, 3), dtype=np.uint8)
    det = run(image)[0]
    x1, y1, x2, y2 = det.bbox_xyxy
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    assert abs(cx - 150) < 1
    assert abs(cy - 100) < 1


def test_roboflow_class_enum_parity() -> None:
    """AC-C8: RoboflowClass values must equal buildings.json names minus 'wall'."""
    from cartographer.detect import RoboflowClass

    buildings_path = Path(__file__).parents[3] / "app" / "data" / "buildings.json"
    data = json.loads(buildings_path.read_text(encoding="utf-8"))
    expected = {entry["name"] for entry in data["entries"]} - {"wall"}
    actual = {c.value for c in RoboflowClass}
    assert actual == expected
