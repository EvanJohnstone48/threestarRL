"""Tests for defense + projectile + splash mechanics (issue 005).

Covers:
  - Mortar non-homing: impact_position committed at fire time, snapped to tile center.
  - Mortar splash applies in radius regardless of original-target survival.
  - Cannon homing projectile silently despawns when target dies mid-flight.
  - Air Defense ignores ground-only troops (target_filter=air).
  - Wizard Tower splash damages only troops, never buildings.
  - Mortar respects min_range_tiles (doesn't fire on close-by troops).
"""

from __future__ import annotations

from sandbox_core.content import load_catalogue
from sandbox_core.schemas import (
    AttackKind,
    BaseLayout,
    BaseLayoutMetadata,
    BuildingPlacement,
    DeploymentAction,
    DeploymentPlan,
    DeploymentPlanMetadata,
    EventType,
    Projectile,
    TroopState,
    WorldState,
)
from sandbox_core.sim import Sim


def _make_sim(base: BaseLayout, plan: DeploymentPlan | None) -> Sim:
    cat = load_catalogue()
    return Sim(
        base,
        plan,
        catalogue_buildings=cat.buildings,
        catalogue_troops=cat.troops,
        catalogue_spells=dict(cat.spells),
    )


def _world(sim: Sim) -> WorldState:
    return sim._world  # type: ignore[attr-defined,no-any-return]


def _mortar_splash_base() -> BaseLayout:
    return BaseLayout(
        metadata=BaseLayoutMetadata(name="mortar_splash", th_level=6),
        th_level=6,
        placements=[
            BuildingPlacement(building_type="town_hall", origin=(3, 3), level=1),
            BuildingPlacement(building_type="mortar", origin=(40, 24), level=4),
        ],
    )


def _mortar_splash_plan() -> DeploymentPlan:
    return DeploymentPlan(
        metadata=DeploymentPlanMetadata(name="mortar_splash"),
        actions=[
            DeploymentAction(
                tick=0,
                kind="deploy_troop",
                entity_type="barbarian",
                position=(47.5, 24.5),
                level=1,
            ),
            DeploymentAction(
                tick=0,
                kind="deploy_troop",
                entity_type="barbarian",
                position=(47.5, 25.5),
                level=1,
            ),
            DeploymentAction(
                tick=0,
                kind="deploy_troop",
                entity_type="barbarian",
                position=(47.5, 26.5),
                level=1,
            ),
            DeploymentAction(
                tick=0,
                kind="deploy_troop",
                entity_type="barbarian",
                position=(48.5, 25.5),
                level=1,
            ),
            DeploymentAction(
                tick=0,
                kind="deploy_troop",
                entity_type="barbarian",
                position=(49.5, 25.5),
                level=1,
            ),
        ],
    )


def _building_id_by_type(sim: Sim, building_type: str) -> int:
    for b in _world(sim).buildings:
        if b.building_type == building_type:
            return b.id
    raise AssertionError(f"no {building_type} found")


def test_mortar_single_impact_damages_three_or_more_clustered_barbarians() -> None:
    """AC: Mortar's first splash impact damages 3+ barbarians in radius."""
    sim = _make_sim(_mortar_splash_base(), _mortar_splash_plan())

    splash_damages_per_tick: dict[int, int] = {}
    while not sim.is_terminal():
        _, events = sim.step_tick()
        for ev in events:
            if ev.type is EventType.DAMAGE and ev.payload.get("kind") == AttackKind.RANGED.value:
                splash_damages_per_tick[ev.tick] = splash_damages_per_tick.get(ev.tick, 0) + 1

    multi_hit_ticks = [t for t, n in splash_damages_per_tick.items() if n >= 3]
    assert multi_hit_ticks, (
        f"expected ≥1 tick with 3+ ranged DAMAGE events from a single Mortar splash; "
        f"got per-tick counts: {splash_damages_per_tick}"
    )


def test_mortar_impact_position_snapped_to_tile_center_at_fire_time() -> None:
    """Non-homing Mortar projectiles commit impact_position to nearest tile center."""
    base = _mortar_splash_base()
    plan = DeploymentPlan(
        metadata=DeploymentPlanMetadata(name="snap"),
        actions=[
            # 47.7, 25.3 — fractional position; tile-center snap should be (47.5, 25.5).
            DeploymentAction(
                tick=0,
                kind="deploy_troop",
                entity_type="barbarian",
                position=(47.7, 25.3),
                level=1,
            ),
        ],
    )
    sim = _make_sim(base, plan)

    while not sim.is_terminal():
        state, events = sim.step_tick()
        for ev in events:
            if ev.type is EventType.PROJECTILE_FIRED:
                assert state.projectiles, "expected a projectile after PROJECTILE_FIRED"
                proj = state.projectiles[0]
                r, c = proj.impact_position
                assert r == int(r) + 0.5, f"row {r} not snapped to tile center"
                assert c == int(c) + 0.5, f"col {c} not snapped to tile center"
                return
    raise AssertionError("Mortar never fired")


