"""Tests for combat.py (damage application and multipliers)."""

from __future__ import annotations

from sandbox_core.combat import troop_damage_against
from sandbox_core.schemas import (
    BuildingCategory,
    TroopLevelStats,
    TroopType,
)


def _troop(
    multipliers: dict[str, float] | None = None, default: float = 1.0, base: float = 10.0
) -> TroopType:
    return TroopType(
        name="x",
        levels=[
            TroopLevelStats(
                level=1, hp=10, base_damage=base, range_tiles=0.5, attack_cooldown_ticks=10
            )
        ],
        damage_multipliers=multipliers or {},
        damage_multiplier_default=default,
    )


def test_default_multiplier_applies_when_category_absent() -> None:
    troop = _troop(multipliers={"resource_collector": 2.0}, default=1.0, base=10.0)
    assert troop_damage_against(troop, 1, BuildingCategory.DEFENSE) == 10.0


def test_explicit_multiplier_overrides_default() -> None:
    troop = _troop(multipliers={"resource_collector": 2.0}, default=1.0, base=10.0)
    assert troop_damage_against(troop, 1, BuildingCategory.RESOURCE_COLLECTOR) == 20.0


def test_wall_breaker_like_low_default_high_wall() -> None:
    wb = _troop(multipliers={"wall": 1.0}, default=0.04, base=200.0)
    assert troop_damage_against(wb, 1, BuildingCategory.WALL) == 200.0
    # Against a non-wall: base * 0.04
    expected = 200.0 * 0.04
    assert abs(troop_damage_against(wb, 1, BuildingCategory.DEFENSE) - expected) < 1e-9
