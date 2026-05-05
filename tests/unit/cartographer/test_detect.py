"""Tests for cartographer.detect — includes AC-C8 class-name parity."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


def _fake_response(predictions: list[dict]) -> MagicMock:
    mock = MagicMock()
    mock.json.return_value = {"predictions": predictions, "image": {"width": 100, "height": 100}}
    mock.raise_for_status.return_value = None
    return mock


def test_parse_response_bbox_center_to_xyxy() -> None:
    """bbox center (x,y) + (w,h) is converted to (x1,y1,x2,y2)."""
    from cartographer.detect import _parse_response

    data = {
        "predictions": [
            {"class": "cannon", "x": 100.0, "y": 200.0, "width": 60.0, "height": 40.0, "confidence": 0.9},
        ]
    }
    accepted, sub = _parse_response(data, confidence_threshold=0.5)
    assert len(accepted) == 1
    assert len(sub) == 0
    x1, y1, x2, y2 = accepted[0].bbox_xyxy
    assert x1 == pytest.approx(70.0)
    assert y1 == pytest.approx(180.0)
    assert x2 == pytest.approx(130.0)
    assert y2 == pytest.approx(220.0)


def test_confidence_filtering() -> None:
    """Detections split correctly into accepted vs sub-threshold."""
    from cartographer.detect import _parse_response

    data = {
        "predictions": [
            {"class": "cannon", "x": 10.0, "y": 10.0, "width": 20.0, "height": 20.0, "confidence": 0.8},
            {"class": "mortar", "x": 50.0, "y": 50.0, "width": 20.0, "height": 20.0, "confidence": 0.3},
            {"class": "archer_tower", "x": 80.0, "y": 80.0, "width": 20.0, "height": 20.0, "confidence": 0.5},
        ]
    }
    accepted, sub = _parse_response(data, confidence_threshold=0.5)
    assert len(accepted) == 2
    assert len(sub) == 1
    assert sub[0].class_name == "mortar"
    assert {d.class_name for d in accepted} == {"cannon", "archer_tower"}


def test_missing_api_key_raises() -> None:
    from cartographer.detect import MissingAPIKeyError, run

    image = np.zeros((100, 100, 3), dtype=np.uint8)
    with pytest.raises(MissingAPIKeyError):
        run(image, project_name="proj", dataset_version="1", confidence_threshold=0.5, api_key="")


def test_run_returns_two_lists_via_mock() -> None:
    """run() parses a mocked Roboflow response and returns (accepted, sub_threshold)."""
    from cartographer.detect import run

    fake = _fake_response([
        {"class": "town_hall", "x": 50.0, "y": 50.0, "width": 80.0, "height": 80.0, "confidence": 0.95},
        {"class": "cannon", "x": 20.0, "y": 20.0, "width": 30.0, "height": 30.0, "confidence": 0.2},
    ])
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    with patch("requests.post", return_value=fake):
        accepted, sub = run(
            image,
            project_name="proj",
            dataset_version="1",
            confidence_threshold=0.5,
            api_key="test-key",
        )

    assert len(accepted) == 1
    assert accepted[0].class_name == "town_hall"
    assert len(sub) == 1
    assert sub[0].class_name == "cannon"


def test_sub_threshold_not_in_accepted() -> None:
    """Sub-threshold detections are never in the accepted list."""
    from cartographer.detect import _parse_response

    data = {
        "predictions": [
            {"class": "bomb", "x": 5.0, "y": 5.0, "width": 10.0, "height": 10.0, "confidence": 0.1},
        ]
    }
    accepted, sub = _parse_response(data, confidence_threshold=0.5)
    assert accepted == []
    assert len(sub) == 1


def test_roboflow_class_enum_parity() -> None:
    """AC-C8: RoboflowClass values must equal buildings.json (minus 'wall') union traps.json."""
    from cartographer.detect import RoboflowClass

    data_dir = Path(__file__).parents[3] / "app" / "data"
    buildings = json.loads((data_dir / "buildings.json").read_text(encoding="utf-8"))
    traps = json.loads((data_dir / "traps.json").read_text(encoding="utf-8"))
    expected = (
        {entry["name"] for entry in buildings["entries"]}
        - {"wall"}
        | {entry["name"] for entry in traps["entries"]}
    )
    actual = {c.value for c in RoboflowClass}
    assert actual == expected
