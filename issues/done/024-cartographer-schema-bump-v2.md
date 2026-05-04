# 024 — Schema bump v1 → v2 with CartographerProvenance

**GitHub Issue:** #24

## Parent PRD

`app/docs/cartographer/prd.md` (§4.10, §7.2)

## What to build

**AFK.** Pure-additive schema work. Lands cleanly before any Cartographer implementation begins; existing v1 hand-built bases continue to load through the identity migration.

Add `CartographerProvenance` to `app/sandbox_core/schemas.py` carrying `source_screenshot`, `ingest_timestamp_utc`, `dataset_version`, `confidence_threshold`, `derived_pitch_px`, `derived_origin_px`, and `per_placement_confidence`. Add an optional `provenance: CartographerProvenance | None = None` field to `BaseLayout`. Bump `BaseLayout.schema_version` from 1 to 2. Register `migrate_baselayout_v1_to_v2` as a no-op identity migration in the schema-migration registry (per the existing scaffolding from issue 022). Regenerate the TypeScript types in `app/sandbox_web/src/generated_types.ts`.

Hand-built bases continue to write `provenance: None` (or omit). v1 BaseLayout JSONs on disk continue to load via the migration with no behavioural change.

## Acceptance criteria

- [ ] `BaseLayout.schema_version` is `2`.
- [ ] `CartographerProvenance` Pydantic model defined with all fields per PRD §4.10.
- [ ] `provenance` is an optional field on `BaseLayout` with default `None`.
- [ ] `migrate_baselayout_v1_to_v2` registered and is the identity function.
- [ ] All existing `BaseLayout` JSONs (tracer, base_01..30, eval_01..05) load successfully through the migration with no diff in behaviour.
- [ ] Pydantic round-trip tests cover both v1-on-disk and v2-with-provenance.
- [ ] Generated TypeScript types regenerated; sandbox-web continues to build.

## Blocked by

None — can start immediately.

## User stories addressed

Parent PRD user stories: 16, 17, 24.
