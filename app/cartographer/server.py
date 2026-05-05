"""FastAPI server for the cartographer calibrate/review workflow."""

from __future__ import annotations

import datetime
import json
import statistics
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from cartographer.calibration import CalibrationFile, CalibrationSample, load_offsets
from cartographer.detect import Detection

_DATA_DIR = Path(__file__).parent.parent / "data"
_BUILDINGS_PATH = _DATA_DIR / "buildings.json"
_CONFIG_PATH = _DATA_DIR / "cartographer_config.json"
_CALIBRATION_PATH = _DATA_DIR / "cartographer_calibration.json"


@dataclass
class ScreenshotEntry:
    filename: str
    image_path: Path
    detections: list[Detection]


def compute_offsets(
    records: list[dict[str, Any]],
) -> tuple[dict[str, tuple[float, float]], dict[str, int]]:
    """Compute per-class median pixel offsets from HITL-placed anchors.

    The placed anchor is the human-marked center of the building footprint:
    - 2x2/4x4: the shared inner border point of the middle tiles
    - 3x3: the center of the middle footprint tile

    offset = footprint_center - bbox_bottom_center  (independent x, y medians)
    """
    return _offsets_from_samples(_samples_from_records(records))


def _samples_from_records(records: list[dict[str, Any]]) -> list[CalibrationSample]:
    samples: list[CalibrationSample] = []
    for rec in records:
        x1, _y1, x2, y2 = rec["bbox_xyxy"]
        bottom_center_x = (x1 + x2) / 2.0
        bottom_center_y = float(y2)
        dx = float(rec["placed_anchor_xy"][0]) - bottom_center_x
        dy = float(rec["placed_anchor_xy"][1]) - bottom_center_y
        samples.append(CalibrationSample(class_name=rec["class_name"], offset=(dx, dy)))
    return samples


def _offsets_from_samples(
    samples: list[CalibrationSample],
) -> tuple[dict[str, tuple[float, float]], dict[str, int]]:
    by_class: dict[str, list[tuple[float, float]]] = {}
    for sample in samples:
        by_class.setdefault(sample.class_name, []).append(sample.offset)

    offsets: dict[str, tuple[float, float]] = {}
    sample_counts: dict[str, int] = {}
    for class_name, deltas in by_class.items():
        dxs = [d[0] for d in deltas]
        dys = [d[1] for d in deltas]
        offsets[class_name] = (statistics.median(dxs), statistics.median(dys))
        sample_counts[class_name] = len(deltas)

    return offsets, sample_counts


def _load_existing_samples(calibration_path: Path, dataset_version: str) -> list[CalibrationSample]:
    if not calibration_path.exists():
        return []

    try:
        cal = CalibrationFile.model_validate(
            json.loads(calibration_path.read_text(encoding="utf-8"))
        )
    except Exception:
        return []

    if cal.dataset_version != dataset_version:
        return []

    if cal.samples:
        return list(cal.samples)

    samples: list[CalibrationSample] = []
    for class_name, offset in cal.offsets.items():
        count = max(1, int(cal.sample_counts.get(class_name, 1)))
        samples.extend(CalibrationSample(class_name=class_name, offset=offset) for _ in range(count))
    return samples


def _load_buildings() -> dict[str, list[int]]:
    raw = json.loads(_BUILDINGS_PATH.read_text(encoding="utf-8"))
    return {entry["name"]: entry["footprint"] for entry in raw["entries"]}


