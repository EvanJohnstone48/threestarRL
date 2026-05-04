"""Orchestration: runs the seven cartographer stages in fixed order."""

from __future__ import annotations

import json
from pathlib import Path

from sandbox_core.schemas import BaseLayout

from cartographer import align, detect, diagnostic, emit, grid, preprocess, walls

_CONFIG_PATH = Path(__file__).parent.parent / "data" / "cartographer_config.json"


def _load_config() -> dict:
    return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))


def run(screenshot_path: Path, out_path: Path | None = None) -> BaseLayout:
    """Run the full ingest pipeline and return the validated BaseLayout.

    Writes JSON to *out_path* (default: app/data/scraped_bases/<stem>.json).
    Always emits a co-located diagnostic PNG at <out_path stem>.diag.png.
    On any exception the diagnostic PNG is still attempted before re-raising.
    """
    screenshot_path = Path(screenshot_path)
    cfg = _load_config()

    if out_path is None:
        out_path = (
            Path(__file__).parent.parent
            / "data"
            / "scraped_bases"
            / (screenshot_path.stem + ".json")
        )
    out_path = Path(out_path)
    diag_path = out_path.with_name(out_path.stem + ".diag.png")

    image = preprocess.load(screenshot_path)
    detections = detect.run(image)
    pitch, origin = grid.run(image)
    placements = align.run(detections, pitch, origin)
    wall_tiles = walls.run(image, pitch, origin)

    try:
        layout = emit.run(
            placements=placements,
            wall_tiles=wall_tiles,
            source_screenshot=str(screenshot_path),
            pitch=pitch,
            origin=origin,
            dataset_version=cfg["dataset_version"],
            confidence_threshold=cfg["confidence_threshold"],
            out_path=out_path,
        )
    except Exception:
        diagnostic.render(image, placements, wall_tiles, pitch, origin, diag_path)
        raise

    diagnostic.render(image, placements, wall_tiles, pitch, origin, diag_path)
    return layout
