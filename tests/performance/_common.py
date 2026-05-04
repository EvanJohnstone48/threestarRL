"""Shared helpers for performance benchmarks."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

RESULTS_DIR = Path(__file__).parent / "results"


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            cwd=Path(__file__).parent,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def save_result(key: str, **fields: Any) -> None:
    sha = _git_sha()
    RESULTS_DIR.mkdir(exist_ok=True)
    results_file = RESULTS_DIR / f"{sha}.json"
    data: dict[str, Any] = {}
    if results_file.exists():
        data = json.loads(results_file.read_text(encoding="utf-8"))
    data[key] = fields
    results_file.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
