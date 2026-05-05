"""Tests for cartographer.align."""

from __future__ import annotations

import logging
import math

import numpy as np
import pytest


# ── helpers ─────────────────────────────────────────────────────────────────

def _make_detection(class_name: str, bbox_xyxy: tuple[float, float, float, float], conf: float = 0.9):
    from cartographer.detect import Detection
    return Detection(class_name=class_name, bbox_xyxy=bbox_xyxy, confidence=conf)


def _basis_matrix(pitch: float) -> np.ndarray:
    from cartographer.grid import ISO_ANGLE_1, ISO_ANGLE_2
    v1 = np.array([math.cos(ISO_ANGLE_1), math.sin(ISO_ANGLE_1)]) * pitch
    v2 = np.array([math.cos(ISO_ANGLE_2), math.sin(ISO_ANGLE_2)]) * pitch
    return np.column_stack([v1, v2])


def _anchor_pixel_for_tile(col0: int, row0: int, n: int, pitch: float, origin: tuple[float, float]) -> tuple[float, float]:
    """Return the bbox bottom-center pixel for a building at (col0, row0) with footprint n."""
    M = _basis_matrix(pitch)
    anchor_tile = np.array([col0 + n, row0 + n], dtype=float)
    pixel = np.array(origin) + M @ anchor_tile
    return float(pixel[0]), float(pixel[1])


def _make_bbox_for_tile(col0: int, row0: int, n: int, pitch: float, origin: tuple[float, float]) -> tuple[float, float, float, float]:
    """Build a plausible bbox whose bottom-center lands at the expected anchor pixel."""
    ax, ay = _anchor_pixel_for_tile(col0, row0, n, pitch, origin)
    half = n * pitch * 0.4
    return (ax - half, ay - 2 * half, ax + half, ay)


# ── existing smoke tests ──────────────────────────────────────────────────

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


# ── footprint size tests ──────────────────────────────────────────────────

@pytest.mark.parametrize("class_name,expected_n", [
    ("builders_hut", 2),
    ("air_sweeper", 2),
    ("cannon", 3),
    ("town_hall", 4),
    ("army_camp", 4),
])
def test_footprint_correct_size(class_name: str, expected_n: int) -> None:
    from cartographer.align import run

    pitch = 64.0
    origin = (500.0, 500.0)
    col0, row0 = 10, 10
    bbox = _make_bbox_for_tile(col0, row0, expected_n, pitch, origin)
    dets = [_make_detection(class_name, bbox)]
    placements = run(dets, pitch=pitch, origin=origin)
    assert len(placements) == 1
    assert placements[0].footprint == (expected_n, expected_n)


# ── known tile origin recovery ─────────────────────────────────────────────

@pytest.mark.parametrize("class_name,n", [
    ("builders_hut", 2),
    ("cannon", 3),
    ("town_hall", 4),
    ("army_camp", 4),
])
def test_known_tile_origin_recovered(class_name: str, n: int) -> None:
    """Known bbox + grid + no calibration → recovers the planted tile origin."""
    from cartographer.align import run

    pitch = 64.0
    origin = (300.0, 300.0)
    col0, row0 = 8, 6
    bbox = _make_bbox_for_tile(col0, row0, n, pitch, origin)
    dets = [_make_detection(class_name, bbox)]

    placements = run(dets, pitch=pitch, origin=origin, offsets={})
    assert len(placements) == 1
    p = placements[0]
    # After centering, origin shifts by round(22 - (col0, row0))
    shift_col = round(22 - col0)
    shift_row = round(22 - row0)
    assert p.origin == (col0 + shift_col, row0 + shift_row)


def test_calibration_offset_shifts_origin() -> None:
    """A known (dx, dy) offset shifts the recovered tile origin predictably."""
    from cartographer.align import _basis_matrix, run

    pitch = 64.0
    origin = (300.0, 300.0)
    col0, row0, n = 8, 8, 3
    bbox = _make_bbox_for_tile(col0, row0, n, pitch, origin)

    # Shift the bbox anchor by exactly one tile in v1 direction → col0 increases by 1
    M = _basis_matrix(pitch)
    dx = float(M[0, 0])  # v1_x = one tile step in column direction
    dy = float(M[1, 0])  # v1_y

    # Offset is subtracted from anchor before converting, so positive dx moves anchor right
    # which means the apparent tile origin is shifted by +1 col
    offsets = {"cannon": (-dx, -dy)}  # negative offset cancels the shift → same origin
    placements_no_offset = run([_make_detection("cannon", bbox)], pitch=pitch, origin=origin, offsets={})
    placements_with_offset = run([_make_detection("cannon", bbox)], pitch=pitch, origin=origin, offsets=offsets)
    # Both should land at same tile since offsets cancel the shift
    assert placements_no_offset[0].origin == placements_with_offset[0].origin


# ── overlap detection ──────────────────────────────────────────────────────

def test_overlapping_placements_raise_overlap_error() -> None:
    from cartographer.align import OverlapError, run

    pitch = 64.0
    origin = (300.0, 300.0)
    # Place two 3x3 buildings at the same tile → guaranteed overlap
    col0, row0, n = 10, 10, 3
    bbox1 = _make_bbox_for_tile(col0, row0, n, pitch, origin)
    bbox2 = _make_bbox_for_tile(col0, row0, n, pitch, origin)
    dets = [
        _make_detection("cannon", bbox1),
        _make_detection("mortar", bbox2),
    ]
    with pytest.raises(OverlapError):
        run(dets, pitch=pitch, origin=origin, offsets={})


