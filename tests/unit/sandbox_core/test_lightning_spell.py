"""Tests for the Lightning Spell (issue 009).

AC:
- lightning_spell loaded in catalogue with correct stats.
- Cast creates SpellCast entity; SPELL_CAST event emitted.
- Cast at deploy-ring position rejected by validator.
- Bolts fire at hit_interval_ticks cadence; BOLT_STRUCK events emitted.
- Bolts damage buildings and troops in radius; walls never damaged.
- Friendly troops in radius take damage.
- Spell capacity enforced; 3rd cast (over TH6 cap of 2) raises InvalidDeploymentError.
- SpellCast despawns when bolts_remaining reaches 0.
"""

from __future__ import annotations

import pytest
from sandbox_core.content import load_catalogue, load_th_caps
from sandbox_core.schemas import (
    BaseLayout,
    BaseLayoutMetadata,
    BuildingPlacement,
    DeploymentAction,
    DeploymentPlan,
    DeploymentPlanMetadata,
    EventType,
    InvalidDeploymentError,
)
from sandbox_core.sim import Sim


def _make_sim(
    base: BaseLayout,
    plan: DeploymentPlan | None = None,
    spell_capacity_total: int = 0,
) -> Sim:
    cat = load_catalogue()
    return Sim(
        base,
        plan,
        catalogue_buildings=cat.buildings,
        catalogue_troops=cat.troops,
        catalogue_spells=cat.spells,
        spell_capacity_total=spell_capacity_total,
    )


def _base(*placements: BuildingPlacement, th_level: int = 6) -> BaseLayout:
    return BaseLayout(
        metadata=BaseLayoutMetadata(name="lightning_test", th_level=th_level),
        th_level=th_level,
        placements=list(placements),
    )


def _plan(*actions: DeploymentAction) -> DeploymentPlan:
    return DeploymentPlan(
        metadata=DeploymentPlanMetadata(name="lightning_test"),
        actions=list(actions),
    )


def _cast(tick: int, position: tuple[float, float], level: int = 3) -> DeploymentAction:
    return DeploymentAction(
        tick=tick,
        kind="cast_spell",
        entity_type="lightning_spell",
        position=position,
        level=level,
    )


# ---------------------------------------------------------------------------
# Catalogue / content checks
# ---------------------------------------------------------------------------


def test_lightning_spell_loaded_in_catalogue() -> None:
    cat = load_catalogue()
    assert "lightning_spell" in cat.spells
    ls = cat.spells["lightning_spell"]
    assert ls.num_hits == 5
    assert ls.radius_tiles == 3.0
    assert ls.damages_walls is False
    assert ls.hit_interval_ticks == 1


def test_spell_capacity_at_th6() -> None:
    caps = load_th_caps()
    assert caps[6]["spell_capacity_total"] == 2


# ---------------------------------------------------------------------------
# Cast creates entity and emits event
# ---------------------------------------------------------------------------


def test_cast_creates_spell_cast_entity() -> None:
    base = _base(
        BuildingPlacement(building_type="town_hall", origin=(3, 3), level=1),
    )
    plan = _plan(_cast(tick=0, position=(26.5, 26.5)))
    sim = _make_sim(base, plan)

    sim.step_tick()  # tick 0: deployment fires

    assert len(sim._world.spells) == 1  # type: ignore[attr-defined]
    sc = sim._world.spells[0]  # type: ignore[attr-defined]
    assert sc.spell_type == "lightning_spell"
    assert sc.bolts_remaining == 5
    assert sc.next_bolt_tick == 1


def test_cast_emits_spell_cast_event() -> None:
    base = _base(
        BuildingPlacement(building_type="town_hall", origin=(3, 3), level=1),
    )
    plan = _plan(_cast(tick=0, position=(26.5, 26.5)))
    sim = _make_sim(base, plan)

    _world, events = sim.step_tick()

    spell_cast_events = [e for e in events if e.type is EventType.SPELL_CAST]
    assert len(spell_cast_events) == 1
    ev = spell_cast_events[0]
    assert ev.payload["spell_type"] == "lightning_spell"
    assert ev.payload["level"] == 3


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_cast_outside_buildable_region_rejected() -> None:
    base = _base(
        BuildingPlacement(building_type="town_hall", origin=(3, 3), level=1),
    )
    # Row 1 is in the deploy ring, not the inner buildable region (rows 3-46).
    plan = _plan(_cast(tick=0, position=(1.5, 25.5)))
    with pytest.raises(InvalidDeploymentError, match="outside inner buildable region"):
        _make_sim(base, plan)


# ---------------------------------------------------------------------------
# Bolt cadence
# ---------------------------------------------------------------------------


def test_bolts_fire_at_correct_cadence() -> None:
    """5 bolts fire at ticks 1-5 (hit_interval_ticks=1)."""
    base = _base(
        BuildingPlacement(building_type="town_hall", origin=(3, 3), level=1),
    )
    plan = _plan(_cast(tick=0, position=(26.5, 26.5)))
    sim = _make_sim(base, plan)

    bolt_ticks: list[int] = []
    for _ in range(7):  # tick 0-6
        _world, events = sim.step_tick()
        for ev in events:
            if ev.type is EventType.BOLT_STRUCK:
                bolt_ticks.append(ev.tick)
        if sim.is_terminal():
            break

    assert bolt_ticks == [1, 2, 3, 4, 5], f"expected [1,2,3,4,5] got {bolt_ticks}"


