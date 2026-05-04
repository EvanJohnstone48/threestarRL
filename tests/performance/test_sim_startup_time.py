"""Performance benchmark: Sim startup time.

Measures the time to load content (loader + content merge) and instantiate Sim
with base validation, asserts ≤ 100 ms per §12.1.
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

THRESHOLD_MS = 100.0

_BASE_PATH = DEFAULT_DATA_DIR / "sample_bases" / "full_th6_attack.json"
_PLAN_PATH = DEFAULT_DATA_DIR / "sample_plans" / "full_th6_attack.json"
_BUILDINGS_PATH = DEFAULT_DATA_DIR / "buildings.json"
_TROOPS_PATH = DEFAULT_DATA_DIR / "troops.json"


@pytest.mark.slow
def test_sim_startup_time() -> None:
    base_raw = json.loads(_BASE_PATH.read_text(encoding="utf-8"))
    plan_raw = json.loads(_PLAN_PATH.read_text(encoding="utf-8"))
    buildings_raw = json.loads(_BUILDINGS_PATH.read_text(encoding="utf-8"))
    troops_raw = json.loads(_TROOPS_PATH.read_text(encoding="utf-8"))

    base = BaseLayout.model_validate(base_raw)
    plan = DeploymentPlan.model_validate(plan_raw)
    config_hash = compute_config_hash(base_raw, plan_raw, buildings_raw, troops_raw)

    start = time.perf_counter()
    catalogue = load_catalogue()
    th_caps = load_th_caps()
    Sim(
        base,
        plan,
        catalogue_buildings=catalogue.buildings,
        catalogue_troops=catalogue.troops,
        catalogue_spells=catalogue.spells,
        spell_capacity_total=th_caps[base.th_level]["spell_capacity_total"],
        sim_version=sandbox_core.__version__,
        config_hash=config_hash,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000

    save_result(
        "sim_startup_time",
        scenario="full_th6_attack",
        elapsed_ms=round(elapsed_ms, 2),
        threshold_ms=THRESHOLD_MS,
        passed=elapsed_ms <= THRESHOLD_MS,
    )

    assert elapsed_ms <= THRESHOLD_MS, (
        f"[sim_startup] startup {elapsed_ms:.1f} ms"
        f" > {THRESHOLD_MS:.0f} ms threshold"
        f" (load_catalogue + load_th_caps + Sim())"
    )
