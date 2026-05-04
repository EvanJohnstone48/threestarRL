"""Grid geometry, footprint occupancy, and region helpers.

Coordinate convention (per app/docs/sandbox/prd.md §5.1):
  - 50x50 outer grid; (row, col) origin at top-left.
  - Inner buildable region: rows 3..46, cols 3..46.
  - Deploy ring: rows 0..2, 47..49, cols 0..2, 47..49.
  - Tile centers at (r + 0.5, c + 0.5).
  - Building origin = top-left tile of footprint.
"""

from __future__ import annotations

import math
from collections.abc import Iterator

GRID_SIZE: int = 50
BUILDABLE_MIN: int = 3
BUILDABLE_MAX: int = 46  # inclusive


def in_grid(row: int, col: int) -> bool:
    return 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE


def in_buildable_region(row: int, col: int) -> bool:
    return BUILDABLE_MIN <= row <= BUILDABLE_MAX and BUILDABLE_MIN <= col <= BUILDABLE_MAX


def in_deploy_ring(row: int, col: int) -> bool:
    return in_grid(row, col) and not in_buildable_region(row, col)


def footprint_tiles(
    origin: tuple[int, int], footprint: tuple[int, int]
) -> Iterator[tuple[int, int]]:
    r0, c0 = origin
    h, w = footprint
    for dr in range(h):
        for dc in range(w):
            yield (r0 + dr, c0 + dc)


def footprint_in_buildable(origin: tuple[int, int], footprint: tuple[int, int]) -> bool:
    return all(in_buildable_region(r, c) for r, c in footprint_tiles(origin, footprint))


def footprint_center(origin: tuple[int, int], footprint: tuple[int, int]) -> tuple[float, float]:
    r0, c0 = origin
    h, w = footprint
    return (r0 + h / 2.0, c0 + w / 2.0)


def tile_center(row: int, col: int) -> tuple[float, float]:
    return (row + 0.5, col + 0.5)


def euclidean(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def distance_point_to_square_hitbox(
    point: tuple[float, float],
    origin: tuple[int, int],
    footprint: tuple[int, int],
    hitbox_inset: float,
) -> float:
    """Euclidean distance from a point to the closest tile of a building's square hitbox.

    The hitbox is the footprint shrunk by `hitbox_inset` on each side. For a 1x1 wall
    with inset 0.5, the hitbox is the full tile (a degenerate point at the center).
    """
    r0, c0 = origin
    h, w = footprint
    r_min = r0 + hitbox_inset
    r_max = r0 + h - hitbox_inset
    c_min = c0 + hitbox_inset
    c_max = c0 + w - hitbox_inset
    if r_min > r_max:
        r_min = r_max = (r_min + r_max) / 2.0
    if c_min > c_max:
        c_min = c_max = (c_min + c_max) / 2.0
    pr, pc = point
    dr = max(r_min - pr, 0.0, pr - r_max)
    dc = max(c_min - pc, 0.0, pc - c_max)
    return math.hypot(dr, dc)


def default_hitbox_inset(footprint: tuple[int, int]) -> float:
    """Default inset rule: 0.5 tiles, regardless of footprint size.

    Per-entity overrides (army_camp = 1.0; wall = 0.0) live in
    manual_overrides.json and are applied by the content loader.
    """
    del footprint  # signature kept for forward compat (e.g. shape-aware overrides).
    return 0.5


def overlap(
    origin_a: tuple[int, int],
    footprint_a: tuple[int, int],
    origin_b: tuple[int, int],
    footprint_b: tuple[int, int],
) -> bool:
    """Two axis-aligned footprints overlap iff they share at least one tile."""
    ar0, ac0 = origin_a
    ah, aw = footprint_a
    br0, bc0 = origin_b
    bh, bw = footprint_b
    return not (ar0 + ah <= br0 or br0 + bh <= ar0 or ac0 + aw <= bc0 or bc0 + bw <= ac0)


__all__ = [
    "BUILDABLE_MAX",
    "BUILDABLE_MIN",
    "GRID_SIZE",
    "default_hitbox_inset",
    "distance_point_to_square_hitbox",
    "euclidean",
    "footprint_center",
    "footprint_in_buildable",
    "footprint_tiles",
    "in_buildable_region",
    "in_deploy_ring",
    "in_grid",
    "overlap",
    "tile_center",
]
