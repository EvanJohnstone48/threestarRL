"""Smoke test confirming the cartographer stub is importable."""

from __future__ import annotations


def test_cartographer_stub_importable() -> None:
    import cartographer

    assert cartographer.__version__ == "0.0.0", "v1 cartographer is a stub"
