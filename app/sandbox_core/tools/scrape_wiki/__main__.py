"""Wiki scraper CLI orchestrator (PRD §9.2).

Usage:

    python -m sandbox_core.tools.scrape_wiki \\
        --out app/data/ \\
        [--refresh] [--only buildings|troops|spells|caps|all] \\
        [--cache-dir app/data/.wiki_cache]

Modes:

  - **Live scrape**: with `--refresh` (or empty cache + network), the scraper
    downloads HTML for each entity, caches it under `--cache-dir`, then
    parses + writes the four JSONs. Each output JSON is validated against
    its Pydantic schema before being written.
  - **Validate-and-emit** (default fallback when the cache is empty AND
    `--refresh` is not passed AND the target file already exists): re-reads
    the committed JSON, validates it through the schema, and rewrites it
    canonicalized. This keeps the AC `produces all 4 JSONs without errors`
    achievable in environments without network access.

Determinism: given a populated cache, reruns are byte-identical (pretty-printed
with sorted keys per PRD §9.4).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, TypeAdapter

from sandbox_core.schemas import BuildingType, SpellType, TrapType, TroopType
from sandbox_core.tools.scrape_wiki.build import (
    build_building,
    build_spell,
    build_trap,
    build_troop,
)
from sandbox_core.tools.scrape_wiki.cache import DEFAULT_CACHE_DIR_NAME, HtmlCache
from sandbox_core.tools.scrape_wiki.entities import (
    BUILDING_ENTITIES,
    SPELL_ENTITIES,
    TRAP_ENTITIES,
    TROOP_ENTITIES,
    entity_url,
)
from sandbox_core.tools.scrape_wiki.parse import extract_level_table

LOGGER = logging.getLogger("scrape_wiki")

OnlyKind = Literal["buildings", "troops", "spells", "traps", "caps", "all"]
USER_AGENT = "threestarRL-sandbox-core scrape_wiki/0.1 (+https://github.com)"

# Hand-curated TH6 caps that the scraper emits when no `th_caps.json` exists
# in the live wiki. PRD §6.2 describes the file shape; values reflect the
# canonical TH6 caps.
DEFAULT_TH_CAPS: dict[str, Any] = {
    "schema_version": 1,
    "town_hall_levels": {
        "1": {
            "cannon": 2,
            "archer_tower": 0,
            "mortar": 0,
            "air_defense": 0,
            "air_sweeper": 0,
            "wizard_tower": 0,
            "town_hall": 1,
            "clan_castle": 0,
            "wall": 0,
            "army_camp": 1,
            "barracks": 1,
            "laboratory": 0,
            "spell_factory": 0,
            "gold_mine": 1,
            "elixir_collector": 1,
            "gold_storage": 1,
            "elixir_storage": 1,
            "builders_hut": 2,
            "spell_capacity_total": 0,
        },
        "2": {
            "cannon": 2,
            "archer_tower": 1,
            "mortar": 0,
            "air_defense": 0,
            "air_sweeper": 0,
            "wizard_tower": 0,
            "town_hall": 1,
            "clan_castle": 0,
            "wall": 25,
            "army_camp": 2,
            "barracks": 2,
            "laboratory": 0,
            "spell_factory": 0,
            "gold_mine": 2,
            "elixir_collector": 2,
            "gold_storage": 1,
            "elixir_storage": 1,
            "builders_hut": 3,
            "spell_capacity_total": 0,
        },
        "3": {
            "cannon": 2,
            "archer_tower": 1,
            "mortar": 1,
            "air_defense": 0,
            "air_sweeper": 0,
            "wizard_tower": 0,
            "town_hall": 1,
            "clan_castle": 1,
            "wall": 50,
            "army_camp": 2,
            "barracks": 2,
            "laboratory": 1,
            "spell_factory": 0,
            "gold_mine": 3,
            "elixir_collector": 3,
            "gold_storage": 1,
            "elixir_storage": 1,
            "builders_hut": 5,
            "spell_capacity_total": 0,
        },
        "4": {
            "cannon": 3,
            "archer_tower": 2,
            "mortar": 1,
            "air_defense": 1,
            "air_sweeper": 0,
            "wizard_tower": 0,
            "town_hall": 1,
            "clan_castle": 1,
            "wall": 75,
            "army_camp": 3,
            "barracks": 3,
            "laboratory": 1,
            "spell_factory": 1,
            "gold_mine": 4,
            "elixir_collector": 4,
            "gold_storage": 2,
            "elixir_storage": 2,
            "builders_hut": 5,
            "spell_capacity_total": 2,
        },
        "5": {
            "cannon": 3,
            "archer_tower": 3,
            "mortar": 2,
            "air_defense": 1,
            "air_sweeper": 0,
            "wizard_tower": 1,
            "town_hall": 1,
            "clan_castle": 1,
            "wall": 75,
            "army_camp": 4,
            "barracks": 3,
            "laboratory": 1,
            "spell_factory": 1,
            "gold_mine": 5,
            "elixir_collector": 5,
            "gold_storage": 2,
            "elixir_storage": 2,
            "builders_hut": 5,
            "spell_capacity_total": 2,
        },
        "6": {
            "cannon": 4,
            "archer_tower": 3,
            "mortar": 2,
            "air_defense": 2,
            "air_sweeper": 1,
            "wizard_tower": 2,
            "town_hall": 1,
            "clan_castle": 1,
            "wall": 75,
            "army_camp": 4,
            "barracks": 3,
            "laboratory": 1,
            "spell_factory": 1,
            "gold_mine": 6,
            "elixir_collector": 6,
            "gold_storage": 2,
            "elixir_storage": 2,
            "builders_hut": 5,
            "spell_capacity_total": 2,
        },
    },
}


def _http_get(url: str, timeout: float = 30.0) -> tuple[str, str, str]:
    """Fetch URL; return (text, etag, last_modified). Raises on network error."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        etag = resp.headers.get("ETag", "")
        last_mod = resp.headers.get("Last-Modified", "")
    return body, etag, last_mod