def create_app(
    screenshot_entries: list[ScreenshotEntry],
    config: dict[str, Any],
    *,
    calibration_path: Path | None = None,
    shutdown_event: threading.Event | None = None,
) -> Any:
    """Create and return the FastAPI application.

    calibration_path: override for tests (defaults to app/data/cartographer_calibration.json)
    shutdown_event: set after POST /api/calibration so the caller can shut down
    """
    from fastapi import FastAPI
    from fastapi.responses import FileResponse, JSONResponse

    app = FastAPI()
    _add_local_frontend_cors(app)
    _cal_path = calibration_path if calibration_path is not None else _CALIBRATION_PATH
    _shutdown = shutdown_event if shutdown_event is not None else threading.Event()

    _image_paths: dict[str, Path] = {e.filename: e.image_path for e in screenshot_entries}

    _screenshots_cache = [
        {
            "filename": e.filename,
            "image_url": f"/api/images/{e.filename}",
            "detections": [
                {
                    "class_name": d.class_name,
                    "bbox_xyxy": list(d.bbox_xyxy),
                    "confidence": d.confidence,
                }
                for d in e.detections
            ],
        }
        for e in screenshot_entries
    ]

    @app.get("/api/screenshots")
    def get_screenshots() -> Any:
        return _screenshots_cache

    @app.get("/api/buildings")
    def get_buildings() -> Any:
        return _load_buildings()

    @app.get("/api/config")
    def get_config() -> Any:
        return config

    @app.get("/api/calibration/offsets")
    def get_calibration_offsets() -> Any:
        offsets = load_offsets(str(config["dataset_version"]), _path=_cal_path)
        return {class_name: list(offset) for class_name, offset in offsets.items()}

    @app.get("/api/images/{filename}")
    def get_image(filename: str) -> Any:
        path = _image_paths.get(filename)
        if path is None or not path.exists():
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Image not found")
        return FileResponse(str(path))

    @app.post("/api/calibration")
    def post_calibration(records: list[dict[str, Any]], finalize: bool = True) -> Any:
        samples = _load_existing_samples(_cal_path, str(config["dataset_version"]))
        samples.extend(_samples_from_records(records))
        offsets, sample_counts = _offsets_from_samples(samples)
        cal = CalibrationFile(
            dataset_version=str(config["dataset_version"]),
            offsets=offsets,
            calibrated_at_utc=datetime.datetime.now(datetime.UTC).isoformat(),
            sample_counts=sample_counts,
            samples=samples,
        )
        _cal_path.write_text(
            json.dumps(cal.model_dump(), indent=2, default=list),
            encoding="utf-8",
        )
        if finalize:
            _shutdown.set()
        return JSONResponse(
            content={
                "status": "ok",
                "finalized": finalize,
                "offsets": {class_name: list(offset) for class_name, offset in offsets.items()},
                "sample_counts": sample_counts,
            }
        )

    return app


def create_review_app(
    screenshot_path: Path,
    candidate_layout: Any,
    derived_pitch_px: float,
    derived_origin_px: tuple[float, float],
    image: np.ndarray,
    out_path: Path,
    config: dict[str, Any],
    *,
    calibration_path: Path | None = None,
    shutdown_event: threading.Event | None = None,
) -> Any:
    """Create a FastAPI app for the review-mode HITL workflow.

    calibration_path: injected for tests to verify it is never written.
    shutdown_event: set after POST /api/review/baselayout.
    """
    from fastapi import FastAPI
    from fastapi.responses import FileResponse, JSONResponse

    app = FastAPI()
    _add_local_frontend_cors(app)
    _shutdown = shutdown_event if shutdown_event is not None else threading.Event()

    # Build footprint lookup (buildings.json + trap fallbacks)
    _buildings = _load_buildings()
    _trap_footprints: dict[str, list[int]] = {
        "bomb": [1, 1],
        "giant_bomb": [2, 2],
        "spring_trap": [1, 1],
        "air_bomb": [1, 1],
    }

    def _footprint(building_type: str) -> tuple[int, int]:
        fp = _buildings.get(building_type) or _trap_footprints.get(building_type) or [3, 3]
        return (int(fp[0]), int(fp[1]))

    @app.get("/api/review/baselayout")
    def get_review_baselayout() -> Any:
        return {
            "screenshot_url": f"/api/images/{screenshot_path.name}",
            "candidate_baselayout": candidate_layout.model_dump(),
            "derived_pitch_px": derived_pitch_px,
            "derived_origin_px": list(derived_origin_px),
        }

    @app.post("/api/review/baselayout")
    def post_review_baselayout(body: dict[str, Any]) -> Any:
        from cartographer import emit, walls
        from cartographer.align import AlignedPlacement

        corrected = body.get("corrected_placements", [])
        aligned: list[AlignedPlacement] = [
            AlignedPlacement(
                class_name=p["building_type"],
                origin=(int(p["origin"][0]), int(p["origin"][1])),
                footprint=_footprint(p["building_type"]),
                confidence=1.0,
            )
            for p in corrected
        ]

        wall_tiles = walls.run(image, derived_pitch_px, derived_origin_px, placements=aligned)

        emit.run(
            placements=aligned,
            wall_tiles=wall_tiles,
            source_screenshot=str(screenshot_path),
            pitch=derived_pitch_px,
            origin=derived_origin_px,
            dataset_version=str(config["dataset_version"]),
            confidence_threshold=float(config["confidence_threshold"]),
            out_path=out_path,
            reviewed=True,
        )
        _shutdown.set()
        return JSONResponse(content={"status": "ok"})

    @app.get("/api/buildings")
    def get_buildings() -> Any:
        return _load_buildings()

    @app.get("/api/images/{filename}")
    def get_image(filename: str) -> Any:
        if filename != screenshot_path.name or not screenshot_path.exists():
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Image not found")
        return FileResponse(str(screenshot_path))

    return app


def _add_local_frontend_cors(app: Any) -> None:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
