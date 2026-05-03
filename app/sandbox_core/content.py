"""Content loader: reads `buildings.json`, `troops.json`, optional `spells.json`,
optional `manual_overrides.json` and returns immutable type catalogues.

In Phase 0, the catalogue is hand-written 2-entity placeholder data (Town Hall +
Cannon, Barbarian + Giant). Issue 004 replaces these with scraped wiki output and
adds the manual_overrides merge layer.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter

from sandbox_core.grid import default_hitbox_inset
from sandbox_core.schemas import BuildingType, SpellType, TroopType

DEFAULT_DATA_DIR: Path = Path(__file__).resolve().parents[1] / "data"


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
    """Load buildings/troops/spells from `data_dir` and return a frozen catalogue.

    Missing spells.json is tolerated (Phase 0 has no spells); missing buildings.json
    or troops.json raises FileNotFoundError.
    """
    base = data_dir or DEFAULT_DATA_DIR

    buildings_raw = json.loads((base / "buildings.json").read_text(encoding="utf-8"))
    troops_raw = json.loads((base / "troops.json").read_text(encoding="utf-8"))

    buildings_data = buildings_raw["entries"] if isinstance(buildings_raw, dict) else buildings_raw
    troops_data = troops_raw["entries"] if isinstance(troops_raw, dict) else troops_raw

    buildings = _resolve_hitbox_insets(_BuildingListAdapter.validate_python(buildings_data))
    troops = _TroopListAdapter.validate_python(troops_data)

    spells_path = base / "spells.json"
    spells: list[SpellType]
    if spells_path.exists():
        spells_raw = json.loads(spells_path.read_text(encoding="utf-8"))
        spells_data = spells_raw["entries"] if isinstance(spells_raw, dict) else spells_raw
        spells = _SpellListAdapter.validate_python(spells_data)
    else:
        spells = []

    return ContentCatalogue(
        buildings={b.name: b for b in buildings},
        troops={t.name: t for t in troops},
        spells={s.name: s for s in spells},
    )


__all__ = ["DEFAULT_DATA_DIR", "ContentCatalogue", "load_catalogue"]
