"""On-disk HTML cache for the wiki scraper (PRD §9.3).

Layout under `app/data/.wiki_cache/`:

    <slug>.html               # the raw HTML page body
    <slug>.metadata.json      # {url, etag, last_modified, sha256, scraped_at}

Cached writes are atomic via tmp-then-rename so a crashed run never leaves a
partial HTML file. The metadata is the source of truth for "was this fetched
fresh or replayed from cache" — useful for traceability.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_CACHE_DIR_NAME = ".wiki_cache"


@dataclass(slots=True, frozen=True)
class CacheEntry:
    slug: str
    html: str
    url: str
    sha256: str
    scraped_at: str
    etag: str = ""
    last_modified: str = ""

    def to_metadata(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "etag": self.etag,
            "last_modified": self.last_modified,
            "sha256": self.sha256,
            "scraped_at": self.scraped_at,
        }


class HtmlCache:
    """Filesystem-backed HTML cache keyed by entity slug."""

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir

    def _html_path(self, slug: str) -> Path:
        return self.cache_dir / f"{slug}.html"

    def _metadata_path(self, slug: str) -> Path:
        return self.cache_dir / f"{slug}.metadata.json"

    def has(self, slug: str) -> bool:
        return self._html_path(slug).exists() and self._metadata_path(slug).exists()

    def read(self, slug: str) -> CacheEntry:
        html = self._html_path(slug).read_text(encoding="utf-8")
        meta_raw = json.loads(self._metadata_path(slug).read_text(encoding="utf-8"))
        return CacheEntry(
            slug=slug,
            html=html,
            url=str(meta_raw.get("url", "")),
            sha256=str(meta_raw.get("sha256", "")),
            scraped_at=str(meta_raw.get("scraped_at", "")),
            etag=str(meta_raw.get("etag", "")),
            last_modified=str(meta_raw.get("last_modified", "")),
        )

    def write(
        self,
        slug: str,
        html: str,
        url: str,
        *,
        etag: str = "",
        last_modified: str = "",
        scraped_at: str | None = None,
    ) -> CacheEntry:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        sha256 = hashlib.sha256(html.encode("utf-8")).hexdigest()
        ts = scraped_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        entry = CacheEntry(
            slug=slug,
            html=html,
            url=url,
            sha256=sha256,
            scraped_at=ts,
            etag=etag,
            last_modified=last_modified,
        )
        _atomic_write_text(self._html_path(slug), html)
        _atomic_write_text(
            self._metadata_path(slug),
            json.dumps(entry.to_metadata(), indent=2, sort_keys=True) + "\n",
        )
        return entry

    def delete(self, slug: str) -> None:
        for p in (self._html_path(slug), self._metadata_path(slug)):
            p.unlink(missing_ok=True)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


__all__ = ["DEFAULT_CACHE_DIR_NAME", "CacheEntry", "HtmlCache"]
