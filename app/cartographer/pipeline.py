"""Orchestration: runs the seven cartographer stages in fixed order."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from sandbox_core.schemas import BaseLayout

from cartographer import align, detect, diagnostic, emit, grid, preprocess, walls
from cartographer.align import AlignedPlacement
from cartographer.calibration import load_offsets
from cartographer.detect import Detection
from cartographer.grid import GridCrossValidationError

_CONFIG_PATH = Path(__file__).parent.parent / "data" / "cartographer_config.json"


def _load_config() -> dict[str, Any]:
    return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))


def _resolve_out_path(screenshot_path: Path, out_path: Path | None) -> Path:
    if out_path is None:
        return (
            Path(__file__).parent.parent
            / "data"
            / "scraped_bases"
            / (screenshot_path.stem + ".json")
        )
    return Path(out_path)


def run_to_align(
    screenshot_path: Path,
    out_path: Path | None = None,
) -> tuple[np.ndarray, list[Detection], list[Detection], float, tuple[float, float], list[AlignedPlacement], Path, dict[str, Any]]:
    """Run stages 1-4 (preprocess -> detect -> grid -> align) and return intermediate state.

    Returns (image, accepted, sub_threshold, pitch, origin, placements, diag_path, cfg).
    Raises GridCrossValidationError (with diagnostic PNG) if grid derivation fails.
    Does NOT run walls, emit, or write any JSON.
    """
    screenshot_path = Path(screenshot_path)
    cfg = _load_config()
    out_path = _resolve_out_path(screenshot_path, out_path)
    diag_path = out_path.with_name(out_path.stem + ".diag.png")

    api_key = os.environ.get("ROBOFLOW_API_KEY", "")

    image = preprocess.load(screenshot_path)
    accepted, sub_threshold = detect.run(
        image,
        project_name=cfg["project_name"],
        dataset_version=cfg["dataset_version"],
        confidence_threshold=cfg["confidence_threshold"],
        api_key=api_key,
    )
    try:
        pitch, origin = grid.run(image, detections=accepted)
    except GridCrossValidationError:
        diagnostic.render(image, [], [], sub_threshold, 64.0, (0.0, 0.0), diag_path, grid_failed=True)
        raise

    offsets = load_offsets(cfg["dataset_version"])
    placements = align.run(accepted, pitch, origin, offsets=offsets)
    return image, accepted, sub_threshold, pitch, origin, placements, diag_path, cfg


def run(screenshot_path: Path, out_path: Path | None = None) -> BaseLayout:
    """Run the full ingest pipeline and return the validated BaseLayout.

    Writes JSON to *out_path* (default: app/data/scraped_bases/<stem>.json).
    Always emits a co-located diagnostic PNG at <out_path stem>.diag.png.
    On any exception the diagnostic PNG is still attempted before re-raising.
    """
    screenshot_path = Path(screenshot_path)
    out_path = _resolve_out_path(screenshot_path, out_path)
    image, _accepted, sub_threshold, pitch, origin, placements, diag_path, cfg = run_to_align(
        screenshot_path, out_path
    )
    wall_tiles = walls.run(image, pitch, origin, placements=placements)

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
        diagnostic.render(image, placements, wall_tiles, sub_threshold, pitch, origin, diag_path)
        raise

    diagnostic.render(image, placements, wall_tiles, sub_threshold, pitch, origin, diag_path)
    return layout
