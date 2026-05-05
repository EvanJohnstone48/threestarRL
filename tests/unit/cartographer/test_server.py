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


# ---------------------------------------------------------------------------
# Review-mode helpers
# ---------------------------------------------------------------------------


def _make_candidate_layout():
    from sandbox_core.schemas import (
        BaseLayout,
        BaseLayoutMetadata,
        BuildingPlacement,
        CartographerProvenance,
    )

    return BaseLayout(
        metadata=BaseLayoutMetadata(name="shot", th_level=6),
        th_level=6,
        placements=[
            BuildingPlacement(building_type="cannon", origin=(10, 10)),
            BuildingPlacement(building_type="town_hall", origin=(20, 20)),
        ],
        provenance=CartographerProvenance(
            source_screenshot="shot.png",
            ingest_timestamp_utc="2026-01-01T00:00:00+00:00",
            dataset_version="1",
            confidence_threshold=0.5,
            derived_pitch_px=64.0,
            derived_origin_px=(100.0, 50.0),
            per_placement_confidence={"cannon_0": 0.9, "town_hall_1": 0.95},
        ),
    )


def _make_review_app(tmp_path: Path):
    import numpy as np
    from cartographer.server import create_review_app
    from sandbox_core.schemas import BaseLayout

    # Tiny 200x200 solid-grey image (no real grass/stone features — walls returns [])
    image = np.full((200, 200, 3), 128, dtype=np.uint8)

    screenshot_path = tmp_path / "shot.png"
    # Write a minimal PNG so FileResponse can serve it
    from PIL import Image

    Image.fromarray(image).save(str(screenshot_path))

    layout: BaseLayout = _make_candidate_layout()
    out_path = tmp_path / "out.json"
    cal_path = tmp_path / "calibration.json"
    config = {"dataset_version": "1", "confidence_threshold": 0.5}

    app = create_review_app(
        screenshot_path=screenshot_path,
        candidate_layout=layout,
        derived_pitch_px=64.0,
        derived_origin_px=(100.0, 50.0),
        image=image,
        out_path=out_path,
        config=config,
        calibration_path=cal_path,
    )
    return app, out_path, cal_path


# ---------------------------------------------------------------------------
# 8. GET /api/review/baselayout — returns candidate layout + grid params
# ---------------------------------------------------------------------------


def test_review_get_baselayout(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    app, _, _ = _make_review_app(tmp_path)
    client = TestClient(app)
    resp = client.get("/api/review/baselayout")
    assert resp.status_code == 200
    data = resp.json()
    assert "screenshot_url" in data
    assert "candidate_baselayout" in data
    assert data["derived_pitch_px"] == pytest.approx(64.0)
    assert data["derived_origin_px"] == pytest.approx([100.0, 50.0])
    # candidate_baselayout should be a dict with placements
    layout_dict = data["candidate_baselayout"]
    assert "placements" in layout_dict
    assert any(p["building_type"] == "cannon" for p in layout_dict["placements"])


# ---------------------------------------------------------------------------
# 9. POST /api/review/baselayout — writes JSON with reviewed=True
# ---------------------------------------------------------------------------


def test_review_post_corrects_placements(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    app, out_path, _ = _make_review_app(tmp_path)
    client = TestClient(app, raise_server_exceptions=True)

    payload = {
        "corrected_placements": [
            {"building_type": "cannon", "origin": [5, 5]},
            {"building_type": "town_hall", "origin": [15, 15]},
        ]
    }
    resp = client.post("/api/review/baselayout", json=payload)
    assert resp.status_code == 200

    assert out_path.exists()
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["provenance"]["reviewed"] is True
    origins = {p["building_type"]: p["origin"] for p in written["placements"]}
    assert origins["cannon"] == [5, 5]
    assert origins["town_hall"] == [15, 15]


# ---------------------------------------------------------------------------
# 10. POST /api/review/baselayout — does NOT modify calibration file
# ---------------------------------------------------------------------------


def test_review_post_does_not_modify_calibration(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    app, _, cal_path = _make_review_app(tmp_path)
    client = TestClient(app, raise_server_exceptions=True)

    # cal_path does not exist before POST
    assert not cal_path.exists()

    payload = {
        "corrected_placements": [
            {"building_type": "cannon", "origin": [5, 5]},
        ]
    }
    client.post("/api/review/baselayout", json=payload)

    # Still must not exist
    assert not cal_path.exists()
