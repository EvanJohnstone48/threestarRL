"""Smoke test confirming the cartographer package is importable."""

from __future__ import annotations


def test_cartographer_importable() -> None:
    import cartographer

    assert cartographer.__version__ == "0.1.0"
