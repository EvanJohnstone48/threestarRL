# 022 — Schema migration scaffolding

**GitHub Issue:** #22

## Parent PRD

`app/docs/sandbox/prd.md` (§6.8 schema_version posture, §11.5)

## What to build

Sets up the schema-migration test harness so future v2 work has a clear path.

- For each persisted schema (`BaseLayout`, `DeploymentPlan`, `Replay`), commit a v1 fixture at `tests/golden/migrations/<schema>_v1.json`. The fixture is a small valid example.
- Migration harness in `app/sandbox_core/schemas.py`: a `MIGRATIONS: dict[str, list[Callable[[dict], dict]]]` registry plus a `migrate_to_latest(payload: dict, target_schema: type) -> dict` helper. v1-target migrations are no-ops.
- Migration test at `tests/unit/sandbox_core/test_schema_migrations.py`: for each fixture, load the dict, run through `migrate_to_latest`, assert the result validates against the latest schema.
- Schemas.py docstring example: how to add a v2 migration. E.g., "renaming the `level` field to `building_level` would add `migrate_baseplacement_v1_to_v2`, register in MIGRATIONS, and append `tests/golden/migrations/baseplacement_v2.json`."

## Acceptance criteria

- [ ] `tests/golden/migrations/baselayout_v1.json`, `deploymentplan_v1.json`, `replay_v1.json` committed; each validates against current schemas.
- [ ] `MIGRATIONS` registry exists in `schemas.py` with empty/no-op v1-target entries for each schema.
- [ ] `migrate_to_latest` helper implemented; covers the no-op v1 case correctly.
- [ ] `test_schema_migrations.py` runs each fixture through the migration chain and asserts validity; passes in CI.
- [ ] Documentation in `schemas.py` describes how to add a v2 migration.
- [ ] When loading a JSON in the wild, the loader checks `schema_version` and dispatches through `migrate_to_latest`.

## Blocked by

- Blocked by `issues/open/001-sandbox-core-tracer.md`

## User stories addressed

- §6.8 (schema versioning posture).
- §11.5 (migration tests).
