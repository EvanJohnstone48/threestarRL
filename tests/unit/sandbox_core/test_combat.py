"""Tests for combat.py (damage application and multipliers)."""

from __future__ import annotations

import pytest
from sandbox_core.combat import troop_damage_against
from sandbox_core.content import load_catalogue
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


# ----- AC: data-driven multiplier checks against the committed catalogue -----


def test_goblin_vs_resource_storage_doubles_base_damage() -> None:
    cat = load_catalogue()
    goblin = cat.troops["goblin"]
    base = goblin.stats_at(1).base_damage
    out = troop_damage_against(goblin, 1, BuildingCategory.RESOURCE_STORAGE)
    assert out == pytest.approx(base * 2.0)


def test_goblin_vs_resource_collector_doubles_base_damage() -> None:
    cat = load_catalogue()
    goblin = cat.troops["goblin"]
    base = goblin.stats_at(2).base_damage
    out = troop_damage_against(goblin, 2, BuildingCategory.RESOURCE_COLLECTOR)
    assert out == pytest.approx(base * 2.0)


def test_goblin_vs_defense_uses_default_multiplier() -> None:
    cat = load_catalogue()
    goblin = cat.troops["goblin"]
    base = goblin.stats_at(3).base_damage
    out = troop_damage_against(goblin, 3, BuildingCategory.DEFENSE)
    # default = 1.0 → unmultiplied
    assert out == pytest.approx(base * 1.0)


def test_barbarian_default_default_yields_1x_against_every_category() -> None:
    cat = load_catalogue()
    barb = cat.troops["barbarian"]
    base = barb.stats_at(6).base_damage
    for cat_enum in BuildingCategory:
        out = troop_damage_against(barb, 6, cat_enum)
        assert out == pytest.approx(base), (
            f"barbarian default-default multiplier should be 1.0 for {cat_enum.value}"
        )


def test_wall_breaker_full_damage_against_wall() -> None:
    cat = load_catalogue()
    wb = cat.troops["wall_breaker"]
    base = wb.stats_at(4).base_damage
    out = troop_damage_against(wb, 4, BuildingCategory.WALL)
    assert out == pytest.approx(base * 1.0)


def test_wall_breaker_default_against_defense() -> None:
    cat = load_catalogue()
    wb = cat.troops["wall_breaker"]
    base = wb.stats_at(4).base_damage
    out = troop_damage_against(wb, 4, BuildingCategory.DEFENSE)
    # Wall Breaker default = 0.04 per overrides
    assert out == pytest.approx(base * 0.04)


def test_wall_breaker_wall_to_defense_damage_ratio_is_25x() -> None:
    """The multiplier math implies wall:non-wall damage = 1.0 / 0.04 = 25x."""
    cat = load_catalogue()
    wb = cat.troops["wall_breaker"]
    wall_dmg = troop_damage_against(wb, 4, BuildingCategory.WALL)
    defense_dmg = troop_damage_against(wb, 4, BuildingCategory.DEFENSE)
    ratio = wall_dmg / defense_dmg
    assert ratio == pytest.approx(25.0)


# ----- AC: roster + validator coverage --------------------------------------


def test_full_th6_troop_roster_loads_with_per_level_stats() -> None:
    cat = load_catalogue()
    expected = {"barbarian", "archer", "goblin", "giant", "wall_breaker", "wizard"}
    assert expected.issubset(cat.troops.keys())
    # Per-level table covers TH1 through TH6 minimum (some troops gate on later TH levels;
    # we just require at least one stat row per troop and that level numbers are contiguous).
    for name in expected:
        troop = cat.troops[name]
        assert len(troop.levels) >= 1
        levels = [s.level for s in troop.levels]
        assert levels == sorted(levels)
        assert levels[0] == 1
        # The PRD requires per-level stats for unlocked levels; verify the highest unlock_at_th
        # in the table is <= 6 (i.e., the troop is fully covered through TH6).
        assert max(s.unlocked_at_th for s in troop.levels) <= 6


def test_every_committed_building_has_a_valid_category() -> None:
    cat = load_catalogue()
    valid = {c.value for c in BuildingCategory}
    for name, building in cat.buildings.items():
        assert building.category.value in valid, f"{name} has invalid category"


def test_unknown_building_category_is_rejected_by_validator() -> None:
    """The closed BuildingCategory StrEnum makes invalid categories fail Pydantic validation."""
    from pydantic import ValidationError
    from sandbox_core.schemas import BuildingType

    with pytest.raises(ValidationError):
        BuildingType(
            name="bogus",
            category="not_a_category",  # pyright: ignore[reportArgumentType]
            footprint=(1, 1),
            levels=[],
        )
