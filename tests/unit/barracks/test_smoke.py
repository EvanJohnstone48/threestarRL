"""Smoke test confirming barracks is importable. Replace once Phase 1.2 lands."""

from __future__ import annotations


def test_barracks_importable() -> None:
    import barracks

    assert barracks.__version__
