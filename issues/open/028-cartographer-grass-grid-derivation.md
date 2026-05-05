# 028 — Grass-grid derivation

**GitHub Issue:** #28

## Parent PRD

`app/docs/cartographer/prd.md` (§4.2, §4.3, §2)

## What to build

**AFK.** Replace the `grid` stage stub from issue 025 with the real grass-edge derivation algorithm. Operates entirely in iso pixel space; iso angles are hardcoded constants per PRD §4.2.

Algorithm per PRD §4.3:

1. **Grass mask.** HSV hue-range filter for CoC home-village grass green, restricted to the convex hull of accepted detections, with bbox interiors plus a small dilation margin removed.
2. **Light/dark labelling.** Otsu threshold on the V channel within the grass mask, producing a binary checker map.
3. **Pitch and phase per axis.** For each iso axis, project labelled pixels onto the perpendicular direction, build a 1D autocorrelation of the binary signal, and extract pitch from the dominant non-zero-lag peak and origin offset from the phase.
4. **Cross-validation.** Pitch estimates from axis-1 and axis-2 must agree within ±2%. If not, raise a typed exception. The pipeline aborts and the diagnostic PNG is still produced.

The diagnostic stage is updated to render the inferred grid as an overlay on the original screenshot (one tick per tile boundary along each iso axis) when grid derivation succeeds, and to mark the failure region when it fails.

Synthetic-fixture unit tests synthesise a checker raster of known `(pitch, origin)` and assert recovered values within tolerance. A degenerate-input test case asserts the cross-validation failure raises.

For tuning the HSV grass-green hue range and the dilation margin against real CoC art, sample images live in `app/data/base_screenshots/` (50 TH6 home-village JPGs already committed). Use these to eyeball the algorithm's behavior on real input while iterating; do not commit them as test fixtures here — fixture creation belongs to issue 031.

AC-C4 (grid match against ground-truth on the 20-screenshot eval set) is scaffolded here but verified end-to-end in issue 031 once eval data exists.

## Acceptance criteria

- [ ] `grid.py` implements the 4-step algorithm and returns `(pitch_px, origin_px)` on success.
- [ ] Iso axes are hardcoded as a module-level constant.
- [ ] Cross-validation failure raises a typed exception consumed by the orchestrator.
- [ ] Diagnostic PNG renders the inferred grid as an overlay when the stage succeeds.
- [ ] Diagnostic PNG marks the failure when the stage fails.
- [ ] Synthetic checker-raster unit test recovers `(pitch, origin)` within ±0.5 tile.
- [ ] Degenerate-input unit test triggers the cross-validation failure.

## Blocked by

- Blocked by `issues/open/025-cartographer-package-skeleton-cli-tracer.md`.

## User stories addressed

Parent PRD user stories: 4, 6, 14, 20, 21.
