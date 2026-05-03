# 014 — Iso renderer + sprite loading

**GitHub Issue:** #14

## Parent PRD

`app/docs/sandbox/prd.md` (§8.1, §8.2 iso projection spec, §8.3 sprite directory)

## What to build

Adds isometric rendering as the second view mode.

- 2:1 dimetric projection per §8.2: 64×32 px tile diamonds, grid origin at top of screen, pixel formula `screen_x = (col − row) × 32 + canvas_center_x`, `screen_y = (col + row) × 16`.
- Sprite anchor: bottom-center pixel of canvas pinned to bottom corner of footprint diamond on screen.
- Sprite loader scans `app/sandbox_web/public/sprites/` per §8.3 directory layout. On app start, attempts to load every expected sprite path. Successful loads use the user-supplied PNG; missing sprites fall back to a magenta placeholder + entity name overlay.
- Z-ordering by `(row + col)` so south-side entities render in front.
- View toggle: `V` key cycles `top-down → iso → top-down`. Default = top-down. Iso enabled only if at least one sprite loaded successfully.
- Selected view persisted to `localStorage` per browser.
- Camera (pan + zoom 0.25×–4× + reset) works in both modes.
- HP bars, troop animation interpolation, and projectile rendering all work in iso.
- Pure-function unit tests (Vitest) for `gridToScreen(r, c)` and `screenToGrid(x, y)` projection helpers.

## Acceptance criteria

- [ ] Iso view renders the 50×50 grid as 64×32 px diamonds; pixel positions match the §8.2 formula exactly.
- [ ] Sprites load from `public/sprites/*` and pin at the bottom-center anchor of the canvas; placement matches the south corner of the building's footprint diamond.
- [ ] Missing sprite shows magenta placeholder + entity name overlay.
- [ ] `V` key cycles views correctly; choice persists across browser sessions via localStorage.
- [ ] Top-down view continues to work identically when no sprites are present.
- [ ] Camera pan/zoom/reset works in both modes.
- [ ] HP bars, troop interpolation, projectile rendering all work in iso.
- [ ] Z-ordering correct: a building closer to screen-south occludes one closer to screen-north when overlapping in screen space.
- [ ] Vitest tests for `gridToScreen` and `screenToGrid` pass; tests cover origin tile, max-extent tile, and a tile in the deploy ring.

## Blocked by

- Blocked by `issues/open/003-sandbox-web-tracer.md`

## User stories addressed

- FR-W1 (full dual-view).