# ---------------------------------------------------------------------------
# Damage behavior
# ---------------------------------------------------------------------------


def test_bolt_damages_building_in_radius() -> None:
    """Lightning damages a non-wall building within radius."""
    # Cannon at (20, 20): 3x3 footprint, center (21.5, 21.5).
    # Cast center at (21.5, 21.5) → distance = 0 → always in radius.
    base = _base(
        BuildingPlacement(building_type="town_hall", origin=(3, 3), level=1),
        BuildingPlacement(building_type="cannon", origin=(20, 20), level=1),
    )
    plan = _plan(_cast(tick=0, position=(21.5, 21.5)))
    sim = _make_sim(base, plan)

    cannon_id = next(
        b.id
        for b in sim._world.buildings  # type: ignore[attr-defined]
        if b.building_type == "cannon"
    )

    damage_events: list[int] = []
    for _ in range(8):
        _world, events = sim.step_tick()
        for ev in events:
            if ev.type is EventType.DAMAGE and ev.payload.get("target_id") == cannon_id:
                damage_events.append(ev.tick)
        if sim.is_terminal():
            break

    assert len(damage_events) >= 1, "Cannon should receive DAMAGE events from Lightning bolts"


def test_bolt_does_not_damage_wall() -> None:
    """Lightning (target_filter=all_except_walls) never damages walls."""
    # Wall at (24, 28): center (24.5, 28.5), distance from (26.5, 26.5) ≈ 2.83 < 3.0.
    base = _base(
        BuildingPlacement(building_type="town_hall", origin=(3, 3), level=1),
        BuildingPlacement(building_type="wall", origin=(24, 28), level=1),
    )
    plan = _plan(_cast(tick=0, position=(26.5, 26.5)))
    sim = _make_sim(base, plan)

    cat = load_catalogue()
    wall_id = next(
        b.id
        for b in sim._world.buildings  # type: ignore[attr-defined]
        if cat.buildings[b.building_type].is_wall
    )

    wall_damage_events: list[int] = []
    for _ in range(8):
        if sim.is_terminal():
            break
        _world, events = sim.step_tick()
        for ev in events:
            if ev.type is EventType.DAMAGE and ev.payload.get("target_id") == wall_id:
                wall_damage_events.append(ev.tick)

    assert wall_damage_events == [], (
        f"Wall should not take Lightning damage (target_filter=all_except_walls), "
        f"got events at ticks: {wall_damage_events}"
    )


def test_bolt_damages_friendly_troop_in_radius() -> None:
    """Lightning damages friendly troops in radius (real-game behavior).

    Barbarian deployed at (47.5, 25.5) — deploy ring.
    Lightning cast at (46.5, 25.5) — buildable region, distance=1.0 < 3.0 radius.
    Bolt at tick 1 hits the barbarian before it has moved far.
    """
    base = _base(
        BuildingPlacement(building_type="town_hall", origin=(3, 3), level=1),
    )
    plan = _plan(
        DeploymentAction(
            tick=0,
            kind="deploy_troop",
            entity_type="barbarian",
            position=(47.5, 25.5),
            level=1,
        ),
        _cast(tick=0, position=(46.5, 25.5)),
    )
    sim = _make_sim(base, plan)

    barb_ids: set[int] = set()
    troop_damage_events: list[int] = []
    for _ in range(8):
        if sim.is_terminal():
            break
        _world, events = sim.step_tick()
        # Collect barbarian IDs once they're deployed.
        barb_ids |= {
            t.id
            for t in _world.troops
            if t.troop_type == "barbarian"
        }
        for ev in events:
            if ev.type is EventType.DAMAGE and ev.payload.get("target_id") in barb_ids:
                troop_damage_events.append(ev.tick)

    assert troop_damage_events, "Friendly Barbarian should take Lightning bolt damage"


# ---------------------------------------------------------------------------
# Spell capacity
# ---------------------------------------------------------------------------


def test_spell_capacity_exceeded_raises_error() -> None:
    """3rd Lightning cast (housing_space=1 each, capacity=2) raises InvalidDeploymentError."""
    base = _base(
        BuildingPlacement(building_type="town_hall", origin=(3, 3), level=1),
    )
    # 3 casts at different ticks; third exceeds capacity.
    plan = _plan(
        _cast(tick=0, position=(26.5, 26.5)),
        _cast(tick=20, position=(26.5, 26.5)),
        _cast(tick=40, position=(26.5, 26.5)),
    )
    sim = _make_sim(base, plan, spell_capacity_total=2)

    with pytest.raises(InvalidDeploymentError, match="spell capacity exceeded"):
        sim.run_until_termination()


# ---------------------------------------------------------------------------
# SpellCast lifecycle
# ---------------------------------------------------------------------------


def test_spell_despawns_after_all_bolts() -> None:
    """After 5 bolts at ticks 1-5, world.spells is empty at tick 6."""
    base = _base(
        BuildingPlacement(building_type="town_hall", origin=(3, 3), level=1),
    )
    plan = _plan(_cast(tick=0, position=(26.5, 26.5)))
    sim = _make_sim(base, plan)

    for _ in range(6):  # ticks 0-5
        if sim.is_terminal():
            break
        sim.step_tick()

    assert sim._world.spells == [], (  # type: ignore[attr-defined]
        "SpellCast should despawn after all 5 bolts have fired"
    )