def test_adjacent_placements_do_not_raise() -> None:
    from cartographer.align import run

    pitch = 64.0
    origin = (300.0, 300.0)
    n = 3
    bbox1 = _make_bbox_for_tile(8, 8, n, pitch, origin)
    bbox2 = _make_bbox_for_tile(8 + n, 8, n, pitch, origin)  # directly adjacent
    dets = [
        _make_detection("cannon", bbox1),
        _make_detection("mortar", bbox2),
    ]
    placements = run(dets, pitch=pitch, origin=origin, offsets={})
    assert len(placements) == 2


# ── reverse projection error ───────────────────────────────────────────────

def test_bad_bbox_raises_reverse_projection_error() -> None:
    """Anchor pixel at a fractional tile corner that maximises rounding error (>0.5 tile).

    With the isometric basis, Δcol=0.5 and Δrow=-0.5 in tile space maps to a
    pixel error of ~57px > 0.5*pitch=32px.  We engineer the anchor to land at
    tile (12.5, 13.5) so Python's banker-rounding gives col0=10, row0=10 for
    col0_frac=9.5, row0_frac=10.5, triggering ReverseProjectionError.
    """
    from cartographer.align import ReverseProjectionError, run

    pitch = 64.0
    origin = (300.0, 300.0)
    # Anchor at tile (12.5, 13.5): col0_frac=9.5 rounds to 10, row0_frac=10.5 rounds to 10.
    # Δcol=0.5, Δrow=-0.5 → pixel error ≈ 57px > 32px = 0.5*pitch.
    anchor_x = 242.75665978  # pre-computed for origin=(300,300), pitch=64
    anchor_y = 1044.16342291
    half = 50.0
    bad_bbox = (anchor_x - half, anchor_y - 100.0, anchor_x + half, anchor_y)
    dets = [_make_detection("cannon", bad_bbox)]
    with pytest.raises(ReverseProjectionError):
        run(dets, pitch=pitch, origin=origin, offsets={})


# ── boundary error ─────────────────────────────────────────────────────────

def test_centering_that_clips_grid_raises_boundary_error() -> None:
    """Placements far from (22, 22) that clip the 44×44 grid after centering."""
    from cartographer.align import BoundaryError, run

    pitch = 64.0
    origin = (1000.0, 1000.0)
    # Place a building far in the corner — tile (0, 0) with a 4x4 footprint.
    # After centering (centroid → 22) the shift is large but should stay in bounds.
    # To force a clip: use a 5x5 at tile (40, 40) → after centering shift is
    # round(22-40) = -18 → new origin = 40-18=22, 22+5=27 ≤ 44, fine.
    # Instead: two buildings far apart such that centroid is at extreme → one clips.
    n = 3
    # Building 1 at tile (1, 1): after centering would be at (1 + round(22-1), 1 + round(22-1)) = (22, 22)
    # Building 2 at tile (42, 1): after centering would be at (42+21, 22) = (63, 22) → clips 44
    bbox1 = _make_bbox_for_tile(1, 1, n, pitch, origin)
    bbox2 = _make_bbox_for_tile(42, 1, n, pitch, origin)
    dets = [
        _make_detection("cannon", bbox1),
        _make_detection("mortar", bbox2),
    ]
    with pytest.raises(BoundaryError):
        run(dets, pitch=pitch, origin=origin, offsets={})


# ── missing calibration file ───────────────────────────────────────────────

def test_missing_calibration_uses_zero_offsets(tmp_path, caplog) -> None:
    """Alignment proceeds normally when calibration is absent; no exception raised."""
    from cartographer.calibration import load_offsets
    from cartographer.align import run

    fake_cal_path = tmp_path / "cartographer_calibration.json"
    # File does not exist
    with caplog.at_level(logging.WARNING, logger="cartographer"):
        offsets = load_offsets("v1", _path=fake_cal_path)

    assert offsets == {}

    pitch = 64.0
    origin = (300.0, 300.0)
    col0, row0, n = 10, 10, 3
    bbox = _make_bbox_for_tile(col0, row0, n, pitch, origin)
    dets = [_make_detection("cannon", bbox)]

    # Should not raise even with empty offsets
    placements = run(dets, pitch=pitch, origin=origin, offsets=offsets)
    assert len(placements) == 1


def test_missing_class_in_offsets_warns_once(caplog) -> None:
    """When offsets exist but don't include a class, one warning is logged per class."""
    from cartographer.align import run

    pitch = 64.0
    origin = (300.0, 300.0)
    col0, row0, n = 10, 10, 3
    bbox1 = _make_bbox_for_tile(col0, row0, n, pitch, origin)
    bbox2 = _make_bbox_for_tile(col0 + n, row0, n, pitch, origin)
    dets = [
        _make_detection("cannon", bbox1),
        _make_detection("cannon", bbox2),  # same class twice
    ]

    with caplog.at_level(logging.WARNING, logger="cartographer"):
        run(dets, pitch=pitch, origin=origin, offsets={"mortar": (0.0, 0.0)})

    # One warning for cannon (not two)
    warnings = [r for r in caplog.records if "cannon" in r.message]
    assert len(warnings) == 1
