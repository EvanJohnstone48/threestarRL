"""Performance benchmark: full TH6 scenario throughput.

Runs the full_th6_attack scenario repeatedly on a single core and asserts
≥ 50 episodes/sec per §12.1.
"""

from __future__ import annotations

import json
import time

import pytest
import sandbox_core
from sandbox_core.content import DEFAULT_DATA_DIR, load_catalogue, load_th_caps
from sandbox_core.replay import compute_config_hash
from sandbox_core.schemas import BaseLayout, DeploymentPlan
from sandbox_core.sim import Sim

from ._common import save_result

THRESHOLD_EP_SEC = 50.0
MIN_DURATION_S = 1.0

_BASE_PATH = DEFAULT_DATA_DIR / "sample_bases" / "full_th6_attack.json"
_PLAN_PATH = DEFAULT_DATA_DIR / "sample_plans" / "full_th6_attack.json"
_BUILDINGS_PATH = DEFAULT_DATA_DIR / "buildings.json"
_TROOPS_PATH = DEFAULT_DATA_DIR / "troops.json"


def _build_sim() -> Sim:
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

    return Sim(
        base,
        plan,
        catalogue_buildings=catalogue.buildings,
        catalogue_troops=catalogue.troops,
        catalogue_spells=catalogue.spells,
        spell_capacity_total=th_caps[base.th_level]["spell_capacity_total"],
        sim_version=sandbox_core.__version__,
        config_hash=config_hash,
    )


@pytest.mark.slow
def test_throughput_full_th6() -> None:
    sim = _build_sim()
    sim.run_until_termination()  # warmup

    episodes = 0
    start = time.perf_counter()
    while time.perf_counter() - start < MIN_DURATION_S:
        sim.reset()
        sim.run_until_termination()
        episodes += 1
    elapsed = time.perf_counter() - start

    ep_sec = episodes / elapsed
    save_result(
        "throughput_full_th6",
        scenario="full_th6_attack",
        episodes=episodes,
        elapsed_s=round(elapsed, 3),
        ep_sec=round(ep_sec, 1),
        threshold_ep_sec=THRESHOLD_EP_SEC,
        passed=ep_sec >= THRESHOLD_EP_SEC,
    )

    assert ep_sec >= THRESHOLD_EP_SEC, (
        f"[full_th6_attack] throughput {ep_sec:.1f} ep/sec"
        f" < {THRESHOLD_EP_SEC} ep/sec threshold"
        f" ({episodes} episodes in {elapsed:.3f}s)"
    )
