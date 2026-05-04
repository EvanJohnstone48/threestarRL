"""Pydantic v2 schemas for sandbox-core v1 data contracts.

Every persisted JSON carries `schema_version: 1`. See:
- app/docs/sandbox/prd.md §6 (data contracts)
- app/docs/technical.md §4 (cross-subsystem contracts)
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION: Literal[1] = 1


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=False,
        validate_assignment=False,
        populate_by_name=True,
    )


class BuildingCategory(StrEnum):
    TOWN_HALL = "town_hall"
    CLAN_CASTLE = "clan_castle"
    DEFENSE = "defense"
    WALL = "wall"
    RESOURCE_COLLECTOR = "resource_collector"
    RESOURCE_STORAGE = "resource_storage"
    ARMY = "army"
    BUILDER_HUT = "builder_hut"


class TroopCategory(StrEnum):
    GROUND = "ground"
    AIR = "air"


class TargetFilter(StrEnum):
    GROUND = "ground"
    AIR = "air"
    BOTH = "both"
    ALL_EXCEPT_WALLS = "all_except_walls"


class TargetPreference(StrEnum):
    NONE = "none"
    DEFENSES = "defenses"
    WALLS = "walls"
    RESOURCES = "resources"


class AttackKind(StrEnum):
    MELEE = "melee"
    RANGED = "ranged"
    SUICIDE = "suicide"
    SPELL_BOLT = "spell_bolt"


class EventType(StrEnum):
    DEPLOY = "deploy"
    SPELL_CAST = "spell_cast"
    BOLT_STRUCK = "bolt_struck"
    ATTACK_START = "attack_start"
    PROJECTILE_FIRED = "projectile_fired"
    DAMAGE = "damage"
    DESTROYED = "destroyed"
    END_ATTACK = "end_attack"
    SIM_TERMINATED = "sim_terminated"
    TARGET_ACQUIRED = "target_acquired"
    TARGET_LOST = "target_lost"
    ATTACK_END = "attack_end"


# ---------------------------------------------------------------------------
# Static content (BuildingType / TroopType / SpellType)
# ---------------------------------------------------------------------------


class BuildingLevelStats(_StrictModel):
    level: int = Field(ge=1)
    hp: float = Field(ge=0)
    damage_per_shot: float = Field(default=0.0, ge=0)
    range_tiles: float = Field(default=0.0, ge=0)
    attack_cooldown_ticks: int = Field(default=0, ge=0)
    unlocked_at_th: int = Field(default=1, ge=1)


class BuildingType(_StrictModel):
    name: str
    category: BuildingCategory
    footprint: tuple[int, int]
    hitbox_inset: float | None = None
    target_filter: TargetFilter = TargetFilter.GROUND
    splash_radius_tiles: float = 0.0
    splash_damages_walls: bool = False
    min_range_tiles: float = 0.0
    projectile_speed_tiles_per_sec: float | None = None
    projectile_homing: bool = True
    is_wall: bool = False
    damages_walls_on_suicide: bool = False
    levels: list[BuildingLevelStats]

    @field_validator("footprint")
    @classmethod
    def _square_footprint(cls, value: tuple[int, int]) -> tuple[int, int]:
        h, w = value
        if h < 1 or w < 1:
            raise ValueError("footprint dimensions must be >= 1")
        return (h, w)

    def stats_at(self, level: int) -> BuildingLevelStats:
        for entry in self.levels:
            if entry.level == level:
                return entry
        raise KeyError(f"BuildingType {self.name!r} has no stats for level {level}")


class TroopLevelStats(_StrictModel):
    level: int = Field(ge=1)
    hp: float = Field(ge=0)
    base_damage: float = Field(default=0.0, ge=0)
    range_tiles: float = Field(default=0.0, ge=0)
    attack_cooldown_ticks: int = Field(default=0, ge=0)
    unlocked_at_th: int = Field(default=1, ge=1)


class TroopType(_StrictModel):
    name: str
    category: TroopCategory = TroopCategory.GROUND
    footprint: tuple[int, int] = (1, 1)
    hitbox_radius_tiles: float = 0.5
    housing_space: int = Field(default=1, ge=0)
    speed_tiles_per_sec: float = Field(default=0.0, ge=0)
    target_filter: TargetFilter = TargetFilter.GROUND
    target_preference: TargetPreference = TargetPreference.NONE
    splash_radius_tiles: float = 0.0
    splash_damages_walls: bool = False
    projectile_speed_tiles_per_sec: float | None = None
    projectile_homing: bool = True
    damages_walls_on_suicide: bool = False
    damage_multipliers: dict[str, float] = Field(default_factory=dict)
    damage_multiplier_default: float = 1.0
    levels: list[TroopLevelStats]

    def stats_at(self, level: int) -> TroopLevelStats:
        for entry in self.levels:
            if entry.level == level:
                return entry
        raise KeyError(f"TroopType {self.name!r} has no stats for level {level}")


class SpellLevelStats(_StrictModel):
    level: int = Field(ge=1)
    damage_per_hit: float = Field(ge=0)
    unlocked_at_th: int = Field(default=1, ge=1)


class SpellType(_StrictModel):
    name: str
    radius_tiles: float = Field(ge=0)
    hit_interval_ticks: int = Field(ge=1)
    num_hits: int = Field(ge=1)
    damages_walls: bool = False
    target_filter: TargetFilter = TargetFilter.ALL_EXCEPT_WALLS
    housing_space: int = Field(default=1, ge=0)
    levels: list[SpellLevelStats]

    def stats_at(self, level: int) -> SpellLevelStats:
        for entry in self.levels:
            if entry.level == level:
                return entry
        raise KeyError(f"SpellType {self.name!r} has no stats for level {level}")


# ---------------------------------------------------------------------------
# BaseLayout / DeploymentPlan
# ---------------------------------------------------------------------------


class BaseLayoutMetadata(_StrictModel):
    name: str
    th_level: int = Field(ge=1, le=15)
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    author: str = ""
    created_at: str = ""


class BuildingPlacement(_StrictModel):
    building_type: str
    origin: tuple[int, int]
    level: int | None = None


class BaseLayout(_StrictModel):
    schema_version: Literal[1] = SCHEMA_VERSION
    metadata: BaseLayoutMetadata
    th_level: int = Field(ge=1, le=15)
    placements: list[BuildingPlacement]
    cc_contents: list[str] = Field(default_factory=list)

    @field_validator("cc_contents")
    @classmethod
    def _cc_empty_in_v1(cls, value: list[str]) -> list[str]:
        if value:
            raise ValueError("cc_contents must be empty in v1")
        return value

    @model_validator(mode="after")
    def _th_level_consistent(self) -> BaseLayout:
        if self.metadata.th_level != self.th_level:
            raise ValueError(
                f"metadata.th_level ({self.metadata.th_level}) must match top-level "
                f"th_level ({self.th_level})"
            )
        return self


class DeploymentPlanMetadata(_StrictModel):
    name: str
    notes: str | None = None
    author: str = ""
    created_at: str = ""


class DeploymentAction(_StrictModel):
    tick: int = Field(ge=0)
    kind: Literal["deploy_troop", "cast_spell"]
    entity_type: str
    position: tuple[float, float]
    level: int | None = None


class DeploymentPlan(_StrictModel):
    schema_version: Literal[1] = SCHEMA_VERSION
    metadata: DeploymentPlanMetadata
    actions: list[DeploymentAction]

    @model_validator(mode="after")
    def _actions_sorted(self) -> DeploymentPlan:
        ticks = [a.tick for a in self.actions]
        if ticks != sorted(ticks):
            raise ValueError("DeploymentPlan.actions must be sorted by tick (ascending)")
        return self


# ---------------------------------------------------------------------------
# WorldState / TickFrame / Replay
# ---------------------------------------------------------------------------


class BuildingState(_StrictModel):
    id: int
    building_type: str
    origin: tuple[int, int]
    level: int
    hp: float
    max_hp: float
    destroyed: bool = False


class TroopState(_StrictModel):
    id: int
    troop_type: str
    level: int
    position: tuple[float, float]
    hp: float
    max_hp: float
    destroyed: bool = False


class Projectile(_StrictModel):
    id: int
    attacker_id: int
    target_id: int | None
    attack_kind: AttackKind
    attacker_position: tuple[float, float]
    current_position: tuple[float, float]
    impact_position: tuple[float, float]
    damage: float
    splash_radius_tiles: float = 0.0
    splash_damages_walls: bool = False
    ticks_to_impact: int = Field(ge=0)


class SpellCast(_StrictModel):
    id: int
    spell_type: str
    level: int
    center: tuple[float, float]
    cast_tick: int
    bolts_remaining: int = Field(ge=0)
    next_bolt_tick: int


class Score(_StrictModel):
    stars: int = Field(ge=0, le=3)
    destruction_pct: float = Field(ge=0.0, le=100.0)
    ticks_elapsed: int = Field(ge=0)
    town_hall_destroyed: bool = False


class WorldState(_StrictModel):
    tick: int = Field(ge=0)
    buildings: list[BuildingState]
    troops: list[TroopState]
    projectiles: list[Projectile] = Field(default_factory=lambda: list[Projectile]())
    spells: list[SpellCast] = Field(default_factory=lambda: list[SpellCast]())
    score: Score


class Event(_StrictModel):
    type: EventType
    tick: int = Field(ge=0)
    payload: dict[str, Any] = Field(default_factory=lambda: dict[str, Any]())


class TickFrame(_StrictModel):
    tick: int = Field(ge=0)
    state: WorldState
    events: list[Event] = Field(default_factory=lambda: list[Event]())


class ReplayMetadata(_StrictModel):
    sim_version: str
    base_name: str
    plan_name: str
    run_id: str = ""
    episode_id: str = ""
    total_ticks: int = Field(ge=0)
    final_score: Score
    started_at: str = ""
    git_sha: str = ""
    config_hash: str = ""


class Replay(_StrictModel):
    schema_version: Literal[1] = SCHEMA_VERSION
    metadata: ReplayMetadata
    initial_state: WorldState
    frames: list[TickFrame]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class SimTerminatedError(RuntimeError):
    """Raised when the sim is advanced or mutated after termination."""


class InvalidDeploymentError(ValueError):
    """Raised when a DeploymentAction violates legality (cap, position, capacity)."""


class ReplayValidationError(ValueError):
    """Raised when a replay JSON fails Pydantic validation on load."""


class SchemaMigrationError(ValueError):
    """Raised when a payload's schema_version cannot be migrated forward."""


