"""Tests for cartographer.walls."""

from __future__ import annotations

import numpy as np


def _make_placement(col: int, row: int, n: int = 2, confidence: float = 1.0):
    from cartographer.align import AlignedPlacement

    return AlignedPlacement(
        class_name="cannon",
        origin=(col, row),
        footprint=(n, n),
        confidence=confidence,
    )


def _box_placements():
    """Four 2x2 placements forming corners of a box enclosing centre tiles."""
    return [
        _make_placement(5, 5),
        _make_placement(15, 5),
        _make_placement(5, 15),
        _make_placement(15, 15),
    ]


def test_empty_placements_returns_empty() -> None:
    from cartographer.walls import run

    image = np.zeros((100, 100, 3), dtype=np.uint8)
    assert run(image, 32.0, (0.0, 0.0), []) == []


def test_fewer_than_3_placements_returns_empty() -> None:
    from cartographer.walls import run

    image = np.zeros((100, 100, 3), dtype=np.uint8)
    placements = [_make_placement(5, 5), _make_placement(15, 5)]
    assert run(image, 16.0, (50.0, 50.0), placements) == []


def test_footprint_tiles_excluded() -> None:
    from cartographer.walls import STONE_COLOR_CENTROID, run

    r, g, b = STONE_COLOR_CENTROID
    image = np.full((300, 300, 3), [r, g, b], dtype=np.uint8)
    placements = _box_placements()

    occupied: set[tuple[int, int]] = set()
    for p in placements:
        c0, r0 = p.origin
        n = p.footprint[0]
        for dc in range(n):
            for dr in range(n):
                occupied.add((c0 + dc, r0 + dr))

    result = run(image, 16.0, (50.0, 50.0), placements)
    for tile in result:
        assert tile not in occupied, f"Footprint tile {tile} leaked into wall result"


def test_grass_tile_not_wall() -> None:
    from cartographer.walls import run

    # Clearly green — far from stone centroid
    image = np.full((300, 300, 3), [90, 160, 70], dtype=np.uint8)
    result = run(image, 16.0, (50.0, 50.0), _box_placements())
    assert result == []


def test_stone_tile_classified_as_wall() -> None:
    from cartographer.walls import STONE_COLOR_CENTROID, run

    r, g, b = STONE_COLOR_CENTROID
    image = np.full((300, 300, 3), [r, g, b], dtype=np.uint8)
    result = run(image, 16.0, (50.0, 50.0), _box_placements())

    assert len(result) > 0
    for tile in result:
        assert isinstance(tile[0], int) and isinstance(tile[1], int)
