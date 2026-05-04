"""Tests for `scrape_wiki` CLI orchestrator (`__main__`).

Two paths covered:

  - **Validate-and-emit** (no cache, no network): the committed JSONs are
    re-validated through their schemas and re-emitted canonical. Reruns are
    byte-identical.
  - **Scrape-from-fixture-cache**: small HTML fixtures pre-populated in the
    cache directory drive the parser end-to-end and produce schema-validated
    output.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from sandbox_core.tools.scrape_wiki.__main__ import main as scraper_main
from sandbox_core.tools.scrape_wiki.cache import HtmlCache
from sandbox_core.tools.scrape_wiki.entities import (
    BUILDING_ENTITIES,
    SPELL_ENTITIES,
    TROOP_ENTITIES,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
COMMITTED_DATA_DIR = REPO_ROOT / "app" / "data"


def _seed_data_dir(target: Path) -> None:
    """Copy committed JSONs into a tmp dir for validate-and-emit testing."""
    target.mkdir(parents=True, exist_ok=True)
    for name in ("buildings.json", "troops.json", "spells.json", "th_caps.json"):
        src = COMMITTED_DATA_DIR / name
        if src.exists():
            shutil.copy2(src, target / name)


def test_validate_and_emit_no_network_no_cache(tmp_path: Path) -> None:
    """With cache empty + no --refresh, the committed JSONs round-trip."""
    out_dir = tmp_path / "data"
    _seed_data_dir(out_dir)
    cache_dir = tmp_path / "empty_cache"

    rc = scraper_main(["--out", str(out_dir), "--cache-dir", str(cache_dir), "--quiet"])
    assert rc == 0
    for name in ("buildings.json", "troops.json", "spells.json", "th_caps.json"):
        assert (out_dir / name).exists()


def test_validate_and_emit_byte_identical_reruns(tmp_path: Path) -> None:
    """Reruns of validate-and-emit produce byte-identical output (PRD §9.3)."""
    out_dir = tmp_path / "data"
    _seed_data_dir(out_dir)
    cache_dir = tmp_path / "empty_cache"

    scraper_main(["--out", str(out_dir), "--cache-dir", str(cache_dir), "--quiet"])
    snapshot = {
        name: (out_dir / name).read_bytes()
        for name in ("buildings.json", "troops.json", "spells.json", "th_caps.json")
    }

    scraper_main(["--out", str(out_dir), "--cache-dir", str(cache_dir), "--quiet"])
    for name, expected in snapshot.items():
        assert (out_dir / name).read_bytes() == expected, f"{name} not byte-identical"


def test_only_filter(tmp_path: Path) -> None:
    """`--only buildings` only writes buildings.json and leaves the others alone."""
    out_dir = tmp_path / "data"
    _seed_data_dir(out_dir)
    cache_dir = tmp_path / "empty_cache"

    # Touch the others with sentinel content; verify they are NOT rewritten.
    for sentinel in ("troops.json", "spells.json", "th_caps.json"):
        (out_dir / sentinel).write_text('{"sentinel": true}', encoding="utf-8")

    rc = scraper_main(
        ["--out", str(out_dir), "--cache-dir", str(cache_dir), "--only", "buildings", "--quiet"]
    )
    assert rc == 0
    for sentinel in ("troops.json", "spells.json", "th_caps.json"):
        assert json.loads((out_dir / sentinel).read_text(encoding="utf-8")) == {"sentinel": True}


def test_only_caps(tmp_path: Path) -> None:
    out_dir = tmp_path / "data"
    cache_dir = tmp_path / "empty_cache"
    rc = scraper_main(
        ["--out", str(out_dir), "--cache-dir", str(cache_dir), "--only", "caps", "--quiet"]
    )
    assert rc == 0
    caps = json.loads((out_dir / "th_caps.json").read_text(encoding="utf-8"))
    assert caps["schema_version"] == 1
    assert {"1", "2", "3", "4", "5", "6"}.issubset(caps["town_hall_levels"])
    th6 = caps["town_hall_levels"]["6"]
    assert th6["wall"] == 75
    assert th6["spell_capacity_total"] == 2


def test_validate_and_emit_missing_target_errors(tmp_path: Path) -> None:
    """With cache empty + no committed JSONs + no --refresh, exits with error."""
    out_dir = tmp_path / "data"
    cache_dir = tmp_path / "empty_cache"
    out_dir.mkdir()
    with pytest.raises(SystemExit, match="cannot validate-and-emit"):
        scraper_main(
            ["--out", str(out_dir), "--cache-dir", str(cache_dir), "--only", "buildings", "--quiet"]
        )


def _fixture_html(level_table_html: str) -> str:
    return f"<html><body>{level_table_html}</body></html>"


CANNON_FIXTURE = _fixture_html("""
<table class="wikitable">
  <tr><th>Level</th><th>Damage per Shot</th><th>Hitpoints</th><th>Range</th>
      <th>Attack Speed (sec)</th><th>Town Hall Level Required</th></tr>
  <tr><td>1</td><td>9</td><td>420</td><td>9</td><td>0.8</td><td>1</td></tr>
  <tr><td>6</td><td>25</td><td>670</td><td>9</td><td>0.8</td><td>6</td></tr>
