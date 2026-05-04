"""Stage 2: Roboflow object detection.

`RoboflowClass` is locked to `buildings.json` keys minus "wall" (AC-C8).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np


class RoboflowClass(StrEnum):
    TOWN_HALL = "town_hall"
    CLAN_CASTLE = "clan_castle"
    CANNON = "cannon"
    ARCHER_TOWER = "archer_tower"
    MORTAR = "mortar"
    AIR_DEFENSE = "air_defense"
    WIZARD_TOWER = "wizard_tower"
    ARMY_CAMP = "army_camp"
    BARRACKS = "barracks"
    LABORATORY = "laboratory"
    SPELL_FACTORY = "spell_factory"
    GOLD_MINE = "gold_mine"
    ELIXIR_COLLECTOR = "elixir_collector"
    GOLD_STORAGE = "gold_storage"
    ELIXIR_STORAGE = "elixir_storage"
    BUILDERS_HUT = "builders_hut"


@dataclass(frozen=True)
class Detection:
    class_name: str
    bbox_xyxy: tuple[float, float, float, float]
    confidence: float


def run(image: np.ndarray) -> list[Detection]:
    """Stub: returns a single Town Hall detection at the image centre with confidence 1.0."""
    h, w = image.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    half = 40.0
    return [
        Detection(
            class_name=RoboflowClass.TOWN_HALL,
            bbox_xyxy=(cx - half, cy - half, cx + half, cy + half),
            confidence=1.0,
        )
    ]
