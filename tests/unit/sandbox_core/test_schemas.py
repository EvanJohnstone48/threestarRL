"""Tests for Pydantic schemas: validation rules, error cases, defaults."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from sandbox_core.schemas import (
    SCHEMA_VERSION,
    BaseLayout,
    BaseLayoutMetadata,
    BuildingPlacement,
    CartographerProvenance,
    DeploymentAction,
    DeploymentPlan,
    DeploymentPlanMetadata,
    Replay,
    ReplayMetadata,
    Score,
    TickFrame,
    WorldState,
    load_validated,
)


def _meta(name: str = "test") -> BaseLayoutMetadata:
    return BaseLayoutMetadata(name=name, th_level=6)


def test_schema_version_is_two() -> None:
    assert SCHEMA_VERSION == 2


def test_baselayout_th_level_consistency_required() -> None:
    with pytest.raises(ValidationError):
        BaseLayout(
            metadata=BaseLayoutMetadata(name="x", th_level=5),
            th_level=6,
            placements=[BuildingPlacement(building_type="town_hall", origin=(15, 15))],
        )


def test_baselayout_rejects_nonempty_cc_contents() -> None:
    with pytest.raises(ValidationError):
        BaseLayout(
            metadata=_meta(),
            th_level=6,
            placements=[BuildingPlacement(building_type="town_hall", origin=(15, 15))],
            cc_contents=["barbarian"],
        )


def test_deployment_plan_actions_must_be_sorted_by_tick() -> None:
    with pytest.raises(ValidationError):
        DeploymentPlan(
            metadata=DeploymentPlanMetadata(name="p"),
            actions=[
                DeploymentAction(
                    tick=10, kind="deploy_troop", entity_type="barbarian", position=(2.5, 2.5)
                ),
                DeploymentAction(
                    tick=5, kind="deploy_troop", entity_type="barbarian", position=(2.5, 2.5)
                ),
            ],
        )


def test_baselayout_v2_with_provenance_round_trips() -> None:
    provenance = CartographerProvenance(
        source_screenshot="bases/th6_01.png",
        ingest_timestamp_utc="2026-05-04T10:00:00Z",
        dataset_version="1",
        confidence_threshold=0.5,
        derived_pitch_px=32.0,
        derived_origin_px=(100.0, 200.0),
        per_placement_confidence={"0": 0.92, "1": 0.85},
    )
    layout = BaseLayout(
        metadata=_meta(),
        th_level=6,
        placements=[BuildingPlacement(building_type="town_hall", origin=(15, 15))],
        provenance=provenance,
    )
    assert layout.schema_version == 2
    recovered = BaseLayout.model_validate_json(layout.model_dump_json())
    assert recovered.provenance is not None
    assert recovered.provenance.source_screenshot == "bases/th6_01.png"
    assert recovered.provenance.derived_origin_px == (100.0, 200.0)


def test_baselayout_v1_loads_via_migration() -> None:
    v1_payload = {
        "schema_version": 1,
        "metadata": {"name": "old", "th_level": 6, "tags": [], "notes": None, "author": "", "created_at": ""},
        "th_level": 6,
        "placements": [{"building_type": "town_hall", "origin": [15, 15], "level": None}],
        "cc_contents": [],
    }
    layout = load_validated(v1_payload, BaseLayout)
    assert layout.schema_version == 2
    assert layout.provenance is None


def test_baselayout_v2_provenance_none_is_valid() -> None:
    layout = BaseLayout(
        metadata=_meta(),
        th_level=6,
        placements=[],
        provenance=None,
    )
    assert layout.provenance is None
    assert layout.schema_version == 2


def test_replay_round_trip_through_json() -> None:
    score = Score(stars=0, destruction_pct=0.0, ticks_elapsed=0, town_hall_destroyed=False)
    state = WorldState(tick=0, buildings=[], troops=[], score=score)
    frame = TickFrame(tick=0, state=state, events=[])
    rmeta = ReplayMetadata(
        sim_version="0.1.0",
        base_name="b",
        plan_name="p",
        total_ticks=1,
        final_score=score,
    )
    replay = Replay(metadata=rmeta, initial_state=state, frames=[frame])

    raw = replay.model_dump_json()
    recovered = Replay.model_validate_json(raw)
    assert recovered.metadata.total_ticks == 1
    assert recovered.frames[0].tick == 0
