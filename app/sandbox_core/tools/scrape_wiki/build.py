"""Build canonical schema-shaped dicts from parsed wiki HTML.

This is the bridge layer between `parse.WikiTable` / `parse.extract_infobox`
output and the BuildingType / TroopType / SpellType payload shapes that
`schemas.py` validates. Pure-functional: takes parsed dicts in, returns
plain dicts out.

Scope notes:

  - Per PRD §9.6, missing fields fall back to `None` rather than raising.
    The validator (in `output.validate_and_write`) decides whether `None` for
    a required field is fatal. The hand-curated `manual_overrides.json` is
    the documented gap-filling layer.
  - The wiki rarely tags fields with category/footprint/target_filter
    machine-readably; these come from the curated `BUILDING_STATIC` map below
    rather than from HTML scraping. That is by design — they are intrinsic
    properties of the entity, not stats that change with patches.
"""

from __future__ import annotations

from typing import Any, Final

from sandbox_core.tools.scrape_wiki.normalize import (
    attack_speed_to_ticks,
    normalize_column,
)
from sandbox_core.tools.scrape_wiki.parse import WikiTable, parse_number

# Static (non-stats) properties of TH6 entities. These are intrinsic to the
# entity rather than scraped from a level table, and the wiki encodes them
# inconsistently across pages. Keeping them in code (with `manual_overrides`
# as the v1 escape hatch) is simpler than fragile HTML extraction.
BUILDING_STATIC: Final[dict[str, dict[str, Any]]] = {
    "town_hall": {"category": "town_hall", "footprint": [4, 4]},
    "clan_castle": {"category": "clan_castle", "footprint": [3, 3]},
    "cannon": {
        "category": "defense",
        "footprint": [3, 3],
        "target_filter": "ground",
        "projectile_speed_tiles_per_sec": 20.0,
    },
    "archer_tower": {
        "category": "defense",
        "footprint": [3, 3],
        "target_filter": "both",
        "projectile_speed_tiles_per_sec": 25.0,
    },
    "mortar": {
        "category": "defense",
        "footprint": [3, 3],
        "target_filter": "ground",
        "projectile_speed_tiles_per_sec": 8.0,
        "projectile_homing": False,
        "splash_radius_tiles": 1.5,
        "min_range_tiles": 4.0,
    },
    "air_defense": {
        "category": "defense",
        "footprint": [3, 3],
        "target_filter": "air",
        "projectile_speed_tiles_per_sec": 22.0,
    },
    "wizard_tower": {
        "category": "defense",
        "footprint": [3, 3],
        "target_filter": "both",
        "projectile_speed_tiles_per_sec": 18.0,
        "splash_radius_tiles": 1.0,
    },
    "wall": {"category": "wall", "footprint": [1, 1], "is_wall": True},
    "army_camp": {"category": "army", "footprint": [4, 4]},
    "barracks": {"category": "army", "footprint": [3, 3]},
    "laboratory": {"category": "army", "footprint": [3, 3]},
    "spell_factory": {"category": "army", "footprint": [3, 3]},
    "gold_mine": {"category": "resource_collector", "footprint": [3, 3]},
    "elixir_collector": {"category": "resource_collector", "footprint": [3, 3]},
    "gold_storage": {"category": "resource_storage", "footprint": [3, 3]},
    "elixir_storage": {"category": "resource_storage", "footprint": [3, 3]},
    "builders_hut": {"category": "builder_hut", "footprint": [2, 2]},
}

TROOP_STATIC: Final[dict[str, dict[str, Any]]] = {
    "barbarian": {"housing_space": 1, "speed_tiles_per_sec": 1.6},
    "archer": {
        "housing_space": 1,
        "speed_tiles_per_sec": 2.4,
        "target_filter": "both",
    },
    "goblin": {
        "housing_space": 1,
        "speed_tiles_per_sec": 3.2,
        "target_preference": "resources",
        "damage_multipliers": {"resource_collector": 2.0, "resource_storage": 2.0},
    },
    "giant": {
        "housing_space": 5,
        "speed_tiles_per_sec": 1.25,
        "target_preference": "defenses",
    },
    "wall_breaker": {
        "housing_space": 2,
        "speed_tiles_per_sec": 2.4,
        "target_preference": "walls",
        "damages_walls_on_suicide": True,
        "splash_radius_tiles": 1.5,
        "splash_damages_walls": True,
        "damage_multipliers": {"wall": 1.0},
    },
    "wizard": {
        "housing_space": 4,
        "speed_tiles_per_sec": 2.4,
        "target_filter": "both",
        "splash_radius_tiles": 0.3,
        "splash_damages_walls": True,
        "projectile_speed_tiles_per_sec": 16.0,
    },
}


def _normalized_rows(table: WikiTable) -> list[dict[str, float | int]]:
    """Apply `normalize_column` to a parsed WikiTable; drop unknown columns."""
    out: list[dict[str, float | int]] = []
    for raw_row in table.rows:
        row: dict[str, float | int] = {}
        for raw_header, raw_value in raw_row.items():
            try:
                canonical = normalize_column(raw_header)
            except KeyError:
                continue  # drop unknown columns; PRD §9.6 expects warnings at caller
            if canonical is None:
                continue
            num = parse_number(raw_value)
            if num is None:
                continue
            if canonical == "attack_cooldown_ticks":
                row[canonical] = attack_speed_to_ticks(num)
            elif canonical in ("level", "unlocked_at_th"):
                row[canonical] = int(num)
            else:
                row[canonical] = num
        if "level" in row:
            out.append(row)
    return out


def build_building(name: str, table: WikiTable | None) -> dict[str, Any]:
    """Build a BuildingType-shaped dict from static + parsed-level data."""
    static = dict(BUILDING_STATIC.get(name, {}))
    levels = _normalized_rows(table) if table else []
    return {
        "name": name,
        **static,
        "levels": levels,
    }


def build_troop(name: str, table: WikiTable | None) -> dict[str, Any]:
    """Build a TroopType-shaped dict from static + parsed-level data."""
    static = dict(TROOP_STATIC.get(name, {}))
    levels = _normalized_rows(table) if table else []
    return {
        "name": name,
        **static,
        "levels": levels,
    }


def build_spell(name: str, table: WikiTable | None) -> dict[str, Any]:
    """Build a SpellType-shaped dict from parsed level data.

    Lightning Spell static fields (radius_tiles=3.0, hit_interval_ticks=1,
    num_hits=*from-page*, damages_walls=False) are not on the wiki page in a
    machine-readable format; defaults are filled by `manual_overrides.json`
    when the scraper output passes through the runtime loader.
    """
    levels = _normalized_rows(table) if table else []
    return {"name": name, "levels": levels}


__all__ = [
    "BUILDING_STATIC",
    "TROOP_STATIC",
    "build_building",
    "build_spell",
    "build_troop",
]
