"""Tests for `content.py` — load + manual_overrides merge layer (PRD §9.4)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from sandbox_core.content import (
    apply_overrides,
    load_catalogue,
    merge_entity_overrides,
)

# ----------------------------------------------------------------- pure merge


def test_merge_top_level_field_replaces() -> None:
    base = {"name": "cannon", "category": "defense", "splash_radius_tiles": 0.0}
    override = {"splash_radius_tiles": 1.5}
    out = merge_entity_overrides(base, override)
    assert out == {"name": "cannon", "category": "defense", "splash_radius_tiles": 1.5}


def test_merge_does_not_mutate_inputs() -> None:
    base = {"levels": [{"level": 1, "hp": 100}]}
    override = {"levels": [{"level": 1, "hp": 200}]}
    merge_entity_overrides(base, override)
    assert base == {"levels": [{"level": 1, "hp": 100}]}
    assert override == {"levels": [{"level": 1, "hp": 200}]}


def test_merge_levels_by_level_value() -> None:
    base = {
        "levels": [
            {"level": 1, "hp": 100, "damage_per_shot": 5},
            {"level": 2, "hp": 200, "damage_per_shot": 10},
        ]
    }
    override = {
        "levels": [
            {"level": 2, "hp": 250},  # patches level 2's hp only
            {"level": 3, "hp": 300, "damage_per_shot": 15},  # appends new level 3
        ]
    }
    out = merge_entity_overrides(base, override)
    levels = out["levels"]
    assert levels == [
        {"level": 1, "hp": 100, "damage_per_shot": 5},
        {"level": 2, "hp": 250, "damage_per_shot": 10},  # damage preserved from base
        {"level": 3, "hp": 300, "damage_per_shot": 15},
    ]


def test_merge_skips_levels_when_override_lacks_them() -> None:
    base = {"levels": [{"level": 1, "hp": 100}], "category": "defense"}
    override = {"category": "army"}
    out = merge_entity_overrides(base, override)
    assert out["levels"] == [{"level": 1, "hp": 100}]
    assert out["category"] == "army"


# -------------------------------------------------------- apply_overrides API


def test_apply_overrides_only_named_entities() -> None:
    buildings = [
        {"name": "cannon", "category": "defense"},
        {"name": "town_hall", "category": "town_hall"},
    ]
    overrides = {"buildings": {"cannon": {"category": "army"}}}
    b, _, _, _ = apply_overrides(
        buildings=buildings, troops=[], spells=[], traps=[], overrides=overrides
    )
    assert b[0]["category"] == "army"
    assert b[1]["category"] == "town_hall"


def test_apply_overrides_handles_empty_override_doc() -> None:
    b, t, s, tr = apply_overrides(
        buildings=[{"name": "x"}], troops=[{"name": "y"}], spells=[], traps=[], overrides={}
    )
    assert b == [{"name": "x"}]
    assert t == [{"name": "y"}]
    assert s == []
    assert tr == []


def test_apply_overrides_skips_unknown_entity_names() -> None:
    """Override entries for entities not in the scraped list are silently skipped."""
    overrides = {"troops": {"unknown_troop": {"hp": 999}}}
    _, t, _, _ = apply_overrides(
        buildings=[], troops=[{"name": "barbarian"}], spells=[], traps=[], overrides=overrides
    )
    assert t == [{"name": "barbarian"}]


# ----------------------------------------------- end-to-end load_catalogue


@pytest.fixture
def synthetic_data_dir(tmp_path: Path) -> Path:
    """Minimal data dir with one building + one troop, no overrides."""
    data: dict[str, Any] = {
        "buildings.json": {
            "schema_version": 1,
            "entries": [
                {
                    "name": "cannon",
                    "category": "defense",
                    "footprint": [3, 3],
                    "target_filter": "ground",
                    "projectile_speed_tiles_per_sec": 20.0,
                    "levels": [
                        {
                            "level": 1,
                            "hp": 420,
                            "damage_per_shot": 9,
                            "range_tiles": 9,
                            "attack_cooldown_ticks": 8,
                            "unlocked_at_th": 1,
                        }
                    ],
                }
            ],
        },
        "troops.json": {
            "schema_version": 1,
            "entries": [
                {
                    "name": "barbarian",
                    "category": "ground",
                    "footprint": [1, 1],
                    "speed_tiles_per_sec": 1.6,
                    "levels": [
                        {
                            "level": 1,
                            "hp": 45,
                            "base_damage": 8,
                            "range_tiles": 0.4,
                            "attack_cooldown_ticks": 10,
                            "unlocked_at_th": 1,
                        }
                    ],
                }
            ],
        },
    }
    for name, payload in data.items():
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")
    return tmp_path


def test_load_catalogue_no_overrides(synthetic_data_dir: Path) -> None:
    cat = load_catalogue(synthetic_data_dir)
    assert "cannon" in cat.buildings
    assert "barbarian" in cat.troops
    assert cat.spells == {}


def test_load_catalogue_applies_overrides(synthetic_data_dir: Path) -> None:
    overrides = {
        "schema_version": 1,
        "buildings": {"cannon": {"splash_radius_tiles": 1.5}},
        "troops": {"barbarian": {"damage_multiplier_default": 0.5}},
    }
    (synthetic_data_dir / "manual_overrides.json").write_text(
        json.dumps(overrides), encoding="utf-8"
    )
    cat = load_catalogue(synthetic_data_dir)
    assert cat.buildings["cannon"].splash_radius_tiles == 1.5
    assert cat.troops["barbarian"].damage_multiplier_default == 0.5


def test_load_catalogue_overrides_levels_merge(synthetic_data_dir: Path) -> None:
    """Level-list override patches a single level's hp without dropping other fields."""
    overrides = {
        "schema_version": 1,
        "buildings": {
            "cannon": {
                "levels": [{"level": 1, "hp": 999}]  # patch hp only
            }
        },
    }
    (synthetic_data_dir / "manual_overrides.json").write_text(
        json.dumps(overrides), encoding="utf-8"
    )
    cat = load_catalogue(synthetic_data_dir)
    cannon = cat.buildings["cannon"]
    lv1 = cannon.stats_at(1)
    assert lv1.hp == 999
    assert lv1.damage_per_shot == 9  # preserved


def test_committed_data_dir_loads_with_overrides() -> None:
    """The actual `app/data/` validates and merges cleanly (smoke check)."""
    cat = load_catalogue()
    assert "cannon" in cat.buildings
    assert "wall_breaker" in cat.troops
    assert "lightning_spell" in cat.spells
    # The committed manual_overrides.json overrides Army Camp + Wall hitbox_inset.
    army_camp = cat.buildings["army_camp"]
    assert army_camp.hitbox_inset == 1.0
    wall = cat.buildings["wall"]
    assert wall.hitbox_inset == 0.0
    # Wall Breaker's damage_multiplier_default applies via override.
    wb = cat.troops["wall_breaker"]
    assert abs(wb.damage_multiplier_default - 0.04) < 1e-9
    assert wb.damage_multipliers == {"wall": 1.0}
    assert wb.damages_walls_on_suicide is True
