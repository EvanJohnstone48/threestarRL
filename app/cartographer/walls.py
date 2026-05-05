"""Stage 5: classify wall tiles by stone-vs-grass colour matching."""

from __future__ import annotations

import math

import numpy as np

from cartographer.align import AlignedPlacement
from cartographer.grid import ISO_ANGLE_1, ISO_ANGLE_2

# Stone-colour centroid (RGB, uint8 space).
# Derived from sampling TH6 home-village wall sections in reference screenshots.
STONE_COLOR_CENTROID: tuple[int, int, int] = (140, 120, 100)

# Maximum Euclidean distance from STONE_COLOR_CENTROID to classify a tile as wall.
STONE_COLOR_THRESHOLD: float = 60.0


def run(
    image: np.ndarray,
    pitch: float,
    origin: tuple[float, float],
    placements: list[AlignedPlacement] | None = None,
) -> list[tuple[int, int]]:
    """Classify candidate tiles as wall or non-wall by stone-colour proximity.

    Candidate set: every integer tile inside the convex hull of placement origins
    (tile space) that is not covered by any placed building footprint.

    Args:
        image: RGB image array (H, W, 3).
        pitch: Tile pitch in pixels from the grid stage.
        origin: Grid origin pixel (ox, oy) from the grid stage.
        placements: Aligned building placements from the align stage.
                    Returns [] immediately when None, empty, or fewer than 3.

    Returns:
        List of (col, row) integer tile origins classified as wall.
    """
    if not placements or len(placements) < 3:
        return []

    import cv2  # type: ignore[import-untyped]

    # Build occupied tile set from all building footprints.
    occupied: set[tuple[int, int]] = set()
    for p in placements:
        c0, r0 = p.origin
        n = p.footprint[0]
        for dc in range(n):
            for dr in range(n):
                occupied.add((c0 + dc, r0 + dr))

    # Convex hull of placement origins in tile space.
    origins = np.array([p.origin for p in placements], dtype=np.float32)
    hull = cv2.convexHull(origins.reshape(-1, 1, 2))

    # Iso basis vectors (pixel offset per one tile step).
    v1x = math.cos(ISO_ANGLE_1) * pitch
    v1y = math.sin(ISO_ANGLE_1) * pitch
    v2x = math.cos(ISO_ANGLE_2) * pitch
    v2y = math.sin(ISO_ANGLE_2) * pitch
    ox, oy = origin

    radius = max(1, int(pitch / 4))
    h_img, w_img = image.shape[:2]

    min_c = int(np.floor(origins[:, 0].min()))
    max_c = int(np.ceil(origins[:, 0].max()))
    min_r = int(np.floor(origins[:, 1].min()))
    max_r = int(np.ceil(origins[:, 1].max()))

    wall_tiles: list[tuple[int, int]] = []

    for col in range(min_c, max_c + 1):
        for row in range(min_r, max_r + 1):
            if (col, row) in occupied:
                continue

            # cv2.pointPolygonTest: positive → inside, negative → outside.
            if cv2.pointPolygonTest(hull, (float(col), float(row)), False) < 0:
                continue

            cx = ox + (col + 0.5) * v1x + (row + 0.5) * v2x
            cy = oy + (col + 0.5) * v1y + (row + 0.5) * v2y

            rgb = _sample_mean_rgb(image, cx, cy, radius, w_img, h_img)
            if rgb is None:
                continue

            dr = rgb[0] - STONE_COLOR_CENTROID[0]
            dg = rgb[1] - STONE_COLOR_CENTROID[1]
            db = rgb[2] - STONE_COLOR_CENTROID[2]
            if math.sqrt(dr * dr + dg * dg + db * db) <= STONE_COLOR_THRESHOLD:
                wall_tiles.append((col, row))

    return wall_tiles


def _sample_mean_rgb(
    image: np.ndarray,
    cx: float,
    cy: float,
    radius: int,
    w: int,
    h: int,
) -> tuple[float, float, float] | None:
    x0 = max(0, int(cx) - radius)
    x1 = min(w, int(cx) + radius + 1)
    y0 = max(0, int(cy) - radius)
    y1 = min(h, int(cy) + radius + 1)
    if x0 >= x1 or y0 >= y1:
        return None
    patch = image[y0:y1, x0:x1]
    if patch.size == 0:
        return None
    mean = patch.mean(axis=(0, 1))
    return float(mean[0]), float(mean[1]), float(mean[2])