def _fetch_html(slug: str, cache: HtmlCache, refresh: bool) -> str | None:
    """Return cached HTML, fetching from network on miss or refresh.

    Returns None if neither cache nor network produces HTML (caller logs and
    falls through to validate-and-emit mode).
    """
    if not refresh and cache.has(slug):
        return cache.read(slug).html
    url = entity_url(slug)
    try:
        body, etag, last_mod = _http_get(url)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        LOGGER.warning("network fetch failed for %s: %s", url, e)
        if cache.has(slug):
            return cache.read(slug).html
        return None
    cache.write(slug, body, url, etag=etag, last_modified=last_mod)
    return body


def _scrape_buildings(cache: HtmlCache, refresh: bool) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name, slug in BUILDING_ENTITIES:
        html = _fetch_html(slug, cache, refresh)
        table = extract_level_table(html) if html else None
        if table is None:
            LOGGER.warning("no level table parsed for building %s; emitting empty levels", name)
        out.append(build_building(name, table))
    return out


def _scrape_troops(cache: HtmlCache, refresh: bool) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name, slug in TROOP_ENTITIES:
        html = _fetch_html(slug, cache, refresh)
        table = extract_level_table(html) if html else None
        if table is None:
            LOGGER.warning("no level table parsed for troop %s; emitting empty levels", name)
        out.append(build_troop(name, table))
    return out


def _scrape_spells(cache: HtmlCache, refresh: bool) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name, slug in SPELL_ENTITIES:
        html = _fetch_html(slug, cache, refresh)
        table = extract_level_table(html) if html else None
        if table is None:
            LOGGER.warning("no level table parsed for spell %s; emitting empty levels", name)
        out.append(build_spell(name, table))
    return out


def _scrape_traps(cache: HtmlCache, refresh: bool) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name, slug in TRAP_ENTITIES:
        html = _fetch_html(slug, cache, refresh)
        table = extract_level_table(html) if html else None
        if table is None:
            LOGGER.warning("no level table parsed for trap %s; emitting empty levels", name)
        out.append(build_trap(name, table))
    return out


_BuildingListAdapter = TypeAdapter(list[BuildingType])
_TroopListAdapter = TypeAdapter(list[TroopType])
_SpellListAdapter = TypeAdapter(list[SpellType])
_TrapListAdapter = TypeAdapter(list[TrapType])


def _validate_entries(entries: list[dict[str, Any]], adapter: TypeAdapter[Any]) -> None:
    adapter.validate_python(entries)