# ---------------------------------------------------------------------------
# Schema migrations (PRD §6.8, §11.5)
# ---------------------------------------------------------------------------
#
# `MIGRATIONS[schema_name][i]` is a step that takes a payload at schema_version
# `i + 1` and returns the equivalent payload at schema_version `i + 2`. The list
# is appended to as new versions ship; at v1 every chain is empty (no-op).
#
# To add a v2 of, say, `BuildingPlacement` that renames the `level` field to
# `building_level`:
#
#     def _migrate_baseplacement_v1_to_v2(payload: dict[str, Any]) -> dict[str, Any]:
#         updated = dict(payload)
#         updated["schema_version"] = 2
#         for placement in updated.get("placements", []):
#             if "level" in placement:
#                 placement["building_level"] = placement.pop("level")
#         return updated
#
#     MIGRATIONS["BaseLayout"].append(_migrate_baseplacement_v1_to_v2)
#
# Then commit `tests/golden/migrations/baselayout_v2.json` so the migration
# chain test covers the new step. The test asserts that loading every fixture
# through `migrate_to_latest` produces a dict that validates against the
# current schema.

MigrationStep = Callable[[dict[str, Any]], dict[str, Any]]

MIGRATIONS: dict[str, list[MigrationStep]] = {
    "BaseLayout": [],
    "DeploymentPlan": [],
    "Replay": [],
}


