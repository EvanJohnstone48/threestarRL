"""Pure-functional splash resolution.

`resolve_splash` returns DamageEvents for every entity within `radius` of `center`,
filtered by source rules (e.g., Mortar splash skips walls). No state is mutated.

Distance metric (PRD §5.7): Euclidean from splash center to closest point of each
target's *square* hitbox; troops measured by their float position.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from sandbox_core.combat import DamageEvent
from sandbox_core.grid import distance_point_to_square_hitbox, euclidean


@dataclass(frozen=True, slots=True)
class SplashTargetBuilding:
    id: int
    origin: tuple[int, int]
    footprint: tuple[int, int]
    hitbox_inset: float
    is_wall: bool
    destroyed: bool


@dataclass(frozen=True, slots=True)
class SplashTargetTroop:
    id: int
    position: tuple[float, float]
    destroyed: bool
    is_friendly: bool


def resolve_splash(
    *,
    center: tuple[float, float],
    radius: float,
    damage: float,
    attacker_id: int,
    buildings: Iterable[SplashTargetBuilding],
    troops: Iterable[SplashTargetTroop],
    splash_damages_walls: bool,
    hits_buildings: bool,
    hits_troops: bool,
    hits_friendly_troops: bool,
) -> list[DamageEvent]:
    """Return one DamageEvent per entity inside the splash radius.

    Iteration order is target-id ascending (PRD §7.4) for deterministic event ordering.
    """
    if radius <= 0 or damage <= 0:
        return []

    events: list[DamageEvent] = []

    if hits_buildings:
        for b in sorted(buildings, key=lambda x: x.id):
            if b.destroyed:
                continue
            if b.is_wall and not splash_damages_walls:
                continue
            d = distance_point_to_square_hitbox(center, b.origin, b.footprint, b.hitbox_inset)
            if d <= radius:
                events.append(DamageEvent(target_id=b.id, damage=damage, attacker_id=attacker_id))

    if hits_troops:
        for t in sorted(troops, key=lambda x: x.id):
            if t.destroyed:
                continue
            if t.is_friendly and not hits_friendly_troops:
                continue
            if euclidean(center, t.position) <= radius:
                events.append(DamageEvent(target_id=t.id, damage=damage, attacker_id=attacker_id))

    return events


__all__ = ["SplashTargetBuilding", "SplashTargetTroop", "resolve_splash"]
