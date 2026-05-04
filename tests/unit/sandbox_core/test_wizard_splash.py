"""Tests for Wizard splash damages walls (issue 008).

AC:
- Wizard has splash_damages_walls: true in merged content.
- Mortar and Wizard Tower have splash_damages_walls: false.
- When Wizard fires on a target whose splash radius covers walls, those walls
  take damage; emits `damage` events for each affected wall.
- Comparison: same splash geometry with Wizard source (walls damaged) vs
  splash_damages_walls=False source (walls untouched).
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
    EventType,
)
from sandbox_core.sim import Sim
from sandbox_core.splash import SplashTargetBuilding, resolve_splash


def _make_sim(base: BaseLayout, plan: DeploymentPlan | None = None) -> Sim:
    cat = load_catalogue()
    return Sim(
        base,
        plan,
        catalogue_buildings=cat.buildings,
        catalogue_troops=cat.troops,
        catalogue_spells=dict(cat.spells),
    )


def _base_with_buildings(*placements: BuildingPlacement) -> BaseLayout:
    return BaseLayout(
        metadata=BaseLayoutMetadata(name="wizard_splash_test", th_level=6),
        th_level=6,
        placements=list(placements),
    )


def _plan_with_actions(*actions: DeploymentAction) -> DeploymentPlan:
    return DeploymentPlan(
        metadata=DeploymentPlanMetadata(name="wizard_splash_test"),
        actions=list(actions),
    )


# ---------------------------------------------------------------------------
# Content / catalogue flag checks
# ---------------------------------------------------------------------------


def test_wizard_splash_damages_walls_true_in_content() -> None:
    cat = load_catalogue()
    wizard = cat.troops["wizard"]
    assert wizard.splash_damages_walls is True, (
        f"Expected wizard.splash_damages_walls=True, got {wizard.splash_damages_walls}"
    )


def test_mortar_splash_damages_walls_false_in_content() -> None:
    cat = load_catalogue()
    mortar = cat.buildings["mortar"]
    assert mortar.splash_damages_walls is False, (
        f"Expected mortar.splash_damages_walls=False, got {mortar.splash_damages_walls}"
    )


def test_wizard_tower_splash_damages_walls_false_in_content() -> None:
    cat = load_catalogue()
    wizard_tower = cat.buildings["wizard_tower"]
    assert wizard_tower.splash_damages_walls is False, (
        f"Expected wizard_tower.splash_damages_walls=False, got {wizard_tower.splash_damages_walls}"
    )


def test_wizard_has_nonzero_splash_radius() -> None:
    """Wizard must have a splash radius large enough to hit adjacent walls."""
    cat = load_catalogue()
    wizard = cat.troops["wizard"]
    assert wizard.splash_radius_tiles >= 1.0, (
        f"Wizard splash_radius_tiles={wizard.splash_radius_tiles} is too small to reach walls"
    )


# ---------------------------------------------------------------------------
# resolve_splash unit: same geometry, walls hit vs not hit
# ---------------------------------------------------------------------------


def test_resolve_splash_with_splash_damages_walls_true_hits_wall() -> None:
    """Wizard-source splash (splash_damages_walls=True) damages a wall in radius."""
    wall = SplashTargetBuilding(
        id=1,
        origin=(23, 23),
        footprint=(1, 1),
        hitbox_inset=0.0,
        is_wall=True,
        destroyed=False,
    )
    # Splash centered at (21.5, 23.5) with radius 2.0 — wall hitbox = full tile
    # [23..24, 23..24]; closest point (23.0, 23.5), distance 1.5 < 2.0 → wall hit.
    events = resolve_splash(
        center=(21.5, 23.5),
        radius=2.0,
        damage=70.0,
        attacker_id=99,
        buildings=[wall],
        troops=[],
        splash_damages_walls=True,
        hits_buildings=True,
        hits_troops=False,
        hits_friendly_troops=False,
    )
    assert len(events) == 1
    assert events[0].target_id == 1
    assert events[0].damage == 70.0


def test_resolve_splash_with_splash_damages_walls_false_skips_wall() -> None:
    """Mortar/WT-source splash (splash_damages_walls=False) skips walls even in radius."""
    wall = SplashTargetBuilding(
        id=1,
        origin=(23, 23),
        footprint=(1, 1),
        hitbox_inset=0.0,
        is_wall=True,
        destroyed=False,
    )
    events = resolve_splash(
        center=(21.5, 23.5),
        radius=2.0,
        damage=45.0,
        attacker_id=99,
        buildings=[wall],
        troops=[],
        splash_damages_walls=False,
        hits_buildings=True,
        hits_troops=False,
        hits_friendly_troops=False,
    )
    assert len(events) == 0, (
        f"Expected 0 splash damage events for wall when splash_damages_walls=False, got {len(events)}"
    )


# ---------------------------------------------------------------------------
# Sim integration: Wizard fires at Gold Mine with adjacent wall
# ---------------------------------------------------------------------------


def _wizard_on_gold_mine_with_wall() -> tuple[BaseLayout, DeploymentPlan]:
    """
    Gold Mine (3x3) at (20, 22); center at (21.5, 23.5).
    Wall (1x1) at (23, 23); hitbox at (23.5, 23.5); distance = 2.0 from center.
    Wizard level 2 deployed from (47.5, 23.5).
    """
    base = _base_with_buildings(
        BuildingPlacement(building_type="town_hall", origin=(3, 3), level=1),
        BuildingPlacement(building_type="gold_mine", origin=(20, 22), level=1),
        BuildingPlacement(building_type="wall", origin=(23, 23), level=1),
    )
    plan = _plan_with_actions(
        DeploymentAction(
            tick=0,
            kind="deploy_troop",
            entity_type="wizard",
            position=(47.5, 23.5),
            level=2,
        )
    )
    return base, plan


def test_wizard_splash_emits_damage_events_on_adjacent_wall() -> None:
    """Wizard fires at Gold Mine; wall within splash radius receives DAMAGE events."""
    base, plan = _wizard_on_gold_mine_with_wall()
    sim = _make_sim(base, plan)

    cat = load_catalogue()
    wall_id = next(
        b.id
        for b in sim._world.buildings  # type: ignore[attr-defined]
        if cat.buildings[b.building_type].is_wall
    )

    wall_damage_ticks: list[int] = []
    max_ticks = 200
    tick = 0
    while not sim.is_terminal() and tick < max_ticks:
        _world, events = sim.step_tick()
        for ev in events:
            if ev.type is EventType.DAMAGE and ev.payload.get("target_id") == wall_id:
                wall_damage_ticks.append(ev.tick)
        tick += 1

    assert wall_damage_ticks, (
        "No DAMAGE events emitted for the wall: Wizard splash did not hit the wall. "
        "Check that wizard.splash_radius_tiles >= 2.0 and splash_damages_walls=True."
    )


def test_wizard_splash_progressively_damages_wall_over_multiple_shots() -> None:
    """Wall HP decreases with each Wizard shot (progressive damage — AC requirement)."""
    base, plan = _wizard_on_gold_mine_with_wall()
    sim = _make_sim(base, plan)

    cat = load_catalogue()
    hp_snapshots: list[float] = []
    last_hp: float = float("inf")

    max_ticks = 200
    tick = 0
    while not sim.is_terminal() and tick < max_ticks:
        world, _events = sim.step_tick()
        wall_buildings = [b for b in world.buildings if cat.buildings[b.building_type].is_wall]
        if not wall_buildings:
            break
        current_hp = wall_buildings[0].hp
        if current_hp < last_hp:
            hp_snapshots.append(current_hp)
            last_hp = current_hp
        tick += 1

    assert len(hp_snapshots) >= 2, (
        f"Expected ≥2 HP decreases on the wall (progressive damage), "
        f"got {len(hp_snapshots)} snapshots: {hp_snapshots}"
    )
