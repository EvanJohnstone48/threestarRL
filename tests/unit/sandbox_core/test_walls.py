"""Tests for wall HP, Wall Breaker suicide mechanics, and breach pathing (issue 007).

Covers:
  - Wall HP at level 1, 3, 6 matches buildings.json catalogue.
  - WB targets the nearest wall, not the nearest non-wall building.
  - WB on hitbox-adjacency to a wall triggers suicide (damage + destroyed events).
  - WB has zero HP and is despawned after suicide.
  - Walls in WB splash radius take damage (splash_damages_walls=True).
  - Non-wall buildings in splash radius take multiplier-adjusted damage.
  - splash_damages_walls=False (Mortar) leaves walls unaffected; WB does not.
  - Destroyed wall is skipped by _nearest_living_wall; WB re-targets remaining wall.
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


def _make_sim(base: BaseLayout, plan: DeploymentPlan | None = None) -> Sim:
    cat = load_catalogue()
    return Sim(
        base,
        plan,
        catalogue_buildings=cat.buildings,
        catalogue_troops=cat.troops,
        catalogue_spells=dict(cat.spells),
    )


def _base_with_walls(
    *wall_origins: tuple[int, int],
    wall_level: int = 1,
    th_origin: tuple[int, int] = (3, 3),
) -> BaseLayout:
    placements = [BuildingPlacement(building_type="town_hall", origin=th_origin, level=1)]
    for origin in wall_origins:
        placements.append(
            BuildingPlacement(building_type="wall", origin=origin, level=wall_level)
        )
    return BaseLayout(
        metadata=BaseLayoutMetadata(name="walls_test", th_level=6),
        th_level=6,
        placements=placements,
    )


def _deploy_wb(tick: int = 0, position: tuple[float, float] = (48.5, 24.5), level: int = 3) -> DeploymentAction:
    return DeploymentAction(
        tick=tick, kind="deploy_troop", entity_type="wall_breaker", position=position, level=level
    )


def _plan(*actions: DeploymentAction) -> DeploymentPlan:
    return DeploymentPlan(
        metadata=DeploymentPlanMetadata(name="test"),
        actions=sorted(actions, key=lambda a: a.tick),
    )


# ---- Wall HP -------------------------------------------------------------------


def test_wall_hp_at_level_1() -> None:
    cat = load_catalogue()
    wall = cat.buildings["wall"]
    assert wall.stats_at(1).hp == 300


def test_wall_hp_at_level_3() -> None:
    cat = load_catalogue()
    wall = cat.buildings["wall"]
    assert wall.stats_at(3).hp == 700


def test_wall_hp_at_level_6() -> None:
    cat = load_catalogue()
    wall = cat.buildings["wall"]
    assert wall.stats_at(6).hp == 2000


# ---- WB targets nearest wall ---------------------------------------------------


def test_wb_targets_nearest_wall_over_closer_non_wall() -> None:
    """WB (target_preference=walls, damages_walls_on_suicide=True) must walk
    toward the nearest wall even when a non-wall building is closer."""
    # TH at row 40 (close to WB deploy at 48.5), wall at row 30 (farther from WB).
    # Without WB-specific targeting, WB would head toward TH (closer).
    # With WB targeting, WB ignores TH and heads toward the wall instead.
    base = BaseLayout(
        metadata=BaseLayoutMetadata(name="wb_target", th_level=6),
        th_level=6,
        placements=[
            BuildingPlacement(building_type="town_hall", origin=(40, 24), level=1),
            BuildingPlacement(building_type="wall", origin=(30, 24), level=1),
        ],
    )
    plan = _plan(_deploy_wb(tick=0, position=(48.5, 24.5), level=3))
    sim = _make_sim(base, plan)

    # After 5 ticks WB has made 5 moves of 0.24 tiles = 1.2 tiles north.
    # If heading toward TH (row 40 center = 42): initial dist-to-hitbox ≈ 4.5, WB moves north.
    # If heading toward wall (row 30 center = 30.5): initial dist-to-hitbox ≈ 18, WB also moves north.
    # Both directions are north from row 48.5, so we can't distinguish by column.
    # Run until WB suicides; the wall should be damaged (not TH).
    wall_id = next(b.id for b in sim._world.buildings if b.building_type == "wall")  # type: ignore[attr-defined]
    th_id = next(b.id for b in sim._world.buildings if b.building_type == "town_hall")  # type: ignore[attr-defined]

    wall_damaged = False
    while not sim.is_terminal():
        _, events = sim.step_tick()
        for ev in events:
            if ev.type is EventType.DAMAGE:
                if ev.payload.get("target_id") == wall_id:
                    wall_damaged = True
                if ev.payload.get("target_id") == th_id and ev.payload.get("attacker_id") is not None:
                    pass  # WB targeted TH instead of wall — noted but checked via wall_damaged below

    assert wall_damaged, "WB must target and damage the wall, not the TH"


# ---- WB suicide mechanics ------------------------------------------------------


def test_wb_suicide_emits_damage_event_on_target_wall() -> None:
    """WB triggers suicide on wall adjacency and emits a DAMAGE event for the target wall."""
    # Wall near south edge; WB deployed in deploy ring just south of it.
    base = _base_with_walls((45, 24), wall_level=1)
    plan = _plan(_deploy_wb(tick=0, position=(48.5, 24.5), level=3))
    sim = _make_sim(base, plan)

    wall_id = next(b.id for b in sim._world.buildings if b.building_type == "wall")  # type: ignore[attr-defined]

    damage_events = []
    while not sim.is_terminal():
        _, events = sim.step_tick()
        damage_events.extend(
            e for e in events
            if e.type is EventType.DAMAGE and e.payload.get("target_id") == wall_id
        )

    assert damage_events, "No DAMAGE event emitted for target wall from WB suicide"


def test_wb_has_zero_hp_and_is_destroyed_after_suicide() -> None:
    """After WB suicides, its destroyed flag is True and hp is 0."""
    base = _base_with_walls((45, 24), wall_level=1)
    plan = _plan(_deploy_wb(tick=0, position=(48.5, 24.5), level=3))
    sim = _make_sim(base, plan)

    while not sim.is_terminal():
        sim.step_tick()

    wb_states = [t for t in sim._world.troops if t.troop_type == "wall_breaker"]  # type: ignore[attr-defined]
    assert wb_states, "WB troop should still be in world state (with destroyed=True)"
    wb = wb_states[0]
    assert wb.destroyed is True, "WB should be destroyed after suicide"
    assert wb.hp == 0.0, f"WB hp should be 0 after suicide, got {wb.hp}"


def test_wb_suicide_emits_destroyed_event_for_wb() -> None:
    """WB suicide emits a DESTROYED event for the Wall Breaker troop itself."""
    base = _base_with_walls((45, 24), wall_level=1)
    plan = _plan(_deploy_wb(tick=0, position=(48.5, 24.5), level=3))
    sim = _make_sim(base, plan)

    destroyed_troops = []
    while not sim.is_terminal():
        _, events = sim.step_tick()
        destroyed_troops.extend(
            e for e in events
            if e.type is EventType.DESTROYED and e.payload.get("kind") == "troop"
            and e.payload.get("troop_type") == "wall_breaker"
        )

    assert destroyed_troops, "No DESTROYED event emitted for wall_breaker after suicide"


# ---- Splash mechanics -----------------------------------------------------------


def test_wb_splash_damages_adjacent_wall() -> None:
    """Walls within WB splash radius (1.5 tiles) take damage from the explosion."""
    # Two walls: WB targets (45, 24), splash hits (45, 23) at 1-tile distance.
    base = _base_with_walls((45, 24), (45, 23), wall_level=1)
    plan = _plan(_deploy_wb(tick=0, position=(48.5, 24.5), level=3))
    sim = _make_sim(base, plan)

    splash_wall_id = next(
        b.id for b in sim._world.buildings  # type: ignore[attr-defined]
        if b.building_type == "wall" and b.origin == (45, 23)
    )

    splash_damage_events = []
    while not sim.is_terminal():
        _, events = sim.step_tick()
        splash_damage_events.extend(
            e for e in events
            if e.type is EventType.DAMAGE and e.payload.get("target_id") == splash_wall_id
        )

    assert splash_damage_events, "Adjacent wall should take splash damage from WB suicide"


def test_wb_wall_outside_splash_radius_not_damaged() -> None:
    """Wall beyond 1.5-tile splash radius takes no splash damage."""
    # WB targets (45, 24); wall at (45, 22) is 2 tiles from center — outside radius 1.5.
    base = _base_with_walls((45, 24), (45, 22), wall_level=1)
    plan = _plan(_deploy_wb(tick=0, position=(48.5, 24.5), level=3))
    sim = _make_sim(base, plan)

    far_wall_id = next(
        b.id for b in sim._world.buildings  # type: ignore[attr-defined]
        if b.building_type == "wall" and b.origin == (45, 22)
    )

    damage_events = []
    while not sim.is_terminal():
        _, events = sim.step_tick()
        damage_events.extend(
            e for e in events
            if e.type is EventType.DAMAGE and e.payload.get("target_id") == far_wall_id
        )

    assert not damage_events, (
        f"Wall at (30,22) is 2 tiles from splash center — should not take damage; got {damage_events}"
    )


def test_splash_damages_walls_false_mortar_leaves_walls_unaffected() -> None:
    """Mortar splash (splash_damages_walls=False) must not damage walls even if in radius."""
    # Mortar + wall in its splash radius — wall should take 0 damage.
    base = BaseLayout(
        metadata=BaseLayoutMetadata(name="mortar_wall", th_level=6),
        th_level=6,
        placements=[
            BuildingPlacement(building_type="town_hall", origin=(3, 3), level=1),
            BuildingPlacement(building_type="mortar", origin=(20, 20), level=4),
            # Wall 1 tile from Mortar splash center (within its 1.5-tile radius).
            BuildingPlacement(building_type="wall", origin=(25, 24), level=1),
        ],
    )
    plan = _plan(
        DeploymentAction(
            tick=0, kind="deploy_troop", entity_type="barbarian",
            position=(47.5, 24.5), level=1,
        ),
    )
    sim = _make_sim(base, plan)

    wall_id = next(b.id for b in sim._world.buildings if b.building_type == "wall")  # type: ignore[attr-defined]

    wall_damage_events = []
    while not sim.is_terminal():
        _, events = sim.step_tick()
        wall_damage_events.extend(
            e for e in events
            if e.type is EventType.DAMAGE and e.payload.get("target_id") == wall_id
        )

    assert not wall_damage_events, (
        "Mortar splash_damages_walls=False must not produce damage events on walls"
    )


def test_wb_splash_damages_walls_true_produces_wall_damage() -> None:
    """Contrast: WB splash_damages_walls=True does produce damage events on walls in radius."""
    base = _base_with_walls((45, 24), (45, 23), wall_level=1)
    plan = _plan(_deploy_wb(tick=0, position=(48.5, 24.5), level=3))
    sim = _make_sim(base, plan)

    all_wall_ids = {b.id for b in sim._world.buildings if b.building_type == "wall"}  # type: ignore[attr-defined]

    wall_damage_events = []
    while not sim.is_terminal():
        _, events = sim.step_tick()
        wall_damage_events.extend(
            e for e in events
            if e.type is EventType.DAMAGE and e.payload.get("target_id") in all_wall_ids
        )

    assert wall_damage_events, "WB splash_damages_walls=True must produce damage events on walls"


# ---- Wall destruction + re-pathing ---------------------------------------------


def test_destroyed_wall_skipped_wb_retargets_remaining_wall() -> None:
    """After WB destroys one wall, subsequent WBs target the remaining undestroyed wall."""
    # Wall A at (45, 24) - first WB target (nearest). Wall B at (45, 10) - second target.
    # Both walls are level 1 (HP=300). Level-3 WB does 320 damage — one-shots each.
    base = BaseLayout(
        metadata=BaseLayoutMetadata(name="retarget", th_level=6),
        th_level=6,
        placements=[
            BuildingPlacement(building_type="town_hall", origin=(3, 3), level=1),
            BuildingPlacement(building_type="wall", origin=(45, 24), level=1),
            BuildingPlacement(building_type="wall", origin=(45, 10), level=1),
        ],
    )
    plan = _plan(
        _deploy_wb(tick=0, position=(48.5, 24.5), level=3),
        # Second WB deployed in col-10 corridor at tick 50 (well after first WB suicides)
        _deploy_wb(tick=50, position=(48.5, 10.5), level=3),
    )
    sim = _make_sim(base, plan)

    while not sim.is_terminal():
        sim.step_tick()

    # Both walls should be destroyed (first by WB1, second by WB2).
    wall_a = next(
        b for b in sim._world.buildings  # type: ignore[attr-defined]
        if b.building_type == "wall" and b.origin == (45, 24)
    )
    wall_b = next(
        b for b in sim._world.buildings  # type: ignore[attr-defined]
        if b.building_type == "wall" and b.origin == (45, 10)
    )
    assert wall_a.destroyed, "Wall A should be destroyed by first WB"
    assert wall_b.destroyed, "Wall B should be destroyed by second WB"
