"""Golden replay test for the issue 008 Wizard splash walls scenario.

Asserts byte-identical replay output for `wizard_splash_walls.json` (base + plan).
The recorded scenario AC: a Wizard fires at a Gold Mine while two walls sit at
exactly 2.0 tiles from the Gold Mine's footprint center; each projectile impact
splashes both walls progressively until they are destroyed. Regenerate with
`pytest --update-golden`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
import sandbox_core
from sandbox_core.content import DEFAULT_DATA_DIR, load_catalogue
from sandbox_core.replay import compute_config_hash, replay_to_dict, serialize
from sandbox_core.schemas import AttackKind, BaseLayout, DeploymentPlan, EventType, load_validated
from sandbox_core.sim import Sim

GOLDEN = Path(__file__).resolve().parent / "wizard_splash_walls.json"


def _produce_replay_dict() -> dict[str, object]:
    base_path = DEFAULT_DATA_DIR / "sample_bases" / "wizard_splash_walls.json"
    plan_path = DEFAULT_DATA_DIR / "sample_plans" / "wizard_splash_walls.json"

    base_raw = json.loads(base_path.read_text(encoding="utf-8"))
    plan_raw = json.loads(plan_path.read_text(encoding="utf-8"))

    base = load_validated(base_raw, BaseLayout)
    plan = load_validated(plan_raw, DeploymentPlan)

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


def test_wizard_splash_walls_golden_replay(update_golden: bool) -> None:
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
            "wizard_splash_walls.json drift detected. Regenerate with `pytest --update-golden`. "
            f"first-divergence summary: {diff_keys}"
        )


def test_wizard_splash_walls_at_least_one_wall_takes_damage() -> None:
    """AC-S1.3: Wizard splash damages walls adjacent to its target."""
    fresh = _produce_replay_dict()
    frames = cast(list[dict[str, Any]], fresh["frames"])

    wall_damage_events: list[dict[str, Any]] = []

    for frame in frames:
        events = cast(list[dict[str, Any]], frame["events"])
        for ev in events:
            if ev["type"] != EventType.DAMAGE.value:
                continue
            payload = cast(dict[str, Any], ev["payload"])
            if payload.get("kind") != AttackKind.RANGED.value:
                continue
            # The attacker is the wizard (a troop); walls are buildings in the base.
            # We flag any ranged damage event whose target_id matches a wall entity.
            wall_damage_events.append(payload)

    # Also verify at least two walls were destroyed.
    destroyed_walls = 0
    for frame in frames:
        events = cast(list[dict[str, Any]], frame["events"])
        for ev in events:
            if ev["type"] == EventType.DESTROYED.value:
                payload = cast(dict[str, Any], ev["payload"])
                if payload.get("kind") == "building":
                    bt = payload.get("building_type", "")
                    if bt == "wall":
                        destroyed_walls += 1

    assert wall_damage_events, (
        "AC violated: no ranged DAMAGE events found — Wizard splash did not emit any events. "
        "Check wizard.splash_damages_walls=True and splash_radius_tiles>=2.0."
    )
    assert destroyed_walls >= 1, (
        f"AC violated: expected at least 1 wall destroyed by Wizard splash, got {destroyed_walls}"
    )


def test_wizard_splash_walls_progressive_damage_on_multiple_shots() -> None:
    """Multiple Wizard shots produce multiple wall damage events (progressive damage)."""
    fresh = _produce_replay_dict()
    frames = cast(list[dict[str, Any]], fresh["frames"])

    # Count distinct ticks that have ranged DAMAGE events (splash from Wizard shots).
    damage_ticks: set[int] = set()
    for frame in frames:
        events = cast(list[dict[str, Any]], frame["events"])
        for ev in events:
            if ev["type"] == EventType.DAMAGE.value:
                payload = cast(dict[str, Any], ev["payload"])
                if payload.get("kind") == AttackKind.RANGED.value:
                    damage_ticks.add(cast(int, ev["tick"]))

    assert len(damage_ticks) >= 3, (
        f"AC violated: expected ≥3 ticks with ranged damage events (progressive damage), "
        f"got {len(damage_ticks)} ticks: {sorted(damage_ticks)}"
    )
