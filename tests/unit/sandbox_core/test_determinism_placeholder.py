"""Placeholder determinism check.

The full byte-identical-replay regression test (issue 011) lives in
`tests/integration/test_replay_determinism.py` and is marked `slow`. This
fast smoke check only asserts that two consecutive runs of the same
`(base, plan)` produce equivalent terminal scores and the same total tick
count — sufficient to catch gross non-determinism in pre-commit.
"""

from __future__ import annotations

from sandbox_core.content import load_catalogue
from sandbox_core.schemas import (
    BaseLayout,
    BaseLayoutMetadata,
    BuildingPlacement,
    DeploymentAction,
    DeploymentPlan,
    DeploymentPlanMetadata,
)
from sandbox_core.sim import Sim


def _build_sim() -> Sim:
    cat = load_catalogue()
    base = BaseLayout(
        metadata=BaseLayoutMetadata(name="t", th_level=6),
        th_level=6,
        placements=[
            BuildingPlacement(building_type="town_hall", origin=(15, 15), level=1),
            BuildingPlacement(building_type="cannon", origin=(40, 40), level=1),
        ],
    )
    plan = DeploymentPlan(
        metadata=DeploymentPlanMetadata(name="p"),
        actions=[
            DeploymentAction(
                tick=0, kind="deploy_troop", entity_type="barbarian", position=(2.5, 17.5), level=6
            )
        ],
    )
    return Sim(base, plan, catalogue_buildings=cat.buildings, catalogue_troops=cat.troops)


def test_two_runs_same_score_and_ticks() -> None:
    sim_a = _build_sim()
    sim_a.run_until_termination()
    sim_b = _build_sim()
    sim_b.run_until_termination()

    assert sim_a.score() == sim_b.score()
    assert len(sim_a.to_replay().frames) == len(sim_b.to_replay().frames)
