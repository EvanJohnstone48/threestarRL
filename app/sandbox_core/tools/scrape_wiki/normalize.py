"""Stat-name normalization per PRD §9.5.

Wiki tables use inconsistent column headers across different entity pages
(e.g. "Damage per Hit" vs "Damage per Shot" vs "Damage per Attack" all mean
the same thing in our schema). This module is the single source of truth for
mapping wiki headers to canonical schema field names.

Rules:

  - `COLUMN_NORMALIZATIONS` maps wiki header (case- and whitespace-normalized)
    to a canonical schema field name. `None` means "drop this column".
  - `attack_speed_to_ticks(seconds)` converts the wiki's "Attack Speed (sec)"
    column to our integer-tick `attack_cooldown_ticks` field.
  - `DROPPED_COLUMNS` is a derived view used by tests.

Adding a new column normalization is a one-line edit. Each rule has a unit
test in `tests/unit/sandbox_core/tools/scrape_wiki/test_normalize.py`.
"""

from __future__ import annotations

from typing import Final


def _key(header: str) -> str:
    """Lowercase + strip + collapse internal whitespace for stable lookups."""
    return " ".join(header.lower().split())


# raw wiki header  ->  canonical field name (or None to drop)
COLUMN_NORMALIZATIONS: Final[dict[str, str | None]] = {
    # Damage variants
    _key("Damage per Hit"): "damage_per_shot",
    _key("Damage per Shot"): "damage_per_shot",
    _key("Damage per Attack"): "damage_per_shot",
    _key("Damage per Second"): None,  # DPS is derivable; drop
    _key("DPS"): None,
    # HP / lifetime
    _key("Hitpoints"): "hp",
    _key("HP"): "hp",
    _key("Health"): "hp",
    # Range
    _key("Range"): "range_tiles",
    _key("Attack Range"): "range_tiles",
    # Attack speed (handled specially via attack_speed_to_ticks)
    _key("Attack Speed"): "attack_cooldown_ticks",
    _key("Attack Speed (sec)"): "attack_cooldown_ticks",
    _key("Attack Speed (seconds)"): "attack_cooldown_ticks",
    # Level / unlock
    _key("Level"): "level",
    _key("Town Hall Level Required"): "unlocked_at_th",
    _key("Town Hall Required"): "unlocked_at_th",
    _key("Required Town Hall Level"): "unlocked_at_th",
    # Lightning Spell
    _key("Damage"): "damage_per_hit",
    # Misc commonly-noisy columns we drop entirely
    _key("Build Cost"): None,
    _key("Build Time"): None,
    _key("Research Cost"): None,
    _key("Research Time"): None,
    _key("Training Cost"): None,
    _key("Training Time"): None,
    _key("Housing Space"): "housing_space",
    _key("Movement Speed"): "speed_tiles_per_sec",
    _key("Speed"): "speed_tiles_per_sec",
}


DROPPED_COLUMNS: Final[frozenset[str]] = frozenset(
    k for k, v in COLUMN_NORMALIZATIONS.items() if v is None
)


def normalize_column(header: str) -> str | None:
    """Return canonical field name, or `None` to drop the column.

    Raises `KeyError` for any header not in `COLUMN_NORMALIZATIONS`. Callers
    that scrape wiki pages with an unrecognized column should add a rule here
    rather than silently dropping data — see PRD §9.6 (defensive parsing logs
    a warning at the call site).
    """
    return COLUMN_NORMALIZATIONS[_key(header)]


def attack_speed_to_ticks(seconds: float) -> int:
    """Convert wiki's "Attack Speed (sec)" to integer tick cooldown.

    PRD §9.5: `attack_cooldown_ticks = round(seconds * 10)`. Tied to the
    sim's 10 Hz tick rate.
    """
    if seconds < 0:
        raise ValueError(f"attack speed must be non-negative, got {seconds}")
    return round(seconds * 10)


__all__ = [
    "COLUMN_NORMALIZATIONS",
    "DROPPED_COLUMNS",
    "attack_speed_to_ticks",
    "normalize_column",
]