</table>
""")


def test_scrape_from_fixture_cache_only_buildings(tmp_path: Path) -> None:
    """End-to-end: a populated cache produces a schema-valid buildings.json."""
    out_dir = tmp_path / "data"
    cache_dir = tmp_path / "wiki_cache"
    cache = HtmlCache(cache_dir)

    # Populate cache for *all* buildings so the scraper takes the live-parse
    # branch (not validate-and-emit). For non-cannon entities we reuse a
    # minimal level table just to get past parsing.
    minimal = _fixture_html("""
    <table class="wikitable"><tr><th>Level</th><th>Hitpoints</th></tr>
    <tr><td>1</td><td>250</td></tr></table>
    """)
    for name, slug in BUILDING_ENTITIES:
        html = CANNON_FIXTURE if name == "cannon" else minimal
        cache.write(slug, html, url=f"https://wiki/{slug}", scraped_at="2026-05-03T00:00:00Z")

    rc = scraper_main(
        ["--out", str(out_dir), "--cache-dir", str(cache_dir), "--only", "buildings", "--quiet"]
    )
    assert rc == 0

    raw = json.loads((out_dir / "buildings.json").read_text(encoding="utf-8"))
    by_name = {e["name"]: e for e in raw["entries"]}
    cannon_levels = {lv["level"]: lv for lv in by_name["cannon"]["levels"]}
    assert cannon_levels[1]["damage_per_shot"] == 9.0
    assert cannon_levels[1]["attack_cooldown_ticks"] == 8
    assert cannon_levels[6]["hp"] == 670.0


def test_full_data_dir_validates(tmp_path: Path) -> None:
    """Sanity check: the committed `app/data/*.json` validates end-to-end."""
    out_dir = tmp_path / "data"
    _seed_data_dir(out_dir)
    cache_dir = tmp_path / "empty_cache"
    rc = scraper_main(["--out", str(out_dir), "--cache-dir", str(cache_dir), "--quiet"])
    assert rc == 0


def test_committed_data_covers_full_th6_roster() -> None:
    """All 17 buildings, 6 troops, 1 spell are present and schema-validated."""
    buildings = json.loads((COMMITTED_DATA_DIR / "buildings.json").read_text(encoding="utf-8"))
    troops = json.loads((COMMITTED_DATA_DIR / "troops.json").read_text(encoding="utf-8"))
    spells = json.loads((COMMITTED_DATA_DIR / "spells.json").read_text(encoding="utf-8"))

    b_names = {e["name"] for e in buildings["entries"]}
    t_names = {e["name"] for e in troops["entries"]}
    s_names = {e["name"] for e in spells["entries"]}

    assert b_names == {n for n, _ in BUILDING_ENTITIES}
    assert t_names == {n for n, _ in TROOP_ENTITIES}
    assert s_names == {n for n, _ in SPELL_ENTITIES}
