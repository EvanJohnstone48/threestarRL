# 032 — Documentation cleanup

**GitHub Issue:** #32

## Parent PRD

`app/docs/cartographer/prd.md` (§7.1)

## What to build

**AFK.** Reflect Cartographer's implemented state in the project-wide docs. Lands after the rest of the v2 work so the docs describe reality, not intent.

**`app/docs/technical.md` §7.1**

- Update the pipeline diagram to seven stages (insert `grid` between `detect` and `align`; insert `walls` between `align` and `emit`).
- Replace the wording "infer footprints from bbox size + class-specific footprint catalog" with "footprints are sourced from the class label; bbox size is sanity-check only" per Cartographer PRD §4.6.
- Add a one-line note that `grid` derives only `(pitch, origin)` per image; iso angles and grid size are hardcoded constants per Cartographer PRD §4.2.

**`app/docs/prd.md` §5.3**

- Append AC-C4 through AC-C8 to the v2 acceptance criteria block.
- Append the v2 out-of-scope items from Cartographer PRD §6.1 that are not already mirrored.

**`app/cartographer/README.md`**

- Replace the "deferred to v2" stub with a short overview of the implemented pipeline, pointing readers at `app/docs/cartographer/prd.md` for the full design and at `app/cartographer/cli.py` for the CLI entry point.

## Acceptance criteria

- [ ] `technical.md` §7.1 reflects the 7-stage pipeline and the class-driven footprint correction.
- [ ] `prd.md` §5.3 includes AC-C4–C8 and the updated v2 out-of-scope list.
- [ ] `cartographer/README.md` describes the implemented package and points at the PRD and CLI.
- [ ] All cross-references between Cartographer PRD and the updated docs validate (sections referenced exist in target docs).

## Blocked by

- Blocked by `issues/open/024-cartographer-schema-bump-v2.md`.
- Blocked by `issues/open/025-cartographer-package-skeleton-cli-tracer.md`.
- Blocked by `issues/open/026-cartographer-roboflow-dataset-and-model.md`.
- Blocked by `issues/open/027-cartographer-real-roboflow-detection.md`.
- Blocked by `issues/open/028-cartographer-grass-grid-derivation.md`.
- Blocked by `issues/open/029-cartographer-detection-grid-alignment.md`.
- Blocked by `issues/open/030-cartographer-wall-classification.md`.
- Blocked by `issues/open/031-cartographer-eval-set-and-integration-tests.md`.

## User stories addressed

— (no specific PRD user stories; reflects implementation reality back into project-wide docs)