def migrate_to_latest(payload: dict[str, Any], target_schema: type[BaseModel]) -> dict[str, Any]:
    """Apply registered migrations to bring `payload` to the latest schema version.

    Looks up the migration chain via `target_schema.__name__`. The starting
    version is `payload["schema_version"]` (defaults to 1 if absent). Returns
    a new dict; does not mutate input. At v1 this is a no-op for every
    registered schema.
    """
    schema_name = target_schema.__name__
    if schema_name not in MIGRATIONS:
        raise SchemaMigrationError(f"no migration chain registered for schema {schema_name!r}")
    chain = MIGRATIONS[schema_name]
    raw_version = payload.get("schema_version", 1)
    if not isinstance(raw_version, int) or raw_version < 1:
        raise SchemaMigrationError(
            f"{schema_name} payload has invalid schema_version={raw_version!r}; must be int >= 1"
        )
    if raw_version > SCHEMA_VERSION:
        raise SchemaMigrationError(
            f"{schema_name} payload has schema_version={raw_version} which is "
            f"newer than the current SCHEMA_VERSION={SCHEMA_VERSION}; "
            f"cannot migrate forward in time"
        )
    current = dict(payload)
    for step_idx in range(raw_version - 1, SCHEMA_VERSION - 1):
        if step_idx >= len(chain):
            raise SchemaMigrationError(
                f"{schema_name} migration chain missing step from "
                f"v{step_idx + 1} to v{step_idx + 2}"
            )
        current = chain[step_idx](current)
    return current


def load_validated[TSchema: BaseModel](
    payload: dict[str, Any], target_schema: type[TSchema]
) -> TSchema:
    """Migrate `payload` to the latest schema version, then validate against `target_schema`.

    The single entry point loaders should use when reading persisted JSON from disk.
    """
    migrated = migrate_to_latest(payload, target_schema)
    return target_schema.model_validate(migrated)


__all__ = [
    "MIGRATIONS",
    "SCHEMA_VERSION",
    "AttackKind",
    "BaseLayout",
    "BaseLayoutMetadata",
    "BuildingCategory",
    "BuildingLevelStats",
    "BuildingPlacement",
    "BuildingState",
    "BuildingType",
    "DeploymentAction",
    "DeploymentPlan",
    "DeploymentPlanMetadata",
    "Event",
    "EventType",
    "InvalidDeploymentError",
    "MigrationStep",
    "Projectile",
    "Replay",
    "ReplayMetadata",
    "ReplayValidationError",
    "SchemaMigrationError",
    "Score",
    "SimTerminatedError",
    "SpellCast",
    "SpellLevelStats",
    "SpellType",
    "TargetFilter",
    "TargetPreference",
    "TickFrame",
    "TroopCategory",
    "TroopLevelStats",
    "TroopState",
    "TroopType",
    "WorldState",
    "load_validated",
    "migrate_to_latest",
]
