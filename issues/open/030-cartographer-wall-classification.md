# 030 — Wall classification

**GitHub Issue:** #30

## Parent PRD

`app/docs/cartographer/prd.md` (§4.5)

## What to build

**AFK.** Replace the `walls` stage stub from issue 025 with the real per-tile classifier. Walls are not a Roboflow class per PRD §4.5; they are inferred from the derived grid plus a stone-color test.

Pipeline:

1. Build the candidate set: every tile inside the convex hull of accepted detections that is not covered by any placed building's footprint.
2. For each candidate, sample its pixel region using the iso basis from the derived grid.
3. Classify wall vs non-wall by RGB distance to a calibrated stone-color centroid (committed as a tested module-level constant; the specific RGB values come from sampling reference screenshots in `app/data/base_screenshots/` — 50 TH6 home-village JPGs already committed, pick a handful with visible wall sections to derive the centroid).
4. Append wall placements to `BaseLayout.placements` with type `wall`. Non-wall tiles (open ground, decorations, obstacles) are left empty.

The diagnostic stage is updated to render classified walls in a distinct color overlay.

Unit tests use synthesised stone-textured and grass-textured tile fixtures and assert correct labels. AC-C5 (≥95% precision, ≥90% recall on the 5-screenshot wall subset) is scaffolded here but verified end-to-end in issue 031.

## Acceptance criteria

- [ ] `walls.py` implements the per-tile classifier.
- [ ] Stone-color centroid committed as a tested module-level constant.
- [ ] Candidate set is "in-hull, non-building tiles" only.
- [ ] Wall placements appended to `BaseLayout.placements` with type `wall`.
- [ ] Diagnostic PNG renders classified walls in a distinct color.
- [ ] Synthetic stone-tile and grass-tile unit tests pass.

## Blocked by

- Blocked by `issues/open/025-cartographer-package-skeleton-cli-tracer.md`.
- Blocked by `issues/open/028-cartographer-grass-grid-derivation.md` (needs the grid for tile sampling).
- Blocked by `issues/open/029-cartographer-detection-grid-alignment.md` (needs placed building footprints to subtract).

## User stories addressed

Parent PRD user stories: 14, 19.
