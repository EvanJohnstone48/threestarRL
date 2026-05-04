"""Golden replay test for the issue 007 Wall Breaker breach scenario.

Asserts byte-identical replay output for `wall_breaker_breach.json` (base + plan).
AC: WB suicides on wall, destroys it and adjacent walls via splash; follow-up
Goblin walks through the breach and destroys the TH (3 stars).
Regenerate with `pytest --update-golden`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
import sandbox_core
from sandbox_core.content import DEFAULT_DATA_DIR, load_catalogue
from sandbox_core.replay import compute_config_hash, replay_to_dict, serialize
from sandbox_core.schemas import BaseLayout, DeploymentPlan, EventType
from sandbox_core.sim import Sim

GOLDEN = Path(__file__).resolve().parent / "wall_breaker_breach.json"


def _produce_replay_dict() -> dict[str, object]:
    base_path = DEFAULT_DATA_DIR / "sample_bases" / "wall_breaker_breach.json"
    plan_path = DEFAULT_DATA_DIR / "sample_plans" / "wall_breaker_breach.json"

    base_raw = json.loads(base_path.read_text(encoding="utf-8"))
    plan_raw = json.loads(plan_path.read_text(encoding="utf-8"))

    base = BaseLayout.model_validate(base_raw)
    plan = DeploymentPlan.model_validate(plan_raw)

    catalogue = load_catalogue()
    config_hash = compute_config_hash(
        base_raw,
        plan_raw,
        json.loads((DEFAULT_DATA_DIR / "buildings.json").read_text(encoding="utf-8")),
        json.loads((DEFAULT_DATA_DIR / "troops.json").read_text(encoding="utf-8")),
    )

    sim = Sim(
        base,
        plan,
        catalogue_buildings=catalogue.buildings,
        catalogue_troops=catalogue.troops,
        sim_version=sandbox_core.__version__,
        config_hash=config_hash,
    )
    sim.run_until_termination()
    replay = sim.to_replay(base_name=base.metadata.name, plan_name=plan.metadata.name)
    return replay_to_dict(replay)


def test_wall_breaker_breach_golden_replay(update_golden: bool) -> None:
    fresh = _produce_replay_dict()
    serialized = serialize(fresh, pretty=True)

    if update_golden or not GOLDEN.exists():
        GOLDEN.write_text(serialized, encoding="utf-8")
        if not GOLDEN.exists():
            pytest.fail(f"golden created: {GOLDEN}")
        return

    expected = GOLDEN.read_text(encoding="utf-8")
    if serialized != expected:
        expected_obj = json.loads(expected)
        diff_keys: list[str] = []
        if expected_obj.get("metadata") != fresh.get("metadata"):
            diff_keys.append("metadata")
        if len(expected_obj.get("frames", [])) != len(fresh.get("frames", [])):  # type: ignore[arg-type]
            diff_keys.append(
                f"frame_count: expected={len(expected_obj.get('frames', []))} "
                f"got={len(fresh.get('frames', []))}"  # type: ignore[arg-type]
            )
        pytest.fail(
            "wall_breaker_breach.json drift detected. Regenerate with `pytest --update-golden`. "
            f"first-divergence summary: {diff_keys}"
        )


def test_wb_suicide_destroys_target_wall_and_adjacent_walls() -> None:
    """AC: WB suicides and destroys 3 walls (direct hit + 2 splash within 1.5 tiles)."""
    fresh = _produce_replay_dict()
    frames = cast(list[dict[str, Any]], fresh["frames"])

    # Find which walls were destroyed (look in the final frame state).
    final_buildings = cast(list[dict[str, Any]], frames[-1]["state"]["buildings"])
    walls = [b for b in final_buildings if b["building_type"] == "wall"]
    destroyed_walls = [b for b in walls if b["destroyed"]]

    assert len(destroyed_walls) >= 2, (
        f"WB suicide should destroy the target wall + at least 1 adjacent wall; "
        f"got {len(destroyed_walls)} destroyed out of {len(walls)} walls"
    )


def test_wb_is_destroyed_after_suicide() -> None:
    """AC: WB troop has destroyed=True after suicide."""
    fresh = _produce_replay_dict()
    frames = cast(list[dict[str, Any]], fresh["frames"])

    wb_destroyed_events = [
        e
        for f in frames
        for e in cast(list[dict[str, Any]], f["events"])
        if e["type"] == EventType.DESTROYED.value
        and cast(dict[str, Any], e["payload"]).get("troop_type") == "wall_breaker"
    ]
    assert wb_destroyed_events, "WB must emit a DESTROYED event after suicide"


def test_goblin_reaches_th_and_episode_achieves_at_least_one_star() -> None:
    """AC: Follow-up Goblin destroys TH; episode reaches >= 1 star."""
    fresh = _produce_replay_dict()
    meta = cast(dict[str, Any], fresh["metadata"])
    assert meta["final_score"]["town_hall_destroyed"] is True, (
        "Goblin should destroy the TH after passing through the breach"
    )
    assert meta["final_score"]["stars"] >= 1, (
        f"Expected >= 1 star; got {meta['final_score']['stars']}"
    )
