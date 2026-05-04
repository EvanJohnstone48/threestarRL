"""Tests for `scrape_wiki.normalize` — one test per documented rule."""

from __future__ import annotations

import pytest
from sandbox_core.tools.scrape_wiki.normalize import (
    DROPPED_COLUMNS,
    attack_speed_to_ticks,
    normalize_column,
)


class TestDamageColumns:
    """PRD §9.5: 'Damage per Hit/Shot/Attack' all -> damage_per_shot."""

    def test_damage_per_hit(self) -> None:
        assert normalize_column("Damage per Hit") == "damage_per_shot"

    def test_damage_per_shot(self) -> None:
        assert normalize_column("Damage per Shot") == "damage_per_shot"

    def test_damage_per_attack(self) -> None:
        assert normalize_column("Damage per Attack") == "damage_per_shot"

    def test_dps_dropped(self) -> None:
        assert normalize_column("DPS") is None
        assert normalize_column("Damage per Second") is None


class TestHpAliases:
    @pytest.mark.parametrize("header", ["Hitpoints", "HP", "Health"])
    def test_hp(self, header: str) -> None:
        assert normalize_column(header) == "hp"


class TestRangeAliases:
    @pytest.mark.parametrize("header", ["Range", "Attack Range"])
    def test_range(self, header: str) -> None:
        assert normalize_column(header) == "range_tiles"


class TestAttackSpeed:
    @pytest.mark.parametrize(
        "header", ["Attack Speed", "Attack Speed (sec)", "Attack Speed (seconds)"]
    )
    def test_attack_speed_aliases(self, header: str) -> None:
        assert normalize_column(header) == "attack_cooldown_ticks"

    def test_attack_speed_to_ticks_round_half_up(self) -> None:
        assert attack_speed_to_ticks(0.5) == 5
        assert attack_speed_to_ticks(0.8) == 8
        assert attack_speed_to_ticks(1.0) == 10
        assert attack_speed_to_ticks(5.0) == 50

    def test_attack_speed_rounds_to_int(self) -> None:
        assert attack_speed_to_ticks(0.45) == 4  # banker's rounding to 4 from .5
        assert attack_speed_to_ticks(0.55) == 6

    def test_attack_speed_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            attack_speed_to_ticks(-1.0)


class TestUnlock:
    @pytest.mark.parametrize(
        "header",
        [
            "Town Hall Level Required",
            "Town Hall Required",
            "Required Town Hall Level",
        ],
    )
    def test_th_aliases(self, header: str) -> None:
        assert normalize_column(header) == "unlocked_at_th"


class TestDroppedColumns:
    @pytest.mark.parametrize(
        "header",
        [
            "DPS",
            "Damage per Second",
            "Build Cost",
            "Build Time",
            "Research Cost",
            "Research Time",
            "Training Cost",
            "Training Time",
        ],
    )
    def test_dropped(self, header: str) -> None:
        assert normalize_column(header) is None

    def test_dropped_columns_view_consistent(self) -> None:
        assert all(normalize_column(h.title()) is None for h in ["build cost", "research time"])
        assert "dps" in DROPPED_COLUMNS


class TestCaseAndWhitespace:
    """PRD §9.5: Header lookups are case- and whitespace-insensitive."""

    def test_lowercase(self) -> None:
        assert normalize_column("hitpoints") == "hp"

    def test_mixed_whitespace(self) -> None:
        assert normalize_column("  Damage   per   Shot ") == "damage_per_shot"

    def test_unknown_raises(self) -> None:
        with pytest.raises(KeyError):
            normalize_column("Some Brand New Wiki Field")
