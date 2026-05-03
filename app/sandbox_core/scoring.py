"""Pure-functional score computation and termination check.

Per app/docs/sandbox/prd.md §5.9:
  - Stars: 1 if destruction>=50; +1 if TH destroyed; +1 if destruction>=100.
  - Destruction%: discrete per non-wall building.
"""

from __future__ import annotations

from sandbox_core.schemas import (
    BuildingCategory,
    BuildingState,
    BuildingType,
    Score,
    WorldState,
)

TIMER_TERMINATION_TICK: int = 1800


def compute_score(
    *,
    buildings: list[BuildingState],
    building_types: dict[str, BuildingType],
    tick: int,
) -> Score:
    non_wall_total = 0
    non_wall_destroyed = 0
    th_destroyed = False
    for b in buildings:
        bt = building_types[b.building_type]
        if bt.is_wall:
            continue
        non_wall_total += 1
        if b.destroyed:
            non_wall_destroyed += 1
            if bt.category is BuildingCategory.TOWN_HALL:
                th_destroyed = True

    destruction_pct = 0.0 if non_wall_total == 0 else (non_wall_destroyed / non_wall_total) * 100.0

    stars = 0
    if destruction_pct >= 50.0:
        stars += 1
    if th_destroyed:
        stars += 1
    if destruction_pct >= 100.0:
        stars += 1

    return Score(
        stars=stars,
        destruction_pct=destruction_pct,
        ticks_elapsed=tick,
        town_hall_destroyed=th_destroyed,
    )


def is_terminal(
    *,
    world: WorldState,
    troops_remaining_in_camps: int,
    spells_remaining: int,
    end_attack_emitted: bool,
) -> bool:
    """Termination conditions (any-fires) per PRD §5.9.

    1) tick >= 1800
    2) Destruction == 100%
    3) end_attack action emitted
    4) No further attack potential (no live troops AND no troops in camp AND no
       spells AND no in-flight projectiles AND no active spell casts).
    """
    if world.tick >= TIMER_TERMINATION_TICK:
        return True
    if world.score.destruction_pct >= 100.0:
        return True
    if end_attack_emitted:
        return True

    live_troops = sum(1 for t in world.troops if not t.destroyed)
    return (
        live_troops == 0
        and troops_remaining_in_camps == 0
        and spells_remaining == 0
        and len(world.projectiles) == 0
        and len(world.spells) == 0
    )


__all__ = ["TIMER_TERMINATION_TICK", "compute_score", "is_terminal"]
