"""HTML parsing primitives (stdlib only) for Fan Wiki entity pages.

We extract two structures from each page:

  - The first `<table class="wikitable">` whose header row resembles a per-level
    stats table (contains a "Level" column). Returned as a list of row dicts
    keyed by raw header text.
  - The infobox metadata block (kept simple — a flat key/value mapping). Real
    Fan Wiki pages use `<aside class="portable-infobox">`; we look for
    `<h3 class="pi-data-label">` + `<div class="pi-data-value">` pairs.

Both extractors are intentionally lenient: missing fields raise nothing; they
just yield empty results. The caller's `build` step decides whether a missing
field is fatal (after running `manual_overrides`).

Stdlib-only: uses `html.parser.HTMLParser` to avoid pulling in BeautifulSoup
just for table extraction. The HTML we care about (wikitable + portable-infobox)
is well-formed enough for a simple state machine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Final, override


@dataclass(slots=True)
class WikiTable:
    headers: list[str] = field(default_factory=lambda: list[str]())
    rows: list[dict[str, str]] = field(default_factory=lambda: list[dict[str, str]]())


def _attr(attrs: list[tuple[str, str | None]], name: str) -> str:
    for k, v in attrs:
        if k == name:
            return v or ""
    return ""


def _has_class(attrs: list[tuple[str, str | None]], wanted: str) -> bool:
    classes = _attr(attrs, "class").split()
    return wanted in classes


class _TableParser(HTMLParser):
    """Extract the first wikitable that has a 'Level' column."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_table = 0  # depth into a wikitable
        self._captured: WikiTable | None = None
        self._current_table: WikiTable | None = None
        self._in_row = False
        self._current_row: list[str] = []
        self._in_cell: str | None = None  # "th" | "td" | None
        self._cell_buffer: list[str] = []

    @property
    def table(self) -> WikiTable | None:
        return self._captured

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table" and _has_class(attrs, "wikitable") and self._captured is None:
            self._in_table += 1
            self._current_table = WikiTable()
        elif self._in_table:
            if tag == "table":
                self._in_table += 1
            elif tag == "tr":
                self._in_row = True
                self._current_row = []
            elif tag in ("th", "td") and self._in_row:
                self._in_cell = tag
                self._cell_buffer = []

    @override
    def handle_endtag(self, tag: str) -> None:
        if not self._in_table:
            return
        if tag == "table":
            self._in_table -= 1
            if self._in_table == 0:
                self._finish_current_table()
        elif tag == "tr" and self._in_row:
            self._finish_row()
        elif tag in ("th", "td") and self._in_cell:
            cell_text = " ".join("".join(self._cell_buffer).split())
            self._current_row.append(cell_text)
            self._in_cell = None
            self._cell_buffer = []

    @override
    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_buffer.append(data)

    def _finish_row(self) -> None:
        assert self._current_table is not None
        if not self._current_table.headers:
            self._current_table.headers = list(self._current_row)
        else:
            row: dict[str, str] = {}
            for i, val in enumerate(self._current_row):
                if i < len(self._current_table.headers):
                    row[self._current_table.headers[i]] = val
            self._current_table.rows.append(row)
        self._in_row = False
        self._current_row = []

    def _finish_current_table(self) -> None:
        assert self._current_table is not None
        norm_headers = [h.lower().strip() for h in self._current_table.headers]
        if any("level" in h for h in norm_headers):
            self._captured = self._current_table
        self._current_table = None


class _InfoboxParser(HTMLParser):
    """Extract `pi-data-label` -> `pi-data-value` pairs from a portable infobox.

    We capture the next `pi-data-value` text after each `pi-data-label`. Only
    the first (most authoritative) infobox on the page is used.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._fields: dict[str, str] = {}
        self._in_label = False
        self._in_value = False
        self._buffer: list[str] = []
        self._pending_label: str | None = None
        self._used_first_infobox = False

    @property
    def fields(self) -> dict[str, str]:
        return self._fields

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        cls = _attr(attrs, "class")
        if "pi-data-label" in cls.split():
            self._in_label = True
            self._buffer = []
        elif "pi-data-value" in cls.split():
            self._in_value = True
            self._buffer = []

    @override
    def handle_endtag(self, tag: str) -> None:
        if self._in_label and tag in ("h3", "div", "span", "p"):
            text = " ".join("".join(self._buffer).split())
            if text:
                self._pending_label = text
            self._in_label = False
            self._buffer = []
        elif self._in_value and tag in ("div", "span", "p"):
            text = " ".join("".join(self._buffer).split())
            if self._pending_label and text:
                self._fields.setdefault(self._pending_label, text)
                self._pending_label = None
            self._in_value = False
            self._buffer = []

    @override
    def handle_data(self, data: str) -> None:
        if self._in_label or self._in_value:
            self._buffer.append(data)


def extract_level_table(html: str) -> WikiTable | None:
    """Return the first wikitable on the page with a 'Level' column, or None."""
    parser = _TableParser()
    parser.feed(html)
    parser.close()
    return parser.table


def extract_infobox(html: str) -> dict[str, str]:
    """Return the `pi-data-label -> pi-data-value` mapping for the first infobox."""
    parser = _InfoboxParser()
    parser.feed(html)
    parser.close()
    return parser.fields


_NUMERIC_TRIM: Final[str] = " ,secx"


def parse_number(text: str) -> float | None:
    """Best-effort numeric parser for wiki cell values.

    Strips common units ("sec", "tiles") and thousands-separator commas.
    Returns the first parseable number in the cell, or None.
    """
    cleaned = text.strip()
    if not cleaned:
        return None
    cleaned = cleaned.replace(",", "")
    token = ""
    for ch in cleaned:
        if ch.isdigit() or ch in ".-":
            token += ch
        elif token:
            break
    if not token or token in (".", "-", "-."):
        return None
    try:
        return float(token)
    except ValueError:
        return None


__all__ = [
    "WikiTable",
    "extract_infobox",
    "extract_level_table",
    "parse_number",
]
