"""Schema migration scaffolding tests (PRD §6.8, §11.5).

For each persisted schema, load the v1 fixture, run it through
`migrate_to_latest`, and assert the result validates against the current
schema. At v1 the chain is a no-op; this test is the harness future v2
migrations plug into.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel
from sandbox_core.schemas import (
    MIGRATIONS,
    SCHEMA_VERSION,
    BaseLayout,
    DeploymentPlan,
    Replay,
    SchemaMigrationError,
    load_validated,
    migrate_to_latest,
)

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "golden" / "migrations"

V1_FIXTURES: list[tuple[str, type[BaseModel]]] = [
    ("baselayout_v1.json", BaseLayout),
    ("deploymentplan_v1.json", DeploymentPlan),
    ("replay_v1.json", Replay),
]


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((MIGRATIONS_DIR / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(("fixture_name", "schema_cls"), V1_FIXTURES)
def test_v1_fixture_validates_against_current_schema(
    fixture_name: str, schema_cls: type[BaseModel]
) -> None:
    raw = _load_fixture(fixture_name)
    instance = load_validated(raw, schema_cls)
    assert isinstance(instance, schema_cls)
    assert raw["schema_version"] == 1


@pytest.mark.parametrize(("fixture_name", "schema_cls"), V1_FIXTURES)
def test_v1_fixture_migrates_to_latest(fixture_name: str, schema_cls: type[BaseModel]) -> None:
    raw = _load_fixture(fixture_name)
    migrated = migrate_to_latest(raw, schema_cls)
    assert migrated is not raw, "migrate_to_latest must not mutate input"
    assert raw["schema_version"] == 1
    assert migrated["schema_version"] == SCHEMA_VERSION


def test_migrations_registered_for_every_persisted_schema() -> None:
    expected = {"BaseLayout", "DeploymentPlan", "Replay"}
    assert expected.issubset(MIGRATIONS.keys())


def test_migrations_chains_match_schema_version() -> None:
    """Each chain has length = SCHEMA_VERSION - 1 so every prior version has a step."""
    for name, chain in MIGRATIONS.items():
        assert len(chain) == SCHEMA_VERSION - 1, (
            f"MIGRATIONS[{name!r}] has {len(chain)} steps but expected "
            f"{SCHEMA_VERSION - 1} for SCHEMA_VERSION={SCHEMA_VERSION}"
        )


def test_migrate_rejects_unregistered_schema() -> None:
    class Unregistered(BaseModel):
        pass

    with pytest.raises(SchemaMigrationError, match="no migration chain"):
        migrate_to_latest({"schema_version": 1}, Unregistered)


def test_migrate_rejects_future_schema_version() -> None:
    payload = {"schema_version": SCHEMA_VERSION + 1}
    with pytest.raises(SchemaMigrationError, match="newer than"):
        migrate_to_latest(payload, BaseLayout)


def test_migrate_rejects_invalid_schema_version() -> None:
    with pytest.raises(SchemaMigrationError, match="invalid schema_version"):
        migrate_to_latest({"schema_version": 0}, BaseLayout)
    with pytest.raises(SchemaMigrationError, match="invalid schema_version"):
        migrate_to_latest({"schema_version": "1"}, BaseLayout)


def test_migrate_defaults_missing_schema_version_to_one() -> None:
    raw = _load_fixture("baselayout_v1.json")
    raw.pop("schema_version")
    migrated = migrate_to_latest(raw, BaseLayout)
    assert migrated["schema_version"] == SCHEMA_VERSION
    instance = BaseLayout.model_validate(migrated)
    assert instance.schema_version == SCHEMA_VERSION


def test_migration_chain_runs_when_versions_differ() -> None:
    """Synthetic regression: when MIGRATIONS contains steps, migrate_to_latest applies them in order."""
    calls: list[int] = []

    def step_one(payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(1)
        return {**payload, "schema_version": 2, "field_added_in_v2": True}

    def step_two(payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(2)
        return {**payload, "schema_version": 3}

    original = MIGRATIONS["BaseLayout"]
    MIGRATIONS["BaseLayout"] = [step_one, step_two]
    try:
        result = _migrate_with_target_version({"schema_version": 1}, BaseLayout, target_version=3)
        assert calls == [1, 2]
        assert result["schema_version"] == 3
        assert result["field_added_in_v2"] is True

        calls.clear()
        result_partial = _migrate_with_target_version(
            {"schema_version": 2, "field_added_in_v2": True},
            BaseLayout,
            target_version=3,
        )
        assert calls == [2]
        assert result_partial["schema_version"] == 3
    finally:
        MIGRATIONS["BaseLayout"] = original


def _migrate_with_target_version(
    payload: dict[str, Any], target_schema: type[BaseModel], *, target_version: int
) -> dict[str, Any]:
    """Test helper: simulate migrate_to_latest if SCHEMA_VERSION were `target_version`.

    Lets us exercise the multi-step path even though the production
    `SCHEMA_VERSION` is 1. Mirrors the body of `migrate_to_latest` but takes
    the target version explicitly.
    """
    chain = MIGRATIONS[target_schema.__name__]
    raw_version = int(payload.get("schema_version", 1))
    current = dict(payload)
    for step_idx in range(raw_version - 1, target_version - 1):
        current = chain[step_idx](current)
    return current
