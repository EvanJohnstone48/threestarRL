"""Golden replay test for the issue 005 Mortar splash scenario.

Asserts byte-identical replay output for `mortar_splash.json` (base + plan).
The recorded scenario AC: a single Mortar projectile splash damages
3+ clustered Barbarians in one impact. Regenerate with
`pytest --update-golden`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import sandbox_core
from sandbox_core.content import DEFAULT_DATA_DIR, load_catalogue
from sandbox_core.replay import compute_config_hash, replay_to_dict, serialize
from sandbox_core.schemas import AttackKind, BaseLayout, DeploymentPlan, EventType, load_validated
from sandbox_core.sim import Sim

GOLDEN = Path(__file__).resolve().parent / "mortar_splash.json"


def _produce_replay_dict() -> dict[str, object]:
    base_path = DEFAULT_DATA_DIR / "sample_bases" / "mortar_splash.json"
    plan_path = DEFAULT_DATA_DIR / "sample_plans" / "mortar_splash.json"

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


def test_mortar_splash_golden_replay(update_golden: bool) -> None:
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
            "mortar_splash.json drift detected. Regenerate with `pytest --update-golden`. "
            f"first-divergence summary: {diff_keys}"
        )


def test_mortar_splash_kills_three_or_more_in_single_impact() -> None:
    """AC-S1.3: Mortar splash damages 3+ clustered Barbarians in one impact."""
    from typing import Any, cast

    fresh = _produce_replay_dict()
    splash_hits_per_tick: dict[int, int] = {}
    frames = cast(list[dict[str, Any]], fresh["frames"])
    for frame in frames:
        events = cast(list[dict[str, Any]], frame["events"])
        for ev in events:
            payload = cast(dict[str, Any], ev["payload"])
            if (
                ev["type"] == EventType.DAMAGE.value
                and payload.get("kind") == AttackKind.RANGED.value
            ):
                t = cast(int, ev["tick"])
                splash_hits_per_tick[t] = splash_hits_per_tick.get(t, 0) + 1
    multi_hit_ticks = [t for t, n in splash_hits_per_tick.items() if n >= 3]
    assert multi_hit_ticks, (
        f"AC violated: expected >= 1 tick with 3+ Mortar splash damage events; "
        f"got per-tick counts: {splash_hits_per_tick}"
    )
