"""Calibration file format and loader for the align stage.

Design rationale: calibration is advisory. The loader never raises — it returns
{} on any problem (missing file, malformed JSON, schema error, version mismatch)
and logs a single warning per process. This means a missing or stale calibration
file can never block an ingest run; zero offsets are used instead.

No CI freshness check is intentional: the calibration file is authored by
humans during the cartographer calibrate workflow (issue 034) and re-authored
when the Roboflow dataset_version changes.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

_logger = logging.getLogger("cartographer")

_CALIBRATION_PATH = Path(__file__).parent.parent / "data" / "cartographer_calibration.json"

_warned: set[str] = set()


class CalibrationSample(BaseModel):
    class_name: str
    offset: tuple[float, float]


class CalibrationFile(BaseModel):
    dataset_version: str
    offsets: dict[str, tuple[float, float]]
    calibrated_at_utc: str
    sample_counts: dict[str, int]
    samples: list[CalibrationSample] = Field(default_factory=list)


def load_offsets(
    config_dataset_version: str,
    _path: Path | None = None,
) -> dict[str, tuple[float, float]]:
    """Return per-class pixel offsets from the calibration file.

    Falls back to {} (zero offsets) on any error, logging at most one warning
    per process per failure mode.
    """
    path = _path if _path is not None else _CALIBRATION_PATH

    if not path.exists():
        key = f"missing:{path}"
        if key not in _warned:
            _warned.add(key)
            _logger.warning(
                "cartographer: no calibration file found at %s, using zero offsets",
                path,
            )
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        key = f"malformed:{path}"
        if key not in _warned:
            _warned.add(key)
            _logger.warning(
                "cartographer: calibration file at %s is malformed (%s), using zero offsets",
                path,
                exc,
            )
        return {}

    try:
        cal = CalibrationFile.model_validate(data)
    except ValidationError as exc:
        key = f"malformed:{path}"
        if key not in _warned:
            _warned.add(key)
            _logger.warning(
                "cartographer: calibration file at %s is malformed (%s), using zero offsets",
                path,
                exc,
            )
        return {}

    if cal.dataset_version != config_dataset_version:
        key = f"version:{path}:{cal.dataset_version}:{config_dataset_version}"
        if key not in _warned:
            _warned.add(key)
            _logger.warning(
                "cartographer: calibration is for dataset_version %s, current is %s, using zero offsets",
                cal.dataset_version,
                config_dataset_version,
            )
        return {}

    _logger.info(
        "cartographer: loaded calibration for %d classes (dataset_version %s)",
        len(cal.offsets),
        cal.dataset_version,
    )
    return dict(cal.offsets)
