"""Byte-determinism regression test for sandbox-core.

For each registered (base, plan) scenario, instantiate two fresh `Sim`s, run
both to termination, and assert the produced replays serialize to identical
JSON. Also asserts matching `config_hash`. Catches regressions caused by
accidental dict-iteration-order, set ordering, RNG slips, or floating-point
non-determinism.

Marked `slow` so it stays out of pre-commit; CI runs the full suite.

Scenario registry: each (base, plan) sample pair from `app/data/sample_*` is
appended as it lands. To add a new scenario, drop one line in `SCENARIOS` —
no other test changes required.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pytest
import sandbox_core
from sandbox_core.content import DEFAULT_DATA_DIR, load_catalogue, load_th_caps
from sandbox_core.replay import compute_config_hash, replay_to_dict, serialize
from sandbox_core.schemas import BaseLayout, DeploymentPlan
from sandbox_core.sim import Sim


@dataclass(frozen=True)
class Scenario:
    name: str
    base_path: Path
    plan_path: Path


SAMPLE_BASES = DEFAULT_DATA_DIR / "sample_bases"
SAMPLE_PLANS = DEFAULT_DATA_DIR / "sample_plans"

SCENARIOS: list[Scenario] = [
    Scenario(
        name="tracer_smoke",
        base_path=SAMPLE_BASES / "tracer.json",
        plan_path=SAMPLE_PLANS / "single_barb.json",
    ),
    Scenario(
        name="mortar_splash",
        base_path=SAMPLE_BASES / "mortar_splash.json",
        plan_path=SAMPLE_PLANS / "mortar_splash.json",
    ),
    Scenario(
        name="wall_breaker_breach",
        base_path=SAMPLE_BASES / "wall_breaker_breach.json",
        plan_path=SAMPLE_PLANS / "wall_breaker_breach.json",
    ),
    Scenario(
        name="wizard_splash_walls",
        base_path=SAMPLE_BASES / "wizard_splash_walls.json",
        plan_path=SAMPLE_PLANS / "wizard_splash_walls.json",
    ),
    Scenario(
        name="lightning_destroys_mortar",
        base_path=SAMPLE_BASES / "lightning_destroys_mortar.json",
        plan_path=SAMPLE_PLANS / "lightning_destroys_mortar.json",
    ),
    Scenario(
        name="full_th6_attack",
        base_path=SAMPLE_BASES / "full_th6_attack.json",
        plan_path=SAMPLE_PLANS / "full_th6_attack.json",
    ),
]

MAX_DIFF_PATHS: int = 20


def _run_scenario(scenario: Scenario) -> tuple[dict[str, Any], str]:
    """Build a fresh Sim from disk inputs, run to termination, return
    (canonical replay dict, config_hash).
    """
    base_raw = json.loads(scenario.base_path.read_text(encoding="utf-8"))
    plan_raw = json.loads(scenario.plan_path.read_text(encoding="utf-8"))

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
    return replay_to_dict(replay), config_hash


def _diff_paths(a: Any, b: Any, path: str = "$", out: list[str] | None = None) -> list[str]:
    """Return up to MAX_DIFF_PATHS dotted paths where `a` and `b` differ.

    Reports the first divergence per branch — does not exhaustively descend
    into mismatched containers.
    """
    if out is None:
        out = []
    if len(out) >= MAX_DIFF_PATHS:
        return out
    if type(a) is not type(b):
        out.append(f"{path}: type mismatch ({type(a).__name__} vs {type(b).__name__})")
        return out
    if isinstance(a, dict):
        a_dict = cast(dict[str, Any], a)
        b_dict = cast(dict[str, Any], b)
        keys_a: set[str] = set(a_dict.keys())
        keys_b: set[str] = set(b_dict.keys())
        for k in sorted(keys_a - keys_b):
            if len(out) >= MAX_DIFF_PATHS:
                return out
            out.append(f"{path}.{k}: present in run-1 only")
        for k in sorted(keys_b - keys_a):
            if len(out) >= MAX_DIFF_PATHS:
                return out
            out.append(f"{path}.{k}: present in run-2 only")
        for k in sorted(keys_a & keys_b):
            if len(out) >= MAX_DIFF_PATHS:
                return out
            _diff_paths(a_dict[k], b_dict[k], f"{path}.{k}", out)
        return out
    if isinstance(a, list):
        a_list = cast(list[Any], a)
        b_list = cast(list[Any], b)
        if len(a_list) != len(b_list):
            out.append(f"{path}: length differs ({len(a_list)} vs {len(b_list)})")
            return out
        for i, (av, bv) in enumerate(zip(a_list, b_list, strict=True)):
            if len(out) >= MAX_DIFF_PATHS:
                return out
            _diff_paths(av, bv, f"{path}[{i}]", out)
        return out
    if a != b:
        out.append(f"{path}: {a!r} != {b!r}")
    return out


@pytest.mark.slow
@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_replay_byte_deterministic(scenario: Scenario) -> None:
    """Two fresh Sim runs of the same (base, plan) must produce byte-identical
    replays and matching config_hashes."""
    replay_a, hash_a = _run_scenario(scenario)
    replay_b, hash_b = _run_scenario(scenario)

    assert hash_a == hash_b, (
        f"[{scenario.name}] config_hash mismatch across runs: {hash_a} vs {hash_b}"
    )

    serialized_a = serialize(replay_a, pretty=True)
    serialized_b = serialize(replay_b, pretty=True)

    if serialized_a != serialized_b:
        diffs = _diff_paths(replay_a, replay_b)
        formatted = "\n  ".join(diffs) if diffs else "(no structural diff — pure string drift?)"
        pytest.fail(
            f"[{scenario.name}] non-determinism detected. "
            f"First {len(diffs)} differing field paths:\n  {formatted}"
        )