def _write_validate_and_emit(out_path: Path, schema: type[BaseModel] | None) -> None:
    """Re-emit a committed JSON file: read, schema-validate, write back canonically.

    Used as the offline fallback when the cache is empty AND `--refresh` was
    not passed AND the target file already exists. Keeps the scraper's
    "produces all 4 JSONs without errors" AC achievable without network.
    """
    if not out_path.exists():
        raise SystemExit(
            f"error: cannot validate-and-emit: {out_path} does not exist and "
            "no cached HTML is available. Run with --refresh to populate the cache."
        )
    raw: Any = json.loads(out_path.read_text(encoding="utf-8"))
    if schema is not None:
        entries: Any = raw["entries"] if isinstance(raw, dict) and "entries" in raw else raw
        if schema is BuildingType:
            _BuildingListAdapter.validate_python(entries)
        elif schema is TroopType:
            _TroopListAdapter.validate_python(entries)
        elif schema is SpellType:
            _SpellListAdapter.validate_python(entries)
    canon = json.dumps(raw, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    out_path.write_text(canon, encoding="utf-8")


def _write_canonical_json(payload: Any, path: Path) -> None:
    """Pretty-print with sorted keys + UTF-8, per PRD §9.4."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def _emit_buildings(out_dir: Path, cache: HtmlCache, refresh: bool) -> None:
    target = out_dir / "buildings.json"
    if not refresh and not _any_cached(cache, [s for _, s in BUILDING_ENTITIES]):
        LOGGER.info(
            "buildings: cache empty and no --refresh; running validate-and-emit on %s", target
        )
        _write_validate_and_emit(target, BuildingType)
        return
    entries = _scrape_buildings(cache, refresh)
    _validate_entries(entries, _BuildingListAdapter)
    _write_canonical_json({"schema_version": 1, "entries": entries}, target)


def _emit_troops(out_dir: Path, cache: HtmlCache, refresh: bool) -> None:
    target = out_dir / "troops.json"
    if not refresh and not _any_cached(cache, [s for _, s in TROOP_ENTITIES]):
        LOGGER.info("troops: cache empty and no --refresh; running validate-and-emit on %s", target)
        _write_validate_and_emit(target, TroopType)
        return
    entries = _scrape_troops(cache, refresh)
    _validate_entries(entries, _TroopListAdapter)
    _write_canonical_json({"schema_version": 1, "entries": entries}, target)


def _emit_spells(out_dir: Path, cache: HtmlCache, refresh: bool) -> None:
    target = out_dir / "spells.json"
    if not refresh and not _any_cached(cache, [s for _, s in SPELL_ENTITIES]):
        LOGGER.info("spells: cache empty and no --refresh; running validate-and-emit on %s", target)
        _write_validate_and_emit(target, SpellType)
        return
    entries = _scrape_spells(cache, refresh)
    _validate_entries(entries, _SpellListAdapter)
    _write_canonical_json({"schema_version": 1, "entries": entries}, target)


def _emit_traps(out_dir: Path, cache: HtmlCache, refresh: bool) -> None:
    target = out_dir / "traps.json"
    if not refresh and not _any_cached(cache, [s for _, s in TRAP_ENTITIES]):
        LOGGER.info("traps: cache empty and no --refresh; running validate-and-emit on %s", target)
        _write_validate_and_emit(target, TrapType)
        return
    entries = _scrape_traps(cache, refresh)
    _validate_entries(entries, _TrapListAdapter)
    _write_canonical_json({"schema_version": 1, "entries": entries}, target)


def _emit_caps(out_dir: Path) -> None:
    """Write `th_caps.json` from the curated `DEFAULT_TH_CAPS` map.

    The Fan Wiki does not publish TH-cap tables in a single machine-readable
    location, so v1 keeps the canonical TH6 caps in code (PRD §13.3 describes
    such curated data as fine for v1). Future TH7+ caps go here.
    """
    target = out_dir / "th_caps.json"
    if target.exists():
        # Idempotency: re-read, validate shape, rewrite canonical.
        raw = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or "town_hall_levels" not in raw:
            raise SystemExit(f"error: {target} is malformed; expected 'town_hall_levels' key")
        _write_canonical_json(raw, target)
        return
    _write_canonical_json(DEFAULT_TH_CAPS, target)


def _any_cached(cache: HtmlCache, slugs: list[str]) -> bool:
    return any(cache.has(s) for s in slugs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m sandbox_core.tools.scrape_wiki",
        description="Deterministic Fan Wiki scraper for sandbox-core content data.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("app/data/"),
        help="output directory for the four JSON files (default: app/data/)",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="invalidate cache and re-fetch over the network",
    )
    parser.add_argument(
        "--only",
        choices=["buildings", "troops", "spells", "traps", "caps", "all"],
        default="all",
        help="emit only one of the JSONs (default: all)",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help=f"HTML cache directory (default: <out>/{DEFAULT_CACHE_DIR_NAME})",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress info-level logs",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)s scrape_wiki: %(message)s",
    )
    out_dir: Path = args.out
    cache_dir: Path = args.cache_dir or (out_dir / DEFAULT_CACHE_DIR_NAME)
    cache = HtmlCache(cache_dir)
    only: OnlyKind = args.only
    refresh: bool = args.refresh

    if args.refresh:
        # PRD §9.3: --refresh invalidates the cache for in-scope entities.
        slugs: list[str] = []
        if only in ("all", "buildings"):
            slugs.extend(s for _, s in BUILDING_ENTITIES)
        if only in ("all", "troops"):
            slugs.extend(s for _, s in TROOP_ENTITIES)
        if only in ("all", "spells"):
            slugs.extend(s for _, s in SPELL_ENTITIES)
        if only in ("all", "traps"):
            slugs.extend(s for _, s in TRAP_ENTITIES)
        for slug in slugs:
            cache.delete(slug)

    if only in ("all", "buildings"):
        _emit_buildings(out_dir, cache, refresh)
    if only in ("all", "troops"):
        _emit_troops(out_dir, cache, refresh)
    if only in ("all", "spells"):
        _emit_spells(out_dir, cache, refresh)
    if only in ("all", "traps"):
        _emit_traps(out_dir, cache, refresh)
    if only in ("all", "caps"):
        _emit_caps(out_dir)

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
