"""Stage 2: Roboflow object detection.

`RoboflowClass` is locked to `buildings.json` keys minus "wall" (AC-C8).
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from enum import StrEnum

import numpy as np


class MissingAPIKeyError(RuntimeError):
    """Raised when ROBOFLOW_API_KEY is not set."""


class RoboflowClass(StrEnum):
    TOWN_HALL = "town_hall"
    CLAN_CASTLE = "clan_castle"
    CANNON = "cannon"
    ARCHER_TOWER = "archer_tower"
    MORTAR = "mortar"
    AIR_DEFENSE = "air_defense"
    AIR_SWEEPER = "air_sweeper"
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
    BOMB = "bomb"
    GIANT_BOMB = "giant_bomb"
    SPRING_TRAP = "spring_trap"
    AIR_BOMB = "air_bomb"


# Trap classes are routed into BaseLayout.traps rather than placements; the
# alignment + emit stages dispatch on this set.
TRAP_CLASSES: frozenset[str] = frozenset(
    {
        RoboflowClass.BOMB,
        RoboflowClass.GIANT_BOMB,
        RoboflowClass.SPRING_TRAP,
        RoboflowClass.AIR_BOMB,
    }
)

_ENDPOINT_BASE = "https://detect.roboflow.com"


@dataclass(frozen=True)
class Detection:
    class_name: str
    bbox_xyxy: tuple[float, float, float, float]
    confidence: float


def _image_to_base64(image: np.ndarray) -> str:
    from PIL import Image

    buf = io.BytesIO()
    Image.fromarray(image).save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _parse_response(
    data: dict,
    confidence_threshold: float,
    target_shape: tuple[int, int] | None = None,
) -> tuple[list[Detection], list[Detection]]:
    """Split Roboflow predictions into accepted and sub-threshold detections."""
    scale_x = 1.0
    scale_y = 1.0
    response_image = data.get("image")
    if target_shape and isinstance(response_image, dict):
        response_w = float(response_image.get("width") or 0)
        response_h = float(response_image.get("height") or 0)
        target_h, target_w = target_shape
        if response_w > 0 and response_h > 0:
            scale_x = target_w / response_w
            scale_y = target_h / response_h

    accepted: list[Detection] = []
    sub_threshold: list[Detection] = []
    for pred in data.get("predictions", []):
        x, y = float(pred["x"]) * scale_x, float(pred["y"]) * scale_y
        w, h = float(pred["width"]) * scale_x, float(pred["height"]) * scale_y
        bbox_xyxy = (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
        conf = float(pred["confidence"])
        det = Detection(
            class_name=pred["class"],
            bbox_xyxy=bbox_xyxy,
            confidence=conf,
        )
        if conf >= confidence_threshold:
            accepted.append(det)
        else:
            sub_threshold.append(det)
    return accepted, sub_threshold


def run(
    image: np.ndarray,
    project_name: str,
    dataset_version: str,
    confidence_threshold: float,
    api_key: str,
) -> tuple[list[Detection], list[Detection]]:
    """Call the Roboflow model and return (accepted, sub_threshold) detections.

    Raises MissingAPIKeyError if api_key is empty.
    """
    import requests

    if not api_key:
        raise MissingAPIKeyError(
            "Set ROBOFLOW_API_KEY to run real detection. "
            "To run with stub detections instead, pass a synthetic image to the pipeline "
            "and mock cartographer.detect.run in your tests."
        )
    b64 = _image_to_base64(image)
    url = f"{_ENDPOINT_BASE}/{project_name}/{dataset_version}"
    resp = requests.post(
        url,
        params={"api_key": api_key},
        data=b64,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=60,
    )
    resp.raise_for_status()
    return _parse_response(resp.json(), confidence_threshold, target_shape=image.shape[:2])
