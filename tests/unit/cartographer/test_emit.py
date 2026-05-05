"""Tests for cartographer.emit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _make_placement(class_name: str = "town_hall", origin=(0, 0), confidence=1.0):
    from cartographer.align import AlignedPlacement

    return AlignedPlacement(class_name=class_name, origin=origin, footprint=(4, 4), confidence=confidence)


def test_run_writes_json_and_returns_layout(tmp_path: Path) -> None:
    from cartographer.emit import run
    from sandbox_core.schemas import BaseLayout

    out = tmp_path / "out.json"
    layout = run(
        placements=[_make_placement()],
        wall_tiles=[],
        source_screenshot="test.png",
        pitch=64.0,
        origin=(100.0, 100.0),
        dataset_version="1",
        confidence_threshold=0.5,
        out_path=out,
    )
    assert isinstance(layout, BaseLayout)
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["schema_version"] == 3
    assert data["provenance"] is not None


def test_provenance_fields_populated(tmp_path: Path) -> None:
    from cartographer.emit import run

    out = tmp_path / "out.json"
    layout = run(
        placements=[_make_placement(confidence=0.87)],
        wall_tiles=[],
        source_screenshot="foo/bar.png",
        pitch=32.0,
        origin=(50.0, 60.0),
        dataset_version="2",
        confidence_threshold=0.5,
        out_path=out,
    )
    prov = layout.provenance
    assert prov is not None
    assert prov.source_screenshot == "foo/bar.png"
    assert prov.derived_pitch_px == 32.0
    assert prov.derived_origin_px == (50.0, 60.0)
    assert prov.dataset_version == "2"
