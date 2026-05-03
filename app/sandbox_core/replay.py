"""Replay writer + reader.

Per PRD §6.5/6.6/6.7:
  - Floats round to 3 decimal places before serialization.
  - Default mode: minified (single-line JSON).
  - Pretty mode: stable key ordering, used for committed golden fixtures.
  - `config_hash` is SHA-256 over the canonicalized JSON of inputs (base + plan
    + content data files).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sandbox_core.schemas import Replay, ReplayValidationError

FLOAT_PRECISION: int = 3


def _round_floats(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, FLOAT_PRECISION)
    if isinstance(value, list):
        return [_round_floats(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_round_floats(v) for v in value)
    if isinstance(value, dict):
        return {k: _round_floats(v) for k, v in value.items()}  # pyright: ignore[reportUnknownVariableType]
    return value


def replay_to_dict(replay: Replay) -> dict[str, Any]:
    raw = replay.model_dump(mode="json")
    return _round_floats(raw)


def write_replay(replay: Replay, path: Path | str, *, pretty: bool = False) -> None:
    payload = replay_to_dict(replay)
    text = serialize(payload, pretty=pretty)
    Path(path).write_text(text, encoding="utf-8")


def serialize(payload: dict[str, Any], *, pretty: bool) -> str:
    if pretty:
        return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False)


def read_replay(path: Path | str) -> Replay:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    try:
        return Replay.model_validate(raw)
    except Exception as e:  # pragma: no cover - re-raised typed
        raise ReplayValidationError(f"failed to validate replay {path}: {e}") from e


def compute_config_hash(*payloads: Any) -> str:
    """SHA-256 of the canonical JSON concatenation of all input payloads.

    Each payload is serialized with sorted keys, separators=(",", ":"), then
    floats are rounded to FLOAT_PRECISION decimals via the same rounding rule
    used for replay serialization.
    """
    h = hashlib.sha256()
    for payload in payloads:
        rounded = _round_floats(payload)
        h.update(
            json.dumps(rounded, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode(
                "utf-8"
            )
        )
        h.update(b"\x00")
    return h.hexdigest()


__all__ = [
    "FLOAT_PRECISION",
    "compute_config_hash",
    "read_replay",
    "replay_to_dict",
    "serialize",
    "write_replay",
]
