"""Tests for scoring.py — stars, destruction percent, termination."""

from __future__ import annotations

from sandbox_core.schemas import (
    BuildingCategory,
    BuildingLevelStats,
    BuildingState,
    BuildingType,
    Score,
    WorldState,
)
from sandbox_core.scoring import compute_score, is_terminal


def _bt(category: BuildingCategory, is_wall: bool = False) -> BuildingType:
    return BuildingType(
        name=str(category.value),
        category=category,
        footprint=(1, 1) if is_wall else (3, 3),
        hitbox_inset=0.5 if is_wall else 1.0,
        is_wall=is_wall,
        levels=[BuildingLevelStats(level=1, hp=100)],
    )


def test_destruction_percent_excludes_walls() -> None:
    types = {
        "town_hall": _bt(BuildingCategory.TOWN_HALL),
        "wall": _bt(BuildingCategory.WALL, is_wall=True),
        "cannon": _bt(BuildingCategory.DEFENSE),
    }
    buildings = [
        BuildingState(
            id=0,
            building_type="town_hall",
            origin=(15, 15),
            level=1,
            hp=0,
            max_hp=100,
            destroyed=True,
        ),
        BuildingState(
            id=1, building_type="wall", origin=(20, 20), level=1, hp=0, max_hp=100, destroyed=True
        ),
        BuildingState(
            id=2,
            building_type="cannon",
            origin=(25, 25),
            level=1,
            hp=100,
            max_hp=100,
            destroyed=False,
        ),
    ]
    score = compute_score(buildings=buildings, building_types=types, tick=10)
    # 1 of 2 non-walls destroyed => 50%, TH destroyed => 1+1 = 2 stars.
    assert score.destruction_pct == 50.0
    assert score.town_hall_destroyed is True
    assert score.stars == 2
    assert score.ticks_elapsed == 10


def test_full_destruction_three_stars() -> None:
    types = {"town_hall": _bt(BuildingCategory.TOWN_HALL), "cannon": _bt(BuildingCategory.DEFENSE)}
    buildings = [
        BuildingState(
            id=0,
            building_type="town_hall",
            origin=(15, 15),
            level=1,
            hp=0,
            max_hp=100,
            destroyed=True,
        ),
        BuildingState(
            id=1, building_type="cannon", origin=(25, 25), level=1, hp=0, max_hp=100, destroyed=True
        ),
    ]
    score = compute_score(buildings=buildings, building_types=types, tick=200)
    assert score.destruction_pct == 100.0
    assert score.stars == 3


def test_terminal_at_timer() -> None:
    score = Score(stars=0, destruction_pct=10.0, ticks_elapsed=1800, town_hall_destroyed=False)
    world = WorldState(tick=1800, buildings=[], troops=[], score=score)
    assert is_terminal(
        world=world, troops_remaining_in_camps=10, spells_remaining=0, end_attack_emitted=False
    )


def test_terminal_at_full_destruction() -> None:
    score = Score(stars=3, destruction_pct=100.0, ticks_elapsed=42, town_hall_destroyed=True)
    world = WorldState(tick=42, buildings=[], troops=[], score=score)
    assert is_terminal(
        world=world, troops_remaining_in_camps=5, spells_remaining=2, end_attack_emitted=False
    )


def test_terminal_when_nothing_left() -> None:
    score = Score(stars=0, destruction_pct=10.0, ticks_elapsed=100, town_hall_destroyed=False)
    world = WorldState(tick=100, buildings=[], troops=[], score=score)
    assert is_terminal(
        world=world, troops_remaining_in_camps=0, spells_remaining=0, end_attack_emitted=False
    )


def test_not_terminal_with_in_pipeline_troops() -> None:
    score = Score(stars=0, destruction_pct=0.0, ticks_elapsed=0, town_hall_destroyed=False)
    world = WorldState(tick=0, buildings=[], troops=[], score=score)
    assert not is_terminal(
        world=world, troops_remaining_in_camps=1, spells_remaining=0, end_attack_emitted=False
    )
