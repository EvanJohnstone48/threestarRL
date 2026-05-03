# 002 — TypeScript schema generation

**GitHub Issue:** #2

## Parent PRD

`app/docs/sandbox/prd.md` (§3.2 FR-W9, §6 data contracts)

## What to build

A `make types` task (or `uv run` script equivalent) that introspects the Pydantic v2 models in `app/sandbox_core/schemas.py` and emits `app/sandbox_web/src/generated_types.ts`. Sandbox-web never declares its own duplicate of any sim schema — every TS interface comes from this generator.

Pipeline: Pydantic `model_json_schema()` → JSON Schema → TypeScript via `json-schema-to-typescript` (or `pydantic2ts`). Output is committed (not gitignored) so the web project builds without invoking Python.

Adds drift detection: pre-commit and CI both regenerate the file in a temp location and `diff` against committed; non-zero diff fails the check.

## Acceptance criteria

- [ ] `make types` (or equivalent task) generates `app/sandbox_web/src/generated_types.ts`.
- [ ] All v1 schemas have corresponding TS exports: `BaseLayout`, `BuildingPlacement`, `DeploymentAction`, `DeploymentPlan`, `WorldState`, `TickFrame`, `Replay`, `Score`, `Event`, `BuildingType`, `TroopType`, `SpellType`, `Projectile`, `SpellCast`.
- [ ] CI step regenerates and diffs against committed `generated_types.ts`; fails on drift with a clear "run `make types` and commit" message.
- [ ] Pre-commit hook also runs the drift check (fast — should add <1s to commit time).
- [ ] `pnpm tsc --noEmit` passes against the generated file.
- [ ] The Makefile (or equivalent) is documented in repo `README.md`.

## Blocked by

- Blocked by `issues/open/001-sandbox-core-tracer.md`

## User stories addressed

- FR-W9 (TS types auto-generated; no duplicate schemas in web project).
- §6 (single source of truth for data contracts).
