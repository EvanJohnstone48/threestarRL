"""Tests for cartographer.calibration — CalibrationFile model and load_offsets."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def reset_warned(monkeypatch: pytest.MonkeyPatch) -> None:
    import cartographer.calibration as cal_mod

    monkeypatch.setattr(cal_mod, "_warned", set())


def _write_valid(tmp_path: Path, dataset_version: str = "1") -> Path:
    p = tmp_path / "cartographer_calibration.json"
    p.write_text(
        json.dumps(
            {
                "dataset_version": dataset_version,
                "offsets": {"cannon": [0.0, -3.5], "archer_tower": [0.0, -8.2]},
                "calibrated_at_utc": "2026-05-05T12:34:56Z",
                "sample_counts": {"cannon": 12, "archer_tower": 7},
            }
        ),
        encoding="utf-8",
    )
    return p


# ---------------------------------------------------------------------------
# 1. Missing file → {}
# ---------------------------------------------------------------------------


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    from cartographer.calibration import load_offsets

    missing = tmp_path / "cartographer_calibration.json"
    result = load_offsets("1", _path=missing)
    assert result == {}


def test_missing_file_logs_warning(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    from cartographer.calibration import load_offsets

    missing = tmp_path / "cartographer_calibration.json"
    with caplog.at_level(logging.WARNING, logger="cartographer"):
        load_offsets("1", _path=missing)

    assert any("no calibration file found" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# 2. Malformed JSON → {}
# ---------------------------------------------------------------------------


def test_malformed_json_returns_empty(tmp_path: Path) -> None:
    from cartographer.calibration import load_offsets

    p = tmp_path / "cartographer_calibration.json"
    p.write_text("{not valid json", encoding="utf-8")
    result = load_offsets("1", _path=p)
    assert result == {}


def test_malformed_json_logs_warning(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    from cartographer.calibration import load_offsets

    p = tmp_path / "cartographer_calibration.json"
    p.write_text("{not valid json", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="cartographer"):
        load_offsets("1", _path=p)

    assert any("malformed" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# 3. Valid JSON but fails Pydantic validation → {}
# ---------------------------------------------------------------------------


def test_pydantic_invalid_returns_empty(tmp_path: Path) -> None:
    from cartographer.calibration import load_offsets

    p = tmp_path / "cartographer_calibration.json"
    p.write_text(json.dumps({"dataset_version": "1"}), encoding="utf-8")  # missing required fields
    result = load_offsets("1", _path=p)
    assert result == {}


# ---------------------------------------------------------------------------
# 4. Version mismatch → {}
# ---------------------------------------------------------------------------


def test_version_mismatch_returns_empty(tmp_path: Path) -> None:
    from cartographer.calibration import load_offsets

    p = _write_valid(tmp_path, dataset_version="1")
    result = load_offsets("2", _path=p)
    assert result == {}


def test_version_mismatch_logs_warning(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    from cartographer.calibration import load_offsets

    p = _write_valid(tmp_path, dataset_version="1")
    with caplog.at_level(logging.WARNING, logger="cartographer"):
        load_offsets("2", _path=p)

    assert any("dataset_version" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# 5. Valid file, version match → correct dict
# ---------------------------------------------------------------------------


def test_valid_returns_correct_offsets(tmp_path: Path) -> None:
    from cartographer.calibration import load_offsets

    p = _write_valid(tmp_path, dataset_version="1")
    result = load_offsets("1", _path=p)
    assert result == {"cannon": (0.0, -3.5), "archer_tower": (0.0, -8.2)}


def test_valid_logs_info(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    from cartographer.calibration import load_offsets

    p = _write_valid(tmp_path, dataset_version="1")
    with caplog.at_level(logging.INFO, logger="cartographer"):
        load_offsets("1", _path=p)

    assert any("loaded calibration" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# 6. Pydantic round-trip
# ---------------------------------------------------------------------------


def test_calibration_file_round_trip() -> None:
    from cartographer.calibration import CalibrationFile

    raw = {
        "dataset_version": "2",
        "offsets": {"mortar": [1.5, -2.0]},
        "calibrated_at_utc": "2026-01-01T00:00:00Z",
        "sample_counts": {"mortar": 5},
    }
    cal = CalibrationFile.model_validate(raw)
    assert cal.dataset_version == "2"
    assert cal.offsets["mortar"] == (1.5, -2.0)
    dumped = cal.model_dump()
    cal2 = CalibrationFile.model_validate(dumped)
    assert cal2 == cal


# ---------------------------------------------------------------------------
# 7. One-warning-per-process dedup
# ---------------------------------------------------------------------------


def test_repeated_missing_logs_only_once(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    from cartographer.calibration import load_offsets

    missing = tmp_path / "cartographer_calibration.json"
    with caplog.at_level(logging.WARNING, logger="cartographer"):
        load_offsets("1", _path=missing)
        load_offsets("1", _path=missing)
        load_offsets("1", _path=missing)

    warning_count = sum(1 for r in caplog.records if "no calibration file found" in r.message)
    assert warning_count == 1
