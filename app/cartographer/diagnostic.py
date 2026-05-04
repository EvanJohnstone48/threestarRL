"""Stage 7: render an annotated diagnostic PNG."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from cartographer.align import AlignedPlacement


def render(
    image: np.ndarray,
    placements: list[AlignedPlacement],
    wall_tiles: list[tuple[int, int]],
    pitch: float,
    origin: tuple[float, float],
    out_path: Path,
) -> None:
    """Save an annotated copy of *image* to *out_path*.

    Draws a labelled rectangle for each aligned placement over the source image.
    """
    from PIL import Image, ImageDraw, ImageFont

    pil_img = Image.fromarray(image).convert("RGB")
    draw = ImageDraw.Draw(pil_img)
    ox, oy = origin

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

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pil_img.save(out_path)
