"""Tests for grid geometry and footprint helpers."""

from __future__ import annotations

import math

from sandbox_core.grid import (
    BUILDABLE_MAX,
    BUILDABLE_MIN,
    GRID_SIZE,
    default_hitbox_inset,
    distance_point_to_square_hitbox,
    footprint_in_buildable,
    footprint_tiles,
    in_buildable_region,
    in_deploy_ring,
    in_grid,
    overlap,
)


def test_grid_constants() -> None:
    assert GRID_SIZE == 50
    assert BUILDABLE_MIN == 3
    assert BUILDABLE_MAX == 46


def test_in_buildable_region_boundary() -> None:
    assert in_buildable_region(3, 3)
    assert in_buildable_region(46, 46)
    assert not in_buildable_region(2, 5)
    assert not in_buildable_region(5, 47)


def test_in_deploy_ring_boundary() -> None:
    assert in_deploy_ring(0, 0)
    assert in_deploy_ring(2, 25)
    assert in_deploy_ring(47, 25)
    assert not in_deploy_ring(3, 25)
    assert not in_deploy_ring(46, 46)


def test_in_grid_bounds() -> None:
    assert in_grid(0, 0)
    assert in_grid(49, 49)
    assert not in_grid(-1, 0)
    assert not in_grid(50, 0)


def test_footprint_tiles_4x4() -> None:
    tiles = list(footprint_tiles((10, 12), (4, 4)))
    assert len(tiles) == 16
    assert (10, 12) in tiles
    assert (13, 15) in tiles
    assert (14, 12) not in tiles


def test_footprint_in_buildable_pass_and_fail() -> None:
    assert footprint_in_buildable((3, 3), (4, 4))
    assert footprint_in_buildable((43, 43), (4, 4))
    assert not footprint_in_buildable((44, 44), (4, 4))  # spills past 46
    assert not footprint_in_buildable((2, 3), (3, 3))  # row 2 in deploy ring


def test_default_hitbox_inset_per_size() -> None:
    assert default_hitbox_inset((1, 1)) == 0.5
    assert default_hitbox_inset((2, 2)) == 0.5
    assert default_hitbox_inset((3, 3)) == 1.0
    assert default_hitbox_inset((4, 4)) == 1.5


def test_distance_to_3x3_hitbox() -> None:
    # 3x3 cannon at (10, 10), inset 1.0 → hitbox r∈[11,12], c∈[11,12].
    # From (5.0, 5.0) to closest hitbox point (11.0, 11.0): sqrt(36+36) = sqrt(72)
    d = distance_point_to_square_hitbox((5.0, 5.0), (10, 10), (3, 3), 1.0)
    assert math.isclose(d, math.sqrt(72), rel_tol=1e-9)


def test_distance_inside_hitbox_is_zero() -> None:
    d = distance_point_to_square_hitbox((11.5, 11.5), (10, 10), (3, 3), 1.0)
    assert d == 0.0


def test_overlap_detection() -> None:
    assert overlap((0, 0), (3, 3), (2, 2), (3, 3))
    assert not overlap((0, 0), (3, 3), (3, 0), (3, 3))  # flush, no shared tile
    assert not overlap((0, 0), (3, 3), (4, 0), (3, 3))
