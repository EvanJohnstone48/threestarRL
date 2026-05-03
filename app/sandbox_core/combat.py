"""Pure-functional damage application.

`apply_damage` computes the damage a single attack deals against a single target,
honoring the troop's per-category multiplier table. No state — returns a damage event.
"""

from __future__ import annotations

from dataclasses import dataclass

from sandbox_core.schemas import BuildingCategory, BuildingType, TroopType


@dataclass(frozen=True, slots=True)
class DamageEvent:
    target_id: int
    damage: float
    attacker_id: int


def troop_damage_against(
    troop: TroopType,
    troop_level: int,
    target_category: BuildingCategory,
) -> float:
    """Final per-attack damage from a troop against a target with the given category.

    Formula (PRD §5.5):
      damage = troop.base_damage_at_level * troop.damage_multipliers.get(category, default)
    """
    base = troop.stats_at(troop_level).base_damage
    multiplier = troop.damage_multipliers.get(
        target_category.value, troop.damage_multiplier_default
    )
    return base * multiplier


def defense_damage(building: BuildingType, level: int) -> float:
    """Defenses apply flat damage_per_shot — no multipliers."""
    return building.stats_at(level).damage_per_shot


def apply_damage(
    target_id: int,
    attacker_id: int,
    damage: float,
) -> DamageEvent:
    """Construct a DamageEvent. Pure helper; HP subtraction happens in the sim step."""
    return DamageEvent(target_id=target_id, damage=damage, attacker_id=attacker_id)


__all__ = ["DamageEvent", "apply_damage", "defense_damage", "troop_damage_against"]
