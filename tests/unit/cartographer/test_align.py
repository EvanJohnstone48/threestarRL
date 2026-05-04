"""Tests for cartographer.align."""

from __future__ import annotations


def test_run_snaps_detection_to_tile() -> None:
    from cartographer.align import AlignedPlacement, run
    from cartographer.detect import Detection

    det = Detection(class_name="town_hall", bbox_xyxy=(140.0, 100.0, 220.0, 180.0), confidence=0.9)
    placements = run([det], pitch=64.0, origin=(100.0, 100.0))
    assert len(placements) == 1
    p = placements[0]
    assert isinstance(p, AlignedPlacement)
    assert p.class_name == "town_hall"
    assert p.confidence == 0.9
    assert isinstance(p.origin, tuple)
    assert len(p.origin) == 2


def test_run_empty_detections() -> None:
    from cartographer.align import run

    assert run([], pitch=64.0, origin=(0.0, 0.0)) == []
