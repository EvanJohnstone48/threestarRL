"""Tests for `scrape_wiki.cache` — on-disk HTML cache."""

from __future__ import annotations

import json
from pathlib import Path

from sandbox_core.tools.scrape_wiki.cache import HtmlCache


def test_round_trip(tmp_path: Path) -> None:
    cache = HtmlCache(tmp_path)
    assert not cache.has("cannon")

    entry = cache.write(
        "cannon",
        "<html>cannon</html>",
        url="https://wiki/Cannon",
        etag='"abc"',
        last_modified="Mon, 01 Jan 2024 00:00:00 GMT",
        scraped_at="2026-05-03T00:00:00Z",
    )
    assert cache.has("cannon")

    read = cache.read("cannon")
    assert read.html == "<html>cannon</html>"
    assert read.url == "https://wiki/Cannon"
    assert read.etag == '"abc"'
    assert read.last_modified == "Mon, 01 Jan 2024 00:00:00 GMT"
    assert read.scraped_at == "2026-05-03T00:00:00Z"
    assert read.sha256 == entry.sha256
    assert len(entry.sha256) == 64  # hex digest


def test_metadata_file_is_json_pretty(tmp_path: Path) -> None:
    cache = HtmlCache(tmp_path)
    cache.write("cannon", "x", url="u", scraped_at="2026-05-03T00:00:00Z")
    meta_path = tmp_path / "cannon.metadata.json"
    raw = meta_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert set(data) == {"url", "etag", "last_modified", "sha256", "scraped_at"}
    # pretty-printed → multiple lines
    assert "\n" in raw


def test_delete(tmp_path: Path) -> None:
    cache = HtmlCache(tmp_path)
    cache.write("cannon", "x", url="u")
    assert cache.has("cannon")
    cache.delete("cannon")
    assert not cache.has("cannon")
    # Deleting nonexistent is a no-op
    cache.delete("ghost")


def test_idempotent_write(tmp_path: Path) -> None:
    cache = HtmlCache(tmp_path)
    cache.write("cannon", "<html>v1</html>", url="u", scraped_at="2026-05-03T00:00:00Z")
    cache.write("cannon", "<html>v2</html>", url="u", scraped_at="2026-05-03T00:00:00Z")
    assert cache.read("cannon").html == "<html>v2</html>"


def test_atomic_write_no_partial_files(tmp_path: Path) -> None:
    cache = HtmlCache(tmp_path)
    cache.write("cannon", "x", url="u")
    # No leftover .tmp files
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []
