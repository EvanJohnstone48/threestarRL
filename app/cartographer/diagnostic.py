"""Stage 7: render an annotated diagnostic PNG."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np

from cartographer.align import AlignedPlacement
from cartographer.detect import Detection
from cartographer.grid import ISO_ANGLE_1, ISO_ANGLE_2


def render(
    image: np.ndarray,
    placements: list[AlignedPlacement],
    wall_tiles: list[tuple[int, int]],
    sub_threshold: list[Detection],
    pitch: float,
    origin: tuple[float, float],
    out_path: Path,
    *,
    grid_failed: bool = False,
) -> None:
    """Save an annotated copy of *image* to *out_path*.

    Draws:
    - Sub-threshold detections in orange (raw pixel bbox).
    - Aligned placements in red with class labels.
    - Wall tiles in blue.
    - Inferred iso grid as grey tick lines (unless *grid_failed*).
    - Red border with "GRID FAIL" text when *grid_failed* is True.
    """
    from PIL import Image, ImageDraw

    pil_img = Image.fromarray(image).convert("RGB")
    draw = ImageDraw.Draw(pil_img)
    ox, oy = origin

    for det in sub_threshold:
        x1, y1, x2, y2 = det.bbox_xyxy
        draw.rectangle([x1, y1, x2, y2], outline=(255, 140, 0), width=1)

    for p in placements:
        tx, ty = p.origin
        x0 = ox + tx * pitch
        y0 = oy + ty * pitch
        x1 = x0 + p.footprint[0] * pitch
        y1 = y0 + p.footprint[1] * pitch
        draw.rectangle([x0, y0, x1, y1], outline=(255, 0, 0), width=2)
        draw.text((x0 + 2, y0 + 2), p.class_name, fill=(255, 255, 0))

    for tile in wall_tiles:
        tx, ty = tile
        x0 = ox + tx * pitch
        y0 = oy + ty * pitch
        draw.rectangle([x0, y0, x0 + pitch, y0 + pitch], outline=(0, 0, 255), width=1)

    if grid_failed:
        w, h = pil_img.size
        draw.rectangle([0, 0, w - 1, h - 1], outline=(255, 0, 0), width=4)
        draw.text((4, 4), "GRID FAIL", fill=(255, 0, 0))
    else:
        _draw_grid(draw, pil_img.size, pitch, origin)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pil_img.save(out_path)


def _draw_grid(
    draw: Any,
    size: tuple[int, int],
    pitch: float,
    origin: tuple[float, float],
) -> None:
    """Draw iso grid lines as grey tick marks on the image."""
    w, h = size
    ox, oy = origin

    d1 = (math.cos(ISO_ANGLE_1), math.sin(ISO_ANGLE_1))
    d2 = (math.cos(ISO_ANGLE_2), math.sin(ISO_ANGLE_2))

    # Number of grid lines to draw along each axis direction
    n_lines = int(max(w, h) / pitch) + 4

    for axis_d, other_d in ((d1, d2), (d2, d1)):
        for k in range(-n_lines, n_lines):
            # Base point on the grid line
            bx = ox + k * pitch * other_d[0]
            by = oy + k * pitch * other_d[1]
            # Extend along axis_d far enough to cross the full image
            length = max(w, h) * 2.0
            x0 = bx - axis_d[0] * length
            y0 = by - axis_d[1] * length
            x1 = bx + axis_d[0] * length
            y1 = by + axis_d[1] * length
            draw.line([(x0, y0), (x1, y1)], fill=(128, 128, 128), width=1)
