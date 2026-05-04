"""Content loader: reads `buildings.json`, `troops.json`, `spells.json`,
optional `manual_overrides.json` and returns immutable type catalogues.

Merge order at sim startup (PRD §9.4):

    wiki scrape  ->  manual_overrides  ->  final BuildingType / TroopType / SpellType

The merge happens once per sim startup. The runtime sim never re-reads or
re-merges; the catalogue object is treated as immutable for the lifetime of
the run.

`manual_overrides.json` shape:

    {
      "schema_version": 1,
      "buildings": { "<name>": {<partial-overrides>}, ... },
      "troops":    { "<name>": {<partial-overrides>}, ... },
      "spells":    { "<name>": {<partial-overrides>}, ... }
    }

Each per-name dict may contain any subset of the corresponding schema's fields.
The `levels` list, if overridden, is merged element-wise by `level` value:
matching levels merge their fields; new levels are appended. This lets the
override file patch a single level without re-listing the whole table.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from pydantic import TypeAdapter

from sandbox_core.grid import default_hitbox_inset
from sandbox_core.schemas import BuildingType, SpellType, TroopType

DEFAULT_DATA_DIR: Path = Path(__file__).resolve().parents[1] / "data"

OVERRIDES_FILENAME = "manual_overrides.json"
TH_CAPS_FILENAME = "th_caps.json"


_BuildingListAdapter = TypeAdapter(list[BuildingType])
_TroopListAdapter = TypeAdapter(list[TroopType])
_SpellListAdapter = TypeAdapter(list[SpellType])


class ContentCatalogue:
    """Immutable catalogue of building / troop / spell types, keyed by name."""

    __slots__ = ("buildings", "spells", "troops")

    def __init__(
        self,
        buildings: dict[str, BuildingType],
        troops: dict[str, TroopType],
        spells: dict[str, SpellType],
    ) -> None:
        self.buildings = buildings
        self.troops = troops
        self.spells = spells

    def building(self, name: str) -> BuildingType:
        try:
            return self.buildings[name]
        except KeyError as e:
            raise KeyError(f"unknown building type: {name!r}") from e

    def troop(self, name: str) -> TroopType:
        try:
            return self.troops[name]
        except KeyError as e:
            raise KeyError(f"unknown troop type: {name!r}") from e

    def spell(self, name: str) -> SpellType:
        try:
            return self.spells[name]
        except KeyError as e:
            raise KeyError(f"unknown spell type: {name!r}") from e


def merge_entity_overrides(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge a single entity's override dict on top of its scraped base dict.

    Top-level fields in `override` replace those in `base`. The `levels` field,
    if present in both, is merged element-wise by `level` value: matching
    levels have their fields union-merged (override wins on conflict); new
    levels are appended in ascending `level` order.

    Pure: returns a new dict, does not mutate inputs.
    """
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if key == "levels" and "levels" in merged:
            merged["levels"] = _merge_levels(merged["levels"], value)
        else:
            merged[key] = value
    return merged


def _merge_levels(
    base_levels: list[dict[str, Any]], override_levels: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_level: dict[int, dict[str, Any]] = {int(lv["level"]): dict(lv) for lv in base_levels}
    for lv in override_levels:
        idx = int(lv["level"])
        if idx in by_level:
            by_level[idx].update(lv)
        else:
            by_level[idx] = dict(lv)
    return [by_level[k] for k in sorted(by_level)]


def apply_overrides(
    *,
    buildings: list[dict[str, Any]],
    troops: list[dict[str, Any]],
    spells: list[dict[str, Any]],
    overrides: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply `manual_overrides.json` content to scraped raw lists.

    `overrides` is the parsed `manual_overrides.json` dict. Lookup is by entity
    `name`. Entities not mentioned in the override file pass through unchanged.
    Returns (buildings, troops, spells) as raw dicts ready for Pydantic
    validation.
    """
    return (
        _apply_per_kind(buildings, overrides.get("buildings", {})),
        _apply_per_kind(troops, overrides.get("troops", {})),
        _apply_per_kind(spells, overrides.get("spells", {})),
    )


def _apply_per_kind(
    entries: list[dict[str, Any]], overrides_for_kind: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for entry in entries:
        name = entry.get("name")
        if isinstance(name, str) and name in overrides_for_kind:
            out.append(merge_entity_overrides(entry, overrides_for_kind[name]))
        else:
            out.append(entry)
    return out


def _resolve_hitbox_insets(buildings: list[BuildingType]) -> list[BuildingType]:
    out: list[BuildingType] = []
    for b in buildings:
        if b.hitbox_inset is None:
            inset = default_hitbox_inset(b.footprint)
            out.append(b.model_copy(update={"hitbox_inset": inset}))
        else:
            out.append(b)
    return out


def load_catalogue(data_dir: Path | None = None) -> ContentCatalogue:
    """Load buildings/troops/spells from `data_dir`, apply overrides, return catalogue.

    Merge order: scraped JSON -> `manual_overrides.json` (if present) -> Pydantic
    validation -> hitbox-inset defaulting -> immutable catalogue.

    Missing `spells.json` is tolerated; missing `buildings.json` or `troops.json`
    raises FileNotFoundError. Missing `manual_overrides.json` is the common case
    and skips the merge step.
    """
    base = data_dir or DEFAULT_DATA_DIR

    buildings_data = _load_entries(base / "buildings.json")
    troops_data = _load_entries(base / "troops.json")
    spells_data = _load_entries_optional(base / "spells.json")

    overrides_path = base / OVERRIDES_FILENAME
    if overrides_path.exists():
        overrides = json.loads(overrides_path.read_text(encoding="utf-8"))
        buildings_data, troops_data, spells_data = apply_overrides(
            buildings=buildings_data,
            troops=troops_data,
            spells=spells_data,
            overrides=overrides,
        )

    buildings = _resolve_hitbox_insets(_BuildingListAdapter.validate_python(buildings_data))
    troops = _TroopListAdapter.validate_python(troops_data)
    spells = _SpellListAdapter.validate_python(spells_data)

    return ContentCatalogue(
        buildings={b.name: b for b in buildings},
        troops={t.name: t for t in troops},
        spells={s.name: s for s in spells},
    )


def _load_entries(path: Path) -> list[dict[str, Any]]:
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    entries: Any = raw["entries"] if isinstance(raw, dict) and "entries" in raw else raw
    return cast(list[dict[str, Any]], entries)


def _load_entries_optional(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return _load_entries(path)


def load_th_caps(data_dir: Path | None = None) -> dict[int, dict[str, Any]]:
    """Load th_caps.json and return a dict keyed by TH level (int)."""
    base = data_dir or DEFAULT_DATA_DIR
    raw: Any = json.loads((base / TH_CAPS_FILENAME).read_text(encoding="utf-8"))
    return {int(k): v for k, v in raw["town_hall_levels"].items()}


__all__ = [
    "DEFAULT_DATA_DIR",
    "OVERRIDES_FILENAME",
    "TH_CAPS_FILENAME",
    "ContentCatalogue",
    "apply_overrides",
    "load_catalogue",
    "load_th_caps",
    "merge_entity_overrides",
]
