"""Tests for cartographer.diagnostic."""

from __future__ import annotations

from pathlib import Path

import numpy as np


def _make_placement(class_name: str = "cannon", origin=(1, 1)):
    from cartographer.align import AlignedPlacement

    return AlignedPlacement(class_name=class_name, origin=origin, footprint=(3, 3), confidence=0.9)


def _make_detection(class_name: str = "mortar", bbox=(10.0, 10.0, 40.0, 40.0), confidence: float = 0.3):
    from cartographer.detect import Detection

    return Detection(class_name=class_name, bbox_xyxy=bbox, confidence=confidence)


def test_render_creates_png(tmp_path: Path) -> None:
    from cartographer.diagnostic import render

    image = np.zeros((200, 200, 3), dtype=np.uint8)
    out = tmp_path / "diag.png"
    render(image, [_make_placement()], [], [], pitch=32.0, origin=(10.0, 10.0), out_path=out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_render_empty_placements(tmp_path: Path) -> None:
    from cartographer.diagnostic import render

    image = np.ones((50, 50, 3), dtype=np.uint8) * 128
    out = tmp_path / "empty.png"
    render(image, [], [], [], pitch=16.0, origin=(0.0, 0.0), out_path=out)
    assert out.exists()


def test_render_sub_threshold_detections(tmp_path: Path) -> None:
    from cartographer.diagnostic import render

    image = np.zeros((200, 200, 3), dtype=np.uint8)
    out = tmp_path / "sub.png"
    sub = [_make_detection()]
    render(image, [], [], sub, pitch=32.0, origin=(0.0, 0.0), out_path=out)
    assert out.exists()
    assert out.stat().st_size > 0
