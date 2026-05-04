"""Hard-coded entity list per PRD §9.7.

Every entity scraped at v1 lives here. Adding a TH7+ entity at later phases
means appending to this list. The URL slugs match the canonical Fan Wiki page
titles (with `_` for spaces, e.g. `Town_Hall`, `Wall_Breaker`, `Wizard_Tower`).
"""

from __future__ import annotations

from typing import Final, Literal

WIKI_BASE: Final[str] = "https://clashofclans.fandom.com/wiki"
TROOP_MOVEMENT_URL: Final[str] = f"{WIKI_BASE}/Troop_Movement_Speed"

EntityKind = Literal["building", "troop", "spell"]


# (canonical_name, wiki_slug) — canonical_name is the snake_case key used in
# our JSONs; wiki_slug is the page-title fragment under /wiki/.
BUILDING_ENTITIES: Final[tuple[tuple[str, str], ...]] = (
    ("town_hall", "Town_Hall"),
    ("clan_castle", "Clan_Castle"),
    ("cannon", "Cannon"),
    ("archer_tower", "Archer_Tower"),
    ("mortar", "Mortar"),
    ("air_defense", "Air_Defense"),
    ("wizard_tower", "Wizard_Tower"),
    ("wall", "Wall"),
    ("army_camp", "Army_Camp"),
    ("barracks", "Barracks"),
    ("laboratory", "Laboratory"),
    ("spell_factory", "Spell_Factory"),
    ("gold_mine", "Gold_Mine"),
    ("elixir_collector", "Elixir_Collector"),
    ("gold_storage", "Gold_Storage"),
    ("elixir_storage", "Elixir_Storage"),
    ("builders_hut", "Builder%27s_Hut"),
)

TROOP_ENTITIES: Final[tuple[tuple[str, str], ...]] = (
    ("barbarian", "Barbarian"),
    ("archer", "Archer"),
    ("goblin", "Goblin"),
    ("giant", "Giant"),
    ("wall_breaker", "Wall_Breaker"),
    ("wizard", "Wizard"),
)

SPELL_ENTITIES: Final[tuple[tuple[str, str], ...]] = (("lightning_spell", "Lightning_Spell"),)


def entity_url(slug: str) -> str:
    """Return the absolute Fan Wiki URL for an entity slug."""
    return f"{WIKI_BASE}/{slug}"


def all_entities() -> tuple[tuple[str, str, EntityKind], ...]:
    out: list[tuple[str, str, EntityKind]] = []
    for name, slug in BUILDING_ENTITIES:
        out.append((name, slug, "building"))
    for name, slug in TROOP_ENTITIES:
        out.append((name, slug, "troop"))
    for name, slug in SPELL_ENTITIES:
        out.append((name, slug, "spell"))
    return tuple(out)


__all__ = [
    "BUILDING_ENTITIES",
    "SPELL_ENTITIES",
    "TROOP_ENTITIES",
    "TROOP_MOVEMENT_URL",
    "WIKI_BASE",
    "EntityKind",
    "all_entities",
    "entity_url",
]
