"""Tests for `scrape_wiki.build` — assembling schema-shaped dicts."""

from __future__ import annotations

from sandbox_core.tools.scrape_wiki.build import (
    BUILDING_STATIC,
    TROOP_STATIC,
    build_building,
    build_spell,
    build_troop,
)
from sandbox_core.tools.scrape_wiki.parse import WikiTable


def _make_table(headers: list[str], rows: list[list[str]]) -> WikiTable:
    table = WikiTable(headers=headers)
    for r in rows:
        table.rows.append(dict(zip(headers, r, strict=True)))
    return table


def test_build_building_normalizes_columns_and_drops_dps() -> None:
    table = _make_table(
        headers=[
            "Level",
            "Damage per Shot",
            "DPS",
            "Hitpoints",
            "Range",
            "Attack Speed (sec)",
            "Town Hall Level Required",
        ],
        rows=[
            ["1", "9", "11.25", "420", "9", "0.8", "1"],
            ["6", "25", "31.25", "670", "9", "0.8", "6"],
        ],
    )
    result = build_building("cannon", table)
    assert result["name"] == "cannon"
    assert result["category"] == "defense"
    assert result["footprint"] == [3, 3]
    assert len(result["levels"]) == 2
    lv1 = result["levels"][0]
    assert lv1["level"] == 1
    assert lv1["damage_per_shot"] == 9.0
    assert lv1["hp"] == 420.0
    assert lv1["range_tiles"] == 9.0
    assert lv1["attack_cooldown_ticks"] == 8  # 0.8s * 10
    assert lv1["unlocked_at_th"] == 1
    assert "dps" not in lv1
    assert "damage_per_second" not in lv1


def test_build_building_static_fields_present() -> None:
    """Sanity: every TH6 building has a category + footprint in static map."""
    expected_names = set(BUILDING_STATIC)
    assert "town_hall" in expected_names
    assert "wall" in expected_names
    assert BUILDING_STATIC["wall"]["is_wall"] is True
    assert BUILDING_STATIC["mortar"]["splash_radius_tiles"] == 1.5
    assert BUILDING_STATIC["mortar"]["projectile_homing"] is False


def test_build_troop_inherits_static_multipliers() -> None:
    table = _make_table(
        headers=["Level", "Damage per Hit", "Hitpoints", "Range", "Attack Speed (sec)"],
        rows=[["1", "11", "25", "0.4", "1.0"]],
    )
    result = build_troop("goblin", table)
    assert result["damage_multipliers"] == {"resource_collector": 2.0, "resource_storage": 2.0}
    assert result["target_preference"] == "resources"


def test_build_troop_wall_breaker_static() -> None:
    """Wall Breaker static map carries the suicide + wall multiplier flags."""
    static = TROOP_STATIC["wall_breaker"]
    assert static["damages_walls_on_suicide"] is True
    assert static["splash_damages_walls"] is True
    assert static["damage_multipliers"] == {"wall": 1.0}


def test_build_troop_no_table_yields_empty_levels() -> None:
    result = build_troop("barbarian", None)
    assert result["levels"] == []
    assert result["name"] == "barbarian"


def test_build_spell() -> None:
    table = _make_table(
        headers=["Level", "Damage", "Town Hall Required"],
        rows=[["1", "150", "5"], ["3", "210", "6"]],
    )
    result = build_spell("lightning_spell", table)
    assert result["name"] == "lightning_spell"
    assert len(result["levels"]) == 2
    assert result["levels"][0]["damage_per_hit"] == 150.0
    assert result["levels"][1]["unlocked_at_th"] == 6
