"""Tests for cartographer.server — median aggregator and FastAPI endpoints."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 1. compute_offsets — single instance
# ---------------------------------------------------------------------------


def test_compute_offsets_single_instance() -> None:
    from cartographer.server import compute_offsets

    # bbox_xyxy = (10, 20, 50, 80) → bottom_center = (30, 80)
    # placed_anchor_xy = (35, 75) → offset = (5, -5)
    records = [
        {
            "filename": "shot.png",
            "class_name": "cannon",
            "bbox_xyxy": [10.0, 20.0, 50.0, 80.0],
            "placed_anchor_xy": [35.0, 75.0],
        }
    ]
    offsets, sample_counts = compute_offsets(records)
    assert offsets == {"cannon": (5.0, -5.0)}
    assert sample_counts == {"cannon": 1}


# ---------------------------------------------------------------------------
# 2. compute_offsets — multiple instances: result is median, not mean
# ---------------------------------------------------------------------------


def test_compute_offsets_median_not_mean() -> None:
    from cartographer.server import compute_offsets

    # Three cannons with dx values [2, 4, 100] → median = 4 (mean would be ~35)
    # dy values [0, 0, 0] → median = 0
    def _rec(placed_x: float) -> dict:
        # bbox bottom_center = (30, 80)
        return {
            "filename": "shot.png",
            "class_name": "cannon",
            "bbox_xyxy": [10.0, 20.0, 50.0, 80.0],
            "placed_anchor_xy": [placed_x, 80.0],
        }

    records = [_rec(32.0), _rec(34.0), _rec(130.0)]
    offsets, sample_counts = compute_offsets(records)
    assert offsets["cannon"] == (4.0, 0.0)
    assert sample_counts["cannon"] == 3


# ---------------------------------------------------------------------------
# 3. compute_offsets — mixed classes produce separate per-class results
# ---------------------------------------------------------------------------


def test_compute_offsets_mixed_classes() -> None:
    from cartographer.server import compute_offsets

    records = [
        {
            "filename": "shot.png",
            "class_name": "cannon",
            "bbox_xyxy": [0.0, 0.0, 20.0, 40.0],
            "placed_anchor_xy": [12.0, 38.0],
        },
        {
            "filename": "shot.png",
            "class_name": "archer_tower",
            "bbox_xyxy": [0.0, 0.0, 30.0, 60.0],
            "placed_anchor_xy": [10.0, 55.0],
        },
    ]
    offsets, sample_counts = compute_offsets(records)
    # cannon: bottom_center=(10,40), placed=(12,38) → offset=(2,-2)
    assert offsets["cannon"] == pytest.approx((2.0, -2.0))
    # archer_tower: bottom_center=(15,60), placed=(10,55) → offset=(-5,-5)
    assert offsets["archer_tower"] == pytest.approx((-5.0, -5.0))
    assert sample_counts == {"cannon": 1, "archer_tower": 1}


# ---------------------------------------------------------------------------
# Helpers shared by smoke tests
# ---------------------------------------------------------------------------


def _make_app(tmp_path: Path):
    """Build a test FastAPI app with stub screenshots and a temp calibration path."""
    from cartographer.detect import Detection
    from cartographer.server import ScreenshotEntry, create_app

    entries = [
        ScreenshotEntry(
            filename="shot.png",
            image_path=tmp_path / "shot.png",
            detections=[
                Detection(
                    class_name="cannon",
                    bbox_xyxy=(10.0, 20.0, 50.0, 80.0),
                    confidence=0.9,
                )
            ],
        )
    ]
    config = {"project_name": "test", "dataset_version": "1", "confidence_threshold": 0.5}
    cal_path = tmp_path / "calibration.json"
    return create_app(entries, config, calibration_path=cal_path), cal_path, config


# ---------------------------------------------------------------------------
# 4. GET /api/buildings — returns {name: [N, N]} dict
# ---------------------------------------------------------------------------


def test_get_buildings_returns_footprints(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    app, _, _ = _make_app(tmp_path)
    client = TestClient(app)
    resp = client.get("/api/buildings")
    assert resp.status_code == 200
    data = resp.json()
    assert "town_hall" in data
    assert data["town_hall"] == [4, 4]
    assert "cannon" in data


# ---------------------------------------------------------------------------
# 5. GET /api/config — returns config dict
# ---------------------------------------------------------------------------


def test_get_config_returns_config(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    app, _, config = _make_app(tmp_path)
    client = TestClient(app)
    resp = client.get("/api/config")
    assert resp.status_code == 200
    assert resp.json() == config


# ---------------------------------------------------------------------------
# 6. GET /api/screenshots — returns cached screenshot data
# ---------------------------------------------------------------------------


def test_get_screenshots_returns_entries(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    app, _, _ = _make_app(tmp_path)
    client = TestClient(app)
    resp = client.get("/api/screenshots")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    entry = data[0]
    assert entry["filename"] == "shot.png"
    assert len(entry["detections"]) == 1
    det = entry["detections"][0]
    assert det["class_name"] == "cannon"
    assert det["confidence"] == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# 7. POST /api/calibration — writes calibration file
# ---------------------------------------------------------------------------


def test_post_calibration_writes_file(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    app, cal_path, _ = _make_app(tmp_path)
    client = TestClient(app, raise_server_exceptions=True)

    payload = [
        {
            "filename": "shot.png",
            "class_name": "cannon",
            "bbox_xyxy": [10.0, 20.0, 50.0, 80.0],
            "placed_anchor_xy": [35.0, 75.0],
        }
    ]
    resp = client.post("/api/calibration", json=payload)
    assert resp.status_code == 200

    assert cal_path.exists()
    written = json.loads(cal_path.read_text(encoding="utf-8"))
    assert written["dataset_version"] == "1"
    assert "cannon" in written["offsets"]
    assert written["offsets"]["cannon"] == pytest.approx([5.0, -5.0])
    assert written["sample_counts"]["cannon"] == 1
    assert "calibrated_at_utc" in written
