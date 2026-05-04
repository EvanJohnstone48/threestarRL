"""Tests for cartographer.walls."""

from __future__ import annotations

import numpy as np


def test_run_returns_list() -> None:
    from cartographer.walls import run

    image = np.zeros((100, 100, 3), dtype=np.uint8)
    result = run(image, pitch=64.0, origin=(0.0, 0.0))
    assert isinstance(result, list)


def test_stub_returns_empty() -> None:
    from cartographer.walls import run

    image = np.zeros((200, 200, 3), dtype=np.uint8)
    assert run(image, pitch=32.0, origin=(10.0, 10.0)) == []
