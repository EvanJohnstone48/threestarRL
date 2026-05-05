# 029 — Detection-to-grid alignment with calibrated offsets and overlap detection

**GitHub Issue:** #29

## Parent PRD

`app/docs/cartographer/prd.md` (§4.6)

## What to build

**AFK.** Replace the `align` stage stub from issue 025 with the real alignment math, anchored on bbox **bottom-center** with per-class calibrated offsets, then translate the convex-hull centroid of placements to grid `(22, 22)` to commit to the 44×44 frame.

For each accepted detection:

1. Compute the bbox bottom-center pixel: `(bbox_x_center, bbox_y_max)`.
2. Apply the per-class offset `(dx, dy)` from the calibration loader (issue 033): `anchor_pixel = bbox_bottom_center + (dx, dy)`. Missing offsets default to `(0, 0)` with a single warning logged per ingest.
3. Convert the anchor pixel to fractional tile coordinates: `(r, c)_frac = inv([v1 v2]) · (anchor_pixel − origin)`, where `(v1, v2)` are the iso basis vectors scaled to the derived `pitch`.
4. Look up the type's footprint `(N, N)` from `app/data/buildings.json`.
5. Compute fractional top-left tile: `(r0, c0)_frac = (r, c)_frac − (N, N)`. (When the anchor is the bottom apex of the diamond, the top-left tile is exactly `N` tiles up-left in tile coords — this works uniformly for 2×2, 3×3, 4×4, and 5×5.)
6. Round to integer: `origin_tile = round((r0, c0)_frac)`.
7. Reverse-project `origin_tile` back to a predicted anchor pixel; assert distance to observed anchor ≤ 0.5 tile.

After all per-detection steps complete:

8. Detect overlapping tile placements across all accepted detections; if any two placed footprints share a tile, raise a typed exception (no automated tie-breaking per PRD §4.6).
9. Compute the convex-hull centroid of all footprint origins (in tile coords) and translate every placement so the centroid lands at grid `(22, 22)`. If translation pushes any placement outside the 44×44 grid, raise a typed exception.

Unit tests:

- known bbox + known grid + known calibration → known integer tile origin, run for all of 2×2, 3×3, 4×4, 5×5 footprints.
- a fixture engineered to produce overlapping placements → typed exception.
- a fixture with a deliberately bad bbox bottom → reverse-projection assertion fires.
- a fixture where hull-centroid centering would clip the 44×44 boundary → typed boundary exception.
- missing calibration file → warning logged once, alignment proceeds with zero offsets, unit test asserts zero-offset behaviour.

This issue overrides the wording in `technical.md §7.1` ("infer footprints from bbox size + class-specific footprint catalog"); the doc edit lands in issue 032.

## Acceptance criteria

- [ ] `align.py` anchors on bbox bottom-center, applies per-class calibrated offsets via the loader from issue 033.
- [ ] Footprints sourced from `buildings.json`, not bbox dimensions.
- [ ] Reverse-projection sanity check enforced (≤ 0.5 tile).
- [ ] Overlapping placements raise a typed exception.
- [ ] Hull-centroid centering to (22, 22) implemented; out-of-bounds translation raises a typed boundary exception.
- [ ] Missing/stale calibration falls back to zero offsets with a single warning, never blocks.
- [ ] Unit tests cover all four footprint sizes, overlap, reverse-projection failure, boundary clip, and missing calibration.

## Blocked by

- Blocked by `issues/open/025-cartographer-package-skeleton-cli-tracer.md`.
- Blocked by `issues/open/028-cartographer-grass-grid-derivation.md` (needs real `(pitch, origin)`).
- Blocked by `issues/open/033-cartographer-calibration-format-and-loader.md` (needs the offset loader).

## User stories addressed

Parent PRD user stories: 5, 14.
