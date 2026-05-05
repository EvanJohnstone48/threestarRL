"""Tests for cartographer.grid."""

from __future__ import annotations

import math

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_grass_checker(
    width: int,
    height: int,
    pitch: float,
    ox: float,
    oy: float,
    angle1: float,
    angle2: float,
    p1_color: tuple[int, int, int] = (100, 160, 60),
    p2_color: tuple[int, int, int] = (70, 120, 40),
) -> np.ndarray:
    """Synthesise an RGB iso checker raster filled with grass-green tones."""
    d1 = (math.cos(angle1), math.sin(angle1))
    d2 = (math.cos(angle2), math.sin(angle2))
    mat = np.array([[d1[0], d2[0]], [d1[1], d2[1]]])
    inv_mat = np.linalg.inv(mat)

    ys, xs = np.mgrid[0:height, 0:width]
    dx = (xs - ox) / pitch
    dy = (ys - oy) / pitch
    r = inv_mat[0, 0] * dx + inv_mat[0, 1] * dy
    c = inv_mat[1, 0] * dx + inv_mat[1, 1] * dy
    checker = (np.floor(r).astype(int) + np.floor(c).astype(int)) % 2

    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[checker == 0] = p1_color
    image[checker == 1] = p2_color
    return image


def _make_noniso_checker(
    width: int,
    height: int,
    pitch1: float,
    pitch2: float,
    ox: float,
    oy: float,
    angle1: float,
    angle2: float,
    p1_color: tuple[int, int, int] = (100, 160, 60),
    p2_color: tuple[int, int, int] = (70, 120, 40),
) -> np.ndarray:
    """Checker with deliberately different pitches along the two iso axes."""
    v1 = (math.cos(angle1) * pitch1, math.sin(angle1) * pitch1)
    v2 = (math.cos(angle2) * pitch2, math.sin(angle2) * pitch2)
    mat = np.array([[v1[0], v2[0]], [v1[1], v2[1]]])
    inv_mat = np.linalg.inv(mat)

    ys, xs = np.mgrid[0:height, 0:width]
    dx = xs - ox
    dy = ys - oy
    r = inv_mat[0, 0] * dx + inv_mat[0, 1] * dy
    c = inv_mat[1, 0] * dx + inv_mat[1, 1] * dy
    checker = (np.floor(r).astype(int) + np.floor(c).astype(int)) % 2

    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[checker == 0] = p1_color
    image[checker == 1] = p2_color
    return image


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_run_returns_pitch_and_origin() -> None:
    from cartographer.grid import run

    image = np.zeros((100, 100, 3), dtype=np.uint8)
    pitch, origin = run(image)
    assert isinstance(pitch, float)
    assert pitch > 0
    assert len(origin) == 2
    assert all(isinstance(v, float) for v in origin)


def test_synthetic_checker_recovers_pitch() -> None:
    """Algorithm recovers pitch from a synthetic iso checker within 2 px."""
    from cartographer.grid import ISO_ANGLE_1, ISO_ANGLE_2, run

    TRUE_PITCH = 40.0
    image = _make_grass_checker(500, 500, TRUE_PITCH, 50.0, 60.0, ISO_ANGLE_1, ISO_ANGLE_2)

    pitch, _ = run(image)

    assert abs(pitch - TRUE_PITCH) < 2.0, f"pitch {pitch:.2f} far from {TRUE_PITCH}"


def test_synthetic_checker_recovers_origin_within_half_tile() -> None:
    """Recovered origin lies on a valid grid point within ±0.5 tile."""
    from cartographer.grid import ISO_ANGLE_1, ISO_ANGLE_2, run

    TRUE_PITCH = 40.0
    TRUE_OX, TRUE_OY = 50.0, 60.0
    image = _make_grass_checker(500, 500, TRUE_PITCH, TRUE_OX, TRUE_OY, ISO_ANGLE_1, ISO_ANGLE_2)

    pitch, (ox, oy) = run(image)

    # Convert pixel diff to tile space; fractional parts must be < 0.5
    d1 = (math.cos(ISO_ANGLE_1), math.sin(ISO_ANGLE_1))
    d2 = (math.cos(ISO_ANGLE_2), math.sin(ISO_ANGLE_2))
    mat = np.array([[d1[0], d2[0]], [d1[1], d2[1]]])
    inv_mat = np.linalg.inv(mat)

    diff = np.array([ox - TRUE_OX, oy - TRUE_OY]) / pitch
    tile_diff = inv_mat @ diff
    for td in tile_diff:
        frac = td - round(td)
        assert abs(frac) < 0.5, f"tile offset {td:.3f} has fractional part {frac:.3f}"


def test_cross_validation_raises_for_noniso_checker() -> None:
    """Deliberately mismatched iso pitches → GridCrossValidationError."""
    from cartographer.grid import GridCrossValidationError, ISO_ANGLE_1, ISO_ANGLE_2, run

    # pitch1=40, pitch2=60 → 40% mismatch → well above 2% threshold
    image = _make_noniso_checker(
        500, 500,
        pitch1=40.0, pitch2=60.0,
        ox=50.0, oy=50.0,
        angle1=ISO_ANGLE_1,
        angle2=ISO_ANGLE_2,
    )

    with pytest.raises(GridCrossValidationError):
        run(image)