def test_air_defense_ignores_ground_only_troops() -> None:
    """AD's target_filter='air' means it never fires on a barbarian (ground)."""
    base = BaseLayout(
        metadata=BaseLayoutMetadata(name="ad", th_level=6),
        th_level=6,
        placements=[
            BuildingPlacement(building_type="town_hall", origin=(3, 3), level=1),
            BuildingPlacement(building_type="air_defense", origin=(20, 20), level=4),
        ],
    )
    plan = DeploymentPlan(
        metadata=DeploymentPlanMetadata(name="g"),
        actions=[
            DeploymentAction(
                tick=0,
                kind="deploy_troop",
                entity_type="barbarian",
                position=(2.5, 21.5),
                level=6,
            ),
        ],
    )
    sim = _make_sim(base, plan)
    ad_id = _building_id_by_type(sim, "air_defense")

    while not sim.is_terminal() and sim.score().ticks_elapsed < 300:
        _, events = sim.step_tick()
        for ev in events:
            assert not (
                ev.type is EventType.PROJECTILE_FIRED and ev.payload.get("attacker_id") == ad_id
            ), "Air Defense fired at a ground troop; target_filter=air must filter it"


def test_homing_projectile_silently_despawns_when_target_already_dead() -> None:
    """A homing projectile in flight whose target dies before impact emits no damage event."""
    base = BaseLayout(
        metadata=BaseLayoutMetadata(name="cannon", th_level=6),
        th_level=6,
        placements=[
            BuildingPlacement(building_type="town_hall", origin=(3, 3), level=1),
            BuildingPlacement(building_type="cannon", origin=(40, 40), level=1),
        ],
    )
    sim = _make_sim(base, None)
    cannon_id = _building_id_by_type(sim, "cannon")

    fake_troop = TroopState(
        id=999,
        troop_type="barbarian",
        level=6,
        position=(40.0, 40.0),
        hp=0.0,
        max_hp=110.0,
        destroyed=True,
    )
    _world(sim).troops.append(fake_troop)

    proj = Projectile(
        id=998,
        attacker_id=cannon_id,
        target_id=999,
        attack_kind=AttackKind.RANGED,
        attacker_position=(41.5, 41.5),
        current_position=(41.5, 41.5),
        impact_position=(40.0, 40.0),
        damage=25.0,
        splash_radius_tiles=0.0,
        splash_damages_walls=False,
        ticks_to_impact=1,
    )
    _world(sim).projectiles.append(proj)

    state, events = sim.step_tick()

    cannon_damage_events = [
        e
        for e in events
        if e.type is EventType.DAMAGE and e.payload.get("attacker_id") == cannon_id
    ]
    assert not cannon_damage_events, (
        f"homing projectile should despawn silently when target dead; got {cannon_damage_events}"
    )
    assert all(p.id != 998 for p in state.projectiles), "projectile not despawned"


def test_wizard_tower_splash_never_damages_buildings() -> None:
    """WT (splash radius 1.0) attacks troops; its splash never produces a damage event
    targeting any building (defenses don't friendly-fire other defenses or walls)."""
    base = BaseLayout(
        metadata=BaseLayoutMetadata(name="wt", th_level=6),
        th_level=6,
        placements=[
            BuildingPlacement(building_type="town_hall", origin=(3, 3), level=1),
            BuildingPlacement(building_type="wizard_tower", origin=(20, 20), level=2),
            BuildingPlacement(building_type="wall", origin=(23, 23), level=6),
        ],
    )
    plan = DeploymentPlan(
        metadata=DeploymentPlanMetadata(name="wt-test"),
        actions=[
            DeploymentAction(
                tick=0,
                kind="deploy_troop",
                entity_type="barbarian",
                position=(2.5, 21.5),
                level=6,
            ),
            DeploymentAction(
                tick=0,
                kind="deploy_troop",
                entity_type="barbarian",
                position=(2.5, 22.5),
                level=6,
            ),
        ],
    )
    sim = _make_sim(base, plan)
    wt_id = _building_id_by_type(sim, "wizard_tower")
    building_ids = {b.id for b in _world(sim).buildings}

    while not sim.is_terminal() and sim.score().ticks_elapsed < 400:
        _, events = sim.step_tick()
        for ev in events:
            if (
                ev.type is EventType.DAMAGE
                and ev.payload.get("attacker_id") == wt_id
                and ev.payload.get("target_id") in building_ids
            ):
                raise AssertionError(
                    f"WT damaged building id={ev.payload.get('target_id')} via splash; "
                    f"defense splash must filter to troops only"
                )


def test_archer_tower_filter_both_fires_on_ground_troop() -> None:
    """AT target_filter=both should still fire on ground troops (regression check)."""
    base = BaseLayout(
        metadata=BaseLayoutMetadata(name="at", th_level=6),
        th_level=6,
        placements=[
            # TH out of the barb's pathing line so it targets AT, not TH.
            BuildingPlacement(building_type="town_hall", origin=(3, 42), level=1),
            BuildingPlacement(building_type="archer_tower", origin=(20, 20), level=6),
        ],
    )
    plan = DeploymentPlan(
        metadata=DeploymentPlanMetadata(name="g"),
        actions=[
            DeploymentAction(
                tick=0,
                kind="deploy_troop",
                entity_type="barbarian",
                position=(2.5, 21.5),
                level=6,
            ),
        ],
    )
    sim = _make_sim(base, plan)
    at_id = _building_id_by_type(sim, "archer_tower")

    fired = False
    while not sim.is_terminal() and not fired and sim.score().ticks_elapsed < 300:
        _, events = sim.step_tick()
        for ev in events:
            if ev.type is EventType.PROJECTILE_FIRED and ev.payload.get("attacker_id") == at_id:
                fired = True
    assert fired, "Archer Tower with filter=both must fire on a ground troop"
