"""Golden replay test for the issue 009 Lightning Spell scenario.

Asserts byte-identical replay output for `lightning_destroys_mortar.json`.

Scenario: Two Lightning level-3 casts (at tick 0 and tick 6) centered on a
Mortar at (25,25). 10 bolts x 42 dmg = 420 total > 400 HP; Mortar destroyed.
A wall at (24,28) is inside the 3-tile radius but takes zero damage because
Lightning target_filter=all_except_walls. Regenerate with `pytest --update-golden`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
import sandbox_core
from sandbox_core.content import DEFAULT_DATA_DIR, load_catalogue, load_th_caps
from sandbox_core.replay import compute_config_hash, replay_to_dict, serialize
from sandbox_core.schemas import BaseLayout, DeploymentPlan, EventType
from sandbox_core.sim import Sim

GOLDEN = Path(__file__).resolve().parent / "lightning_destroys_mortar.json"


def _produce_replay_dict() -> dict[str, object]:
    base_path = DEFAULT_DATA_DIR / "sample_bases" / "lightning_destroys_mortar.json"
    plan_path = DEFAULT_DATA_DIR / "sample_plans" / "lightning_destroys_mortar.json"

    base_raw = json.loads(base_path.read_text(encoding="utf-8"))
    plan_raw = json.loads(plan_path.read_text(encoding="utf-8"))

    base = BaseLayout.model_validate(base_raw)
    plan = DeploymentPlan.model_validate(plan_raw)

    catalogue = load_catalogue()
    th_caps = load_th_caps()
    spell_capacity_total = th_caps[base.th_level]["spell_capacity_total"]

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
        catalogue_spells=catalogue.spells,
        spell_capacity_total=spell_capacity_total,
        sim_version=sandbox_core.__version__,
        config_hash=config_hash,
    )
    sim.run_until_termination()
    replay = sim.to_replay(base_name=base.metadata.name, plan_name=plan.metadata.name)
    return replay_to_dict(replay)


def test_lightning_destroys_mortar_golden_replay(update_golden: bool) -> None:
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
            "lightning_destroys_mortar.json drift detected. Regenerate with `pytest --update-golden`. "
            f"first-divergence summary: {diff_keys}"
        )


def test_mortar_is_destroyed_by_lightning() -> None:
    """AC: Lightning bolts destroy the Mortar (HP reduced to 0)."""
    fresh = _produce_replay_dict()
    frames = cast(list[dict[str, Any]], fresh["frames"])

    mortar_destroyed = any(
        ev["type"] == EventType.DESTROYED.value
        and cast(dict[str, Any], ev["payload"]).get("building_type") == "mortar"
        for frame in frames
        for ev in cast(list[dict[str, Any]], frame["events"])
    )
    assert mortar_destroyed, (
        "AC violated: Mortar was not destroyed. "
        "Check Lightning level-3 damage (42/bolt x 10 bolts = 420 > 400 HP)."
    )


def test_wall_in_radius_takes_no_damage() -> None:
    """AC: Wall within the 3-tile Lightning radius takes zero damage (target_filter=all_except_walls)."""
    fresh = _produce_replay_dict()
    frames = cast(list[dict[str, Any]], fresh["frames"])
    initial_state = cast(dict[str, Any], fresh["initial_state"])

    # Find wall entity ID from initial state.
    buildings = cast(list[dict[str, Any]], initial_state["buildings"])
    wall_ids = {b["id"] for b in buildings if b["building_type"] == "wall"}
    assert wall_ids, "Expected at least one wall in the base"

    wall_damage_events = [
        ev
        for frame in frames
        for ev in cast(list[dict[str, Any]], frame["events"])
        if ev["type"] == EventType.DAMAGE.value
        and cast(dict[str, Any], ev["payload"]).get("target_id") in wall_ids
    ]
    assert wall_damage_events == [], (
        f"AC violated: wall received {len(wall_damage_events)} DAMAGE event(s) from Lightning. "
        "Lightning target_filter=all_except_walls should prevent wall damage."
    )
