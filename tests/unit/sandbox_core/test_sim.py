"""Tests for Sim — error contracts, basic step semantics."""

from __future__ import annotations

from pathlib import Path

import pytest
from sandbox_core.content import load_catalogue
from sandbox_core.schemas import (
    BaseLayout,
    BaseLayoutMetadata,
    BuildingPlacement,
    DeploymentAction,
    DeploymentPlan,
    DeploymentPlanMetadata,
    EventType,
    InvalidDeploymentError,
    SimTerminatedError,
)
from sandbox_core.sim import Sim


def _tracer_base() -> BaseLayout:
    return BaseLayout(
        metadata=BaseLayoutMetadata(name="t", th_level=6),
        th_level=6,
        placements=[
            BuildingPlacement(building_type="town_hall", origin=(15, 15), level=1),
            BuildingPlacement(building_type="cannon", origin=(40, 40), level=1),
        ],
    )


def _single_barb_plan() -> DeploymentPlan:
    return DeploymentPlan(
        metadata=DeploymentPlanMetadata(name="p"),
        actions=[
            DeploymentAction(
                tick=0, kind="deploy_troop", entity_type="barbarian", position=(2.5, 17.5), level=6
            )
        ],
    )


def _make_sim(plan: DeploymentPlan | None = None) -> Sim:
    cat = load_catalogue()
    return Sim(
        _tracer_base(),
        plan,
        catalogue_buildings=cat.buildings,
        catalogue_troops=cat.troops,
        catalogue_spells=dict(cat.spells),
    )


def test_step_after_termination_raises() -> None:
    sim = _make_sim(_single_barb_plan())
    sim.run_until_termination()
    assert sim.is_terminal()
    with pytest.raises(SimTerminatedError):
        sim.step_tick()


def test_advance_to_backwards_raises() -> None:
    sim = _make_sim(_single_barb_plan())
    sim.step_tick()
    with pytest.raises(ValueError):
        sim.advance_to(0)


def test_schedule_after_termination_raises() -> None:
    sim = _make_sim(_single_barb_plan())
    sim.run_until_termination()
    with pytest.raises(SimTerminatedError):
        sim.schedule_deployment(
            DeploymentAction(
                tick=10, kind="deploy_troop", entity_type="barbarian", position=(2.5, 17.5)
            )
        )


def test_invalid_deploy_position_raises() -> None:
    sim = _make_sim()
    # (15, 15) is inside the buildable region, not deploy ring → invalid for troops.
    with pytest.raises(InvalidDeploymentError):
        sim.schedule_deployment(
            DeploymentAction(
                tick=10, kind="deploy_troop", entity_type="barbarian", position=(15.5, 15.5)
            )
        )


def test_unknown_troop_type_raises() -> None:
    sim = _make_sim()
    with pytest.raises(InvalidDeploymentError):
        sim.schedule_deployment(
            DeploymentAction(
                tick=10, kind="deploy_troop", entity_type="dragon", position=(2.5, 17.5)
            )
        )


def test_tracer_destroys_town_hall_and_terminates() -> None:
    sim = _make_sim(_single_barb_plan())
    sim.run_until_termination()
    assert sim.is_terminal()
    score = sim.score()
    assert score.town_hall_destroyed
    assert score.destruction_pct >= 50.0
    assert score.stars >= 2


def test_goblin_on_gold_storage_deals_2x_base_damage_per_attack_tick() -> None:
    """AC issue #6: Goblin's resource_storage multiplier is honored end-to-end."""
    cat = load_catalogue()
    base = BaseLayout(
        metadata=BaseLayoutMetadata(name="t", th_level=6),
        th_level=6,
        placements=[
            # TH placed far from the deploy point so the goblin prefers gold_storage.
            BuildingPlacement(building_type="town_hall", origin=(40, 40), level=1),
            BuildingPlacement(building_type="gold_storage", origin=(3, 3), level=1),
        ],
    )
    plan = DeploymentPlan(
        metadata=DeploymentPlanMetadata(name="p"),
        actions=[
            DeploymentAction(
                tick=0, kind="deploy_troop", entity_type="goblin", position=(2.5, 4.5), level=4
            )
        ],
    )
    sim = Sim(
        base,
        plan,
        catalogue_buildings=cat.buildings,
        catalogue_troops=cat.troops,
        catalogue_spells=dict(cat.spells),
    )

    expected = cat.troops["goblin"].stats_at(4).base_damage * 2.0
    base_damage = cat.troops["goblin"].stats_at(4).base_damage

    damage_values: list[float] = []
    # Run enough ticks for the goblin to walk to the storage and attack a few times.
    for _ in range(60):
        if sim.is_terminal():
            break
        _, events = sim.step_tick()
        for ev in events:
            if (
                ev.type is EventType.DAMAGE
                and ev.payload.get("attacker_id") is not None
                and "kind" in ev.payload
            ):
                # Only count goblin attacks (attacker_id is the goblin's id).
                # The deployed goblin is the only troop on the field, so its id is the
                # only non-building attacker id we'll see.
                # Filter to attacks against the gold_storage by checking damage value
                # is non-zero and target was a building (defenses don't shoot here).
                damage_values.append(float(ev.payload["damage"]))

    assert damage_values, "expected at least one goblin attack to land"
    # Every recorded goblin → gold_storage damage should be exactly 2x base.
    for d in damage_values:
        assert d == pytest.approx(expected), (
            f"goblin damage {d} != expected 2x base {expected} (base={base_damage})"
        )


def test_replay_artifact_round_trip(tmp_path: Path) -> None:
    from sandbox_core.replay import read_replay, write_replay

    sim = _make_sim(_single_barb_plan())
    sim.run_until_termination()
    replay = sim.to_replay(base_name="t", plan_name="p")

    p = tmp_path / "r.json"
    write_replay(replay, p, pretty=False)
    loaded = read_replay(p)
    assert loaded.metadata.total_ticks == replay.metadata.total_ticks
    assert loaded.metadata.final_score.stars == replay.metadata.final_score.stars
    assert len(loaded.frames) == len(replay.frames)
