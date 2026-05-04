# 025 — Cartographer package skeleton + CLI tracer

**GitHub Issue:** #25

## Parent PRD

`app/docs/cartographer/prd.md` (§4.12, §4.13, §2)

## What to build

**AFK.** Architectural tracer bullet. Scaffolds the entire 9-module package and CLI; pipeline runs end-to-end on any input and emits a hardcoded-but-valid `BaseLayout` JSON + diagnostic PNG. Proves wiring before any CV code lands.

Create `app/cartographer/{preprocess,detect,grid,align,walls,emit,diagnostic,pipeline,cli}.py` per PRD §4.12. Each stage module exposes a single typed top-level function with the eventual production signature; bodies return hardcoded stub values that produce a syntactically valid output (e.g., `detect` returns one Town Hall detection at the image center; `grid` returns a fixed `(pitch, origin)`; `walls` returns an empty list).

`pipeline.py` orchestrates the seven stages in fixed order per PRD §4.1, with explicit data flow. `cli.py` exposes `python -m cartographer ingest --in <screenshot> [--out <path>]` with default output to `app/data/scraped_bases/<input_basename>.json` and co-located `<input_basename>.diag.png`.

Commit the local class-name enum locked to keys in `app/data/buildings.json` (excluding `wall`). Scaffold `app/data/cartographer_config.json` with placeholder `project_name`, `dataset_version`, and `confidence_threshold = 0.5`.

Tests: each stage module gets a test file with at least one passing trivial test. AC-C8 class-name parity test passes from this issue forward.

## Acceptance criteria

- [ ] All 9 modules created with typed function signatures.
- [ ] `python -m cartographer ingest --in <any-png>` runs to completion in <1s on any input.
- [ ] Emits a syntactically valid `BaseLayout` JSON validating against the v2 schema (with populated `provenance`) to the default output path.
- [ ] Emits a co-located diagnostic PNG.
- [ ] AC-C8 unit test passes: Roboflow class enum equals `set(buildings.json keys) - {"wall"}`.
- [ ] `cartographer_config.json` scaffolded with the three fields named.
- [ ] Test files exist for each stage module (bodies may be trivial; just the scaffolding).
- [ ] `app/cartographer/__init__.py` exposes the `pipeline.run()` entry point.

## Blocked by

- Blocked by `issues/open/024-cartographer-schema-bump-v2.md` (needs schema_version 2 + provenance).

## User stories addressed

Parent PRD user stories: 1, 8, 9, 10, 22, 23, 24, 25.
