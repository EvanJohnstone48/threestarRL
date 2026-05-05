"""Stage 4: snap Roboflow detections to integer grid tiles."""

from __future__ import annotations

import math
from dataclasses import dataclass

from cartographer.detect import Detection

_FOOTPRINTS: dict[str, tuple[int, int]] = {
    "town_hall": (4, 4),
    "clan_castle": (3, 3),
    "cannon": (3, 3),
    "archer_tower": (3, 3),
    "mortar": (3, 3),
    "air_defense": (3, 3),
    "air_sweeper": (2, 2),
    "wizard_tower": (3, 3),
    "army_camp": (5, 5),
    "barracks": (3, 3),
    "laboratory": (4, 4),
    "spell_factory": (3, 3),
    "gold_mine": (3, 3),
    "elixir_collector": (3, 3),
    "gold_storage": (4, 4),
    "elixir_storage": (4, 4),
    "builders_hut": (2, 2),
    "bomb": (1, 1),
    "giant_bomb": (2, 2),
    "spring_trap": (1, 1),
    "air_bomb": (1, 1),
}


@dataclass(frozen=True)
class AlignedPlacement:
    class_name: str
    origin: tuple[int, int]
    footprint: tuple[int, int]
    confidence: float


def run(
    detections: list[Detection],
    pitch: float,
    origin: tuple[float, float],
) -> list[AlignedPlacement]:
    """Snap each detection's bbox centre to the nearest grid tile origin."""
    ox, oy = origin
    placements: list[AlignedPlacement] = []
    for det in detections:
        x1, y1, x2, y2 = det.bbox_xyxy
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        col = math.floor((cx - ox) / pitch)
        row = math.floor((cy - oy) / pitch)
        fp = _FOOTPRINTS.get(det.class_name, (3, 3))
        half_w, half_h = fp[0] // 2, fp[1] // 2
        tile_origin = (max(0, col - half_w), max(0, row - half_h))
        placements.append(
            AlignedPlacement(
                class_name=det.class_name,
                origin=tile_origin,
                footprint=fp,
                confidence=det.confidence,
            )
        )
    return placements
