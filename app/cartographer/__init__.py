"""Cartographer — Roboflow-based CV pipeline for ingesting Clash base screenshots.

v2 architectural tracer bullet: all 9 modules scaffolded with typed signatures and
stub bodies that produce syntactically valid BaseLayout v2 JSON + diagnostic PNG.
"""

from __future__ import annotations

__version__ = "0.1.0"


def run(screenshot_path, out_path=None):
    """Entry point: delegates to pipeline.run()."""
    from cartographer import pipeline

    return pipeline.run(screenshot_path, out_path)
