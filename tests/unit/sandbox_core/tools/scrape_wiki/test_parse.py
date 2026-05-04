"""Tests for `scrape_wiki.parse` — HTML table + infobox extraction.

Uses small fixture HTML snippets that mimic the Fan Wiki structure, not full
real wiki pages. The full-wiki path is exercised via `--refresh` runs by a
developer with network access; the parser logic itself is verified here.
"""

from __future__ import annotations

import pytest
from sandbox_core.tools.scrape_wiki.parse import (
    extract_infobox,
    extract_level_table,
    parse_number,
)

CANNON_LEVEL_TABLE = """
<html><body>
<table class="wikitable">
  <tr>
    <th>Level</th><th>Damage per Shot</th><th>Damage per Second</th>
    <th>Hitpoints</th><th>Range</th><th>Attack Speed (sec)</th>
    <th>Town Hall Level Required</th>
  </tr>
  <tr>
    <td>1</td><td>9</td><td>11.25</td><td>420</td><td>9</td><td>0.8</td><td>1</td>
  </tr>
  <tr>
    <td>2</td><td>11</td><td>13.75</td><td>470</td><td>9</td><td>0.8</td><td>1</td>
  </tr>
  <tr>
    <td>6</td><td>25</td><td>31.25</td><td>670</td><td>9</td><td>0.8</td><td>6</td>
  </tr>
</table>
</body></html>
"""


def test_extract_level_table_basic() -> None:
    table = extract_level_table(CANNON_LEVEL_TABLE)
    assert table is not None
    assert "Level" in table.headers
    assert "Damage per Shot" in table.headers
    assert len(table.rows) == 3
    assert table.rows[0]["Level"] == "1"
    assert table.rows[0]["Damage per Shot"] == "9"
    assert table.rows[2]["Hitpoints"] == "670"


def test_extract_level_table_picks_first_table_with_level() -> None:
    """Skip wikitables that don't have a 'Level' column."""
    html = (
        """
    <table class="wikitable"><tr><th>Foo</th><th>Bar</th></tr><tr><td>x</td><td>y</td></tr></table>
    """
        + CANNON_LEVEL_TABLE
    )
    table = extract_level_table(html)
    assert table is not None
    assert "Level" in table.headers


def test_extract_level_table_returns_none_when_no_match() -> None:
    html = """<table class="wikitable"><tr><th>Foo</th></tr><tr><td>1</td></tr></table>"""
    assert extract_level_table(html) is None


def test_extract_level_table_ignores_non_wikitable() -> None:
    html = """<table><tr><th>Level</th></tr><tr><td>1</td></tr></table>"""
    assert extract_level_table(html) is None


def test_extract_infobox_basic() -> None:
    html = """
    <aside class="portable-infobox">
      <h3 class="pi-data-label">Housing Space</h3>
      <div class="pi-data-value">1</div>
      <h3 class="pi-data-label">Movement Speed</h3>
      <div class="pi-data-value">16</div>
    </aside>
    """
    fields = extract_infobox(html)
    assert fields["Housing Space"] == "1"
    assert fields["Movement Speed"] == "16"


def test_extract_infobox_empty_when_no_aside() -> None:
    assert extract_infobox("<html></html>") == {}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("9", 9.0),
        ("9.5", 9.5),
        ("420", 420.0),
        ("1,500", 1500.0),
        ("1,000,000", 1_000_000.0),
        ("0.8 sec", 0.8),
        ("9 tiles", 9.0),
        ("11.25", 11.25),
        ("", None),
        ("    ", None),
        ("N/A", None),
        ("Yes", None),
        ("-3", -3.0),
    ],
)
def test_parse_number(text: str, expected: float | None) -> None:
    assert parse_number(text) == expected
