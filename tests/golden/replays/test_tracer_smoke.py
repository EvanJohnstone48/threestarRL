"""Golden replay test for the Phase 0 tracer scenario.

Asserts byte-identical (after canonicalization) replay output for
`tracer.json` + `single_barb.json` against the committed fixture
`tracer_smoke.json`. Regenerate with `pytest --update-golden`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import sandbox_core
from sandbox_core.content import DEFAULT_DATA_DIR, load_catalogue
from sandbox_core.replay import compute_config_hash, replay_to_dict, serialize
from sandbox_core.schemas import BaseLayout, DeploymentPlan
from sandbox_core.sim import Sim

GOLDEN = Path(__file__).resolve().parent / "tracer_smoke.json"


def _produce_replay_dict() -> dict[str, object]:
    base_path = DEFAULT_DATA_DIR / "sample_bases" / "tracer.json"
    plan_path = DEFAULT_DATA_DIR / "sample_plans" / "single_barb.json"

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


def test_tracer_golden_replay(update_golden: bool) -> None:
    fresh = _produce_replay_dict()
    serialized = serialize(fresh, pretty=True)

    if update_golden or not GOLDEN.exists():
        GOLDEN.write_text(serialized, encoding="utf-8")
        if not GOLDEN.exists():
            pytest.fail(f"golden created: {GOLDEN}")
        return

    expected = GOLDEN.read_text(encoding="utf-8")
    if serialized != expected:
        # Surface a useful diff hint without blasting hundreds of frames.
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
            "tracer_smoke.json drift detected. Regenerate with `pytest --update-golden`. "
            f"first-divergence summary: {diff_keys}"
        )
