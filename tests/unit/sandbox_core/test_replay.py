"""Tests for replay.py: rounding, hashing, round-trip."""

from __future__ import annotations

from pathlib import Path

from sandbox_core.replay import (
    FLOAT_PRECISION,
    compute_config_hash,
    read_replay,
    replay_to_dict,
    serialize,
    write_replay,
)
from sandbox_core.schemas import (
    Replay,
    ReplayMetadata,
    Score,
    TickFrame,
    TroopState,
    WorldState,
)


def _replay() -> Replay:
    score = Score(stars=0, destruction_pct=0.0, ticks_elapsed=0, town_hall_destroyed=False)
    troop = TroopState(
        id=1,
        troop_type="barbarian",
        level=1,
        position=(2.123456, 17.987654),
        hp=10.0,
        max_hp=10.0,
    )
    state = WorldState(tick=0, buildings=[], troops=[troop], score=score)
    frame = TickFrame(tick=0, state=state, events=[])
    rmeta = ReplayMetadata(
        sim_version="0.1.0", base_name="b", plan_name="p", total_ticks=1, final_score=score
    )
    return Replay(metadata=rmeta, initial_state=state, frames=[frame])


def test_floats_rounded_to_three_decimals() -> None:
    payload = replay_to_dict(_replay())
    pos = payload["frames"][0]["state"]["troops"][0]["position"]
    assert pos == [round(2.123456, FLOAT_PRECISION), round(17.987654, FLOAT_PRECISION)]


def test_minified_serialization_is_single_line() -> None:
    payload = replay_to_dict(_replay())
    out = serialize(payload, pretty=False)
    assert "\n" not in out


def test_pretty_serialization_has_indent() -> None:
    payload = replay_to_dict(_replay())
    out = serialize(payload, pretty=True)
    assert "  " in out
    assert out.endswith("\n")


def test_replay_round_trip(tmp_path: Path) -> None:
    out = tmp_path / "r.json"
    write_replay(_replay(), out, pretty=False)
    loaded = read_replay(out)
    assert loaded.metadata.total_ticks == 1
    assert loaded.frames[0].state.troops[0].position[0] == round(2.123456, FLOAT_PRECISION)


def test_config_hash_stable_for_equivalent_floats() -> None:
    a = compute_config_hash({"x": 1.234999})
    b = compute_config_hash({"x": 1.235000})
    # Both round to 1.235; hash is identical.
    assert a == b


def test_config_hash_changes_with_meaningful_diff() -> None:
    a = compute_config_hash({"x": 1.234})
    b = compute_config_hash({"x": 5.000})
    assert a != b
