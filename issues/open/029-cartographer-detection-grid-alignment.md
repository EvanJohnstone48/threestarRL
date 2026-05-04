# 029 — Detection-to-grid alignment with overlap detection

**GitHub Issue:** #29

## Parent PRD

`app/docs/cartographer/prd.md` (§4.6)

## What to build

**AFK.** Replace the `align` stage stub from issue 025 with the real alignment math.

For each accepted detection:

1. Compute bbox center in pixel space.
2. Convert to fractional tile coordinates: `(r, c)_frac = inv([v1 v2]) · (center − origin)`, where `(v1, v2)` are the iso basis vectors scaled to the derived `pitch`.
3. Look up the type's footprint `(H, W)` from `app/data/buildings.json` (footprint is class-driven per PRD §4.6, not derived from bbox dimensions).
4. Subtract half-footprint and round: `origin_tile = round((r, c)_frac − (H/2 − 0.5, W/2 − 0.5))`.
5. Reverse-projection sanity check: re-project the integer origin back to a predicted bbox center; assert distance to observed center ≤ 0.5 tile.
6. Detect overlapping tile placements across all detections; if any two placed footprints share a tile, raise a typed exception (no automated tie-breaking per PRD §4.6).

Unit tests:

- known bbox + known grid → known integer tile origin.
- a fixture engineered to produce overlapping placements → typed exception.
- a fixture with a deliberately bad bbox center → reverse-projection assertion fires.

This issue overrides the wording in `technical.md §7.1` ("infer footprints from bbox size + class-specific footprint catalog"); the doc edit lands in issue 032.

## Acceptance criteria

- [ ] `align.py` implements the bbox-to-tile alignment math.
- [ ] Footprints sourced from `buildings.json`, not bbox dimensions.
- [ ] Reverse-projection sanity check enforced (≤ 0.5 tile).
- [ ] Overlapping placements raise a typed exception.
- [ ] Unit tests cover happy path, overlap, and reverse-projection failure.

## Blocked by

- Blocked by `issues/open/025-cartographer-package-skeleton-cli-tracer.md`.
- Blocked by `issues/open/028-cartographer-grass-grid-derivation.md` (needs real `(pitch, origin)` to round against).

## User stories addressed

Parent PRD user stories: 5, 14.
