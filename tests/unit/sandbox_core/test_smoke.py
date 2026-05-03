"""Smoke test confirming sandbox_core is importable. Replace once Phase 0.1 lands."""

from __future__ import annotations


def test_sandbox_core_importable() -> None:
    import sandbox_core

    assert sandbox_core.__version__
