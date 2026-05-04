"""Wiki scraper package for sandbox-core content data files.

Produces `app/data/{buildings,troops,spells,th_caps}.json` from the Clash of
Clans Fan Wiki (https://clashofclans.fandom.com), per PRD §9.

The package is deliberately split into small testable modules:

  - `entities`       : the hard-coded TH6 entity list and URL builders (§9.7).
  - `normalize`      : `COLUMN_NORMALIZATIONS` and `attack_speed_to_ticks` (§9.5).
  - `cache`          : on-disk HTML cache + per-page metadata (§9.3).
  - `parse`          : stdlib HTML parsing primitives — wikitable extraction.
  - `build`          : assembles BuildingType/TroopType/SpellType payloads.

The CLI (`__main__.py`) is the orchestrator. In environments without network
access it falls back to a "validate and re-emit" mode that reads the committed
JSON files, validates them through the schemas, and writes them back — keeping
reruns byte-identical.
"""

from sandbox_core.tools.scrape_wiki.entities import (
    BUILDING_ENTITIES,
    SPELL_ENTITIES,
    TROOP_ENTITIES,
    entity_url,
)
from sandbox_core.tools.scrape_wiki.normalize import (
    COLUMN_NORMALIZATIONS,
    DROPPED_COLUMNS,
    attack_speed_to_ticks,
    normalize_column,
)

__all__ = [
    "BUILDING_ENTITIES",
    "COLUMN_NORMALIZATIONS",
    "DROPPED_COLUMNS",
    "SPELL_ENTITIES",
    "TROOP_ENTITIES",
    "attack_speed_to_ticks",
    "entity_url",
    "normalize_column",
]
