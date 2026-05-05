"""Stage 6: assemble BaseLayout v3, validate with Pydantic, write JSON."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

from sandbox_core.schemas import (
    BaseLayout,
    BaseLayoutMetadata,
    BuildingPlacement,
    CartographerProvenance,
    TrapPlacement,
)

from cartographer.align import AlignedPlacement
from cartographer.detect import TRAP_CLASSES

_TH_LEVEL = 6


def run(
    placements: list[AlignedPlacement],
    wall_tiles: list[tuple[int, int]],
    source_screenshot: str,
    pitch: float,
    origin: tuple[float, float],
    dataset_version: str,
    confidence_threshold: float,
    out_path: Path,
) -> BaseLayout:
    """Assemble a valid BaseLayout, write it to *out_path*, and return it.

    Detections classified as traps (`TRAP_CLASSES` from `detect.py`) are routed
    into `BaseLayout.traps`; everything else lands in `BaseLayout.placements`.
    """
    building_placements: list[BuildingPlacement] = []
    trap_placements: list[TrapPlacement] = []
    for p in placements:
        if p.class_name in TRAP_CLASSES:
            trap_placements.append(TrapPlacement(trap_type=p.class_name, origin=p.origin))
        else:
            building_placements.append(BuildingPlacement(building_type=p.class_name, origin=p.origin))
    for tile in wall_tiles:
        building_placements.append(BuildingPlacement(building_type="wall", origin=tile))

    per_conf = {f"{p.class_name}_{i}": p.confidence for i, p in enumerate(placements)}

    provenance = CartographerProvenance(
        source_screenshot=source_screenshot,
        ingest_timestamp_utc=datetime.datetime.now(datetime.UTC).isoformat(),
        dataset_version=dataset_version,
        confidence_threshold=confidence_threshold,
        derived_pitch_px=pitch,
        derived_origin_px=(origin[0], origin[1]),
        per_placement_confidence=per_conf,
    )

    layout = BaseLayout(
        metadata=BaseLayoutMetadata(name=Path(source_screenshot).stem, th_level=_TH_LEVEL),
        th_level=_TH_LEVEL,
        placements=building_placements,
        traps=trap_placements,
        provenance=provenance,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(layout.model_dump(), indent=2), encoding="utf-8")
    return layout
