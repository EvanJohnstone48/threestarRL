"""Tests for splash.py (radius resolution + filters)."""

from __future__ import annotations

from sandbox_core.splash import SplashTargetBuilding, SplashTargetTroop, resolve_splash


def _b(id: int, origin: tuple[int, int] = (10, 10), is_wall: bool = False) -> SplashTargetBuilding:
    return SplashTargetBuilding(
        id=id,
        origin=origin,
        footprint=(1, 1) if is_wall else (3, 3),
        hitbox_inset=0.5 if is_wall else 1.0,
        is_wall=is_wall,
        destroyed=False,
    )


def _t(id: int, position: tuple[float, float], is_friendly: bool = True) -> SplashTargetTroop:
    return SplashTargetTroop(id=id, position=position, destroyed=False, is_friendly=is_friendly)


def test_empty_radius_returns_no_events() -> None:
    out = resolve_splash(
        center=(11.5, 11.5),
        radius=0.0,
        damage=10.0,
        attacker_id=99,
        buildings=[_b(0)],
        troops=[_t(1, (11.5, 11.5))],
        splash_damages_walls=False,
        hits_buildings=True,
        hits_troops=True,
        hits_friendly_troops=False,
    )
    assert out == []


def test_splash_hits_multiple_clustered_troops() -> None:
    out = resolve_splash(
        center=(20.0, 20.0),
        radius=2.0,
        damage=15.0,
        attacker_id=99,
        buildings=[],
        troops=[
            _t(1, (20.0, 20.0), is_friendly=False),
            _t(2, (21.5, 20.0), is_friendly=False),
            _t(3, (25.0, 20.0), is_friendly=False),  # outside radius
        ],
        splash_damages_walls=False,
        hits_buildings=False,
        hits_troops=True,
        hits_friendly_troops=False,
    )
    ids = [e.target_id for e in out]
    assert ids == [1, 2]


def test_splash_walls_filter_skips_walls_when_false() -> None:
    out = resolve_splash(
        center=(11.5, 11.5),
        radius=2.5,
        damage=15.0,
        attacker_id=99,
        buildings=[_b(0, is_wall=False), _b(1, origin=(13, 13), is_wall=True)],
        troops=[],
        splash_damages_walls=False,
        hits_buildings=True,
        hits_troops=True,
        hits_friendly_troops=False,
    )
    assert [e.target_id for e in out] == [0]


def test_splash_walls_filter_includes_walls_when_true() -> None:
    # Wall at (13,13) has 1x1 footprint with inset 0.5 → hitbox point (13.5, 13.5).
    # Distance from center (11.5, 11.5) is sqrt(8) ≈ 2.828, so radius must exceed that.
    out = resolve_splash(
        center=(11.5, 11.5),
        radius=3.0,
        damage=15.0,
        attacker_id=99,
        buildings=[_b(0, is_wall=False), _b(1, origin=(13, 13), is_wall=True)],
        troops=[],
        splash_damages_walls=True,
        hits_buildings=True,
        hits_troops=True,
        hits_friendly_troops=False,
    )
    assert sorted(e.target_id for e in out) == [0, 1]


def test_friendly_troop_excluded_unless_explicitly_allowed() -> None:
    out = resolve_splash(
        center=(20.0, 20.0),
        radius=3.0,
        damage=10.0,
        attacker_id=99,
        buildings=[],
        troops=[_t(1, (20.0, 20.0), is_friendly=True)],
        splash_damages_walls=False,
        hits_buildings=False,
        hits_troops=True,
        hits_friendly_troops=False,
    )
    assert out == []
    out2 = resolve_splash(
        center=(20.0, 20.0),
        radius=3.0,
        damage=10.0,
        attacker_id=99,
        buildings=[],
        troops=[_t(1, (20.0, 20.0), is_friendly=True)],
        splash_damages_walls=False,
        hits_buildings=False,
        hits_troops=True,
        hits_friendly_troops=True,
    )
    assert [e.target_id for e in out2] == [1]
