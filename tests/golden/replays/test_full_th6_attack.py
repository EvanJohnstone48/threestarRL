"""Golden replay test for the issue 010 capstone integrative scenario.

Asserts byte-identical replay output for `full_th6_attack.json` (base + plan).
The recorded scenario AC: a full TH6 base + scripted attack using all six
troop types and at least one Lightning cast reaches >=50% destruction (>=1
star) reliably under the placeholder pathing. Regenerate with
`pytest --update-golden`.

Includes an in-test byte-determinism subassertion: the sim is run twice
and the produced replays are compared. The broader determinism regression
(`tests/integration/test_replay_determinism.py`) covers the same property
across the corpus; this test asserts it specifically for the integrative
scenario.
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

GOLDEN = Path(__file__).resolve().parent / "full_th6_attack.json"


def _produce_replay_dict() -> dict[str, object]:
    base_path = DEFAULT_DATA_DIR / "sample_bases" / "full_th6_attack.json"
    plan_path = DEFAULT_DATA_DIR / "sample_plans" / "full_th6_attack.json"

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


def test_full_th6_attack_golden_replay(update_golden: bool) -> None:
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
            "full_th6_attack.json drift detected. Regenerate with `pytest --update-golden`. "
            f"first-divergence summary: {diff_keys}"
        )


def test_full_th6_attack_byte_deterministic_within_test() -> None:
    """Per-issue-010 AC: rerunning the integrative sim produces a byte-identical replay.

    This is in addition to the broader determinism regression test in
    `tests/integration/test_replay_determinism.py` — it asserts the
    integrative scenario specifically.
    """
    a = _produce_replay_dict()
    b = _produce_replay_dict()
    serialized_a = serialize(a, pretty=True)
    serialized_b = serialize(b, pretty=True)
    assert serialized_a == serialized_b, (
        "full_th6_attack non-determinism: two runs produced different replays"
    )
    meta_a = cast(dict[str, Any], a["metadata"])
    meta_b = cast(dict[str, Any], b["metadata"])
    assert meta_a["config_hash"] == meta_b["config_hash"], (
        f"config_hash mismatch across runs: {meta_a['config_hash']} vs {meta_b['config_hash']}"
    )


def test_full_th6_attack_reaches_at_least_50_percent_destruction() -> None:
    """AC: final score has >=50% destruction and >=1 star."""
    fresh = _produce_replay_dict()
    meta = cast(dict[str, Any], fresh["metadata"])
    final_score = cast(dict[str, Any], meta["final_score"])
    assert final_score["destruction_pct"] >= 50.0, (
        f"AC violated: expected destruction_pct >= 50, got {final_score['destruction_pct']}"
    )
    assert final_score["stars"] >= 1, (
        f"AC violated: expected stars >= 1, got {final_score['stars']}"
    )


def test_full_th6_attack_uses_all_six_troop_types() -> None:
    """AC: plan deploys all six TH6 troop types."""
    fresh = _produce_replay_dict()
    frames = cast(list[dict[str, Any]], fresh["frames"])
    deployed_types: set[str] = set()
    for frame in frames:
        events = cast(list[dict[str, Any]], frame["events"])
        for ev in events:
            if ev["type"] == EventType.DEPLOY.value:
                payload = cast(dict[str, Any], ev["payload"])
                deployed_types.add(cast(str, payload["troop_type"]))
    expected = {"barbarian", "archer", "goblin", "giant", "wall_breaker", "wizard"}
    missing = expected - deployed_types
    assert not missing, f"AC violated: missing troop types in deploys: {sorted(missing)}"


def test_full_th6_attack_casts_at_least_one_lightning() -> None:
    """AC: plan casts at least one Lightning spell."""
    fresh = _produce_replay_dict()
    frames = cast(list[dict[str, Any]], fresh["frames"])
    lightning_casts = sum(
        1
        for frame in frames
        for ev in cast(list[dict[str, Any]], frame["events"])
        if ev["type"] == EventType.SPELL_CAST.value
        and cast(dict[str, Any], ev["payload"]).get("spell_type") == "lightning_spell"
    )
    assert lightning_casts >= 1, f"AC violated: expected >=1 Lightning cast, got {lightning_casts}"
