"""Performance benchmark: full TH6 replay serialization size.

Runs the full_th6_attack scenario, serializes the replay in both pretty and
minified modes, and asserts §12.1 budgets: pretty ≤ 3 MB, minified ≤ 1.5 MB.
"""

from __future__ import annotations

import json

import pytest
import sandbox_core
from sandbox_core.content import DEFAULT_DATA_DIR, load_catalogue, load_th_caps
from sandbox_core.replay import compute_config_hash, replay_to_dict, serialize
from sandbox_core.schemas import BaseLayout, DeploymentPlan
from sandbox_core.sim import Sim

from ._common import save_result

THRESHOLD_PRETTY_BYTES = 3 * 1024 * 1024  # 3 MB
THRESHOLD_MINIFIED_BYTES = int(1.5 * 1024 * 1024)  # 1.5 MB

_BASE_PATH = DEFAULT_DATA_DIR / "sample_bases" / "full_th6_attack.json"
_PLAN_PATH = DEFAULT_DATA_DIR / "sample_plans" / "full_th6_attack.json"
_BUILDINGS_PATH = DEFAULT_DATA_DIR / "buildings.json"
_TROOPS_PATH = DEFAULT_DATA_DIR / "troops.json"


def _run_sim() -> Sim:
    base_raw = json.loads(_BASE_PATH.read_text(encoding="utf-8"))
    plan_raw = json.loads(_PLAN_PATH.read_text(encoding="utf-8"))

    base = BaseLayout.model_validate(base_raw)
    plan = DeploymentPlan.model_validate(plan_raw)

    catalogue = load_catalogue()
    th_caps = load_th_caps()

    config_hash = compute_config_hash(
        base_raw,
        plan_raw,
        json.loads(_BUILDINGS_PATH.read_text(encoding="utf-8")),
        json.loads(_TROOPS_PATH.read_text(encoding="utf-8")),
    )

    sim = Sim(
        base,
        plan,
        catalogue_buildings=catalogue.buildings,
        catalogue_troops=catalogue.troops,
        catalogue_spells=catalogue.spells,
        spell_capacity_total=th_caps[base.th_level]["spell_capacity_total"],
        sim_version=sandbox_core.__version__,
        config_hash=config_hash,
    )
    sim.run_until_termination()
    return sim


@pytest.mark.slow
def test_replay_size_full_th6() -> None:
    sim = _run_sim()
    replay = sim.to_replay(base_name="full_th6_attack", plan_name="full_th6_attack")
    payload = replay_to_dict(replay)

    pretty_bytes = len(serialize(payload, pretty=True).encode("utf-8"))
    minified_bytes = len(serialize(payload, pretty=False).encode("utf-8"))

    save_result(
        "replay_size_full_th6",
        scenario="full_th6_attack",
        pretty_bytes=pretty_bytes,
        minified_bytes=minified_bytes,
        threshold_pretty_bytes=THRESHOLD_PRETTY_BYTES,
        threshold_minified_bytes=THRESHOLD_MINIFIED_BYTES,
        passed=(
            pretty_bytes <= THRESHOLD_PRETTY_BYTES
            and minified_bytes <= THRESHOLD_MINIFIED_BYTES
        ),
    )

    assert pretty_bytes <= THRESHOLD_PRETTY_BYTES, (
        f"[full_th6_attack] pretty replay {pretty_bytes / 1024 / 1024:.2f} MB"
        f" > {THRESHOLD_PRETTY_BYTES / 1024 / 1024:.1f} MB threshold"
    )
    assert minified_bytes <= THRESHOLD_MINIFIED_BYTES, (
        f"[full_th6_attack] minified replay {minified_bytes / 1024 / 1024:.2f} MB"
        f" > {THRESHOLD_MINIFIED_BYTES / 1024 / 1024:.1f} MB threshold"
    )
