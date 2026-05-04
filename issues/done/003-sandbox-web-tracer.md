# 003 — Sandbox-web tracer (top-down viewer)

**GitHub Issue:** #3

## Parent PRD

`app/docs/sandbox/prd.md` (Phase 0 deliverable; §8 Sandbox-web)

## What to build

A minimal Vite + React + TypeScript + PixiJS project at `app/sandbox_web/` that renders a `Replay` JSON in **top-down view only** (iso is issue 014). Demoable as the Phase 0 tracer bullet's web side.

Includes:

- Vite project scaffold (already partially exists; complete the wiring).
- React app shell with drag-drop and file-picker replay loading.
- PixiJS-driven top-down renderer per §8.1 / §8.4: 50×50 grid as axis-aligned squares (32 px tile), buildings as colored rectangles with text labels, troops as colored circles, HP bars on damaged entities, deploy zone visually distinct from buildable area.
- 60 fps render loop with linear interpolation of troop and projectile positions between consecutive `TickFrame`s (6 render frames per 10 Hz tick).
- Basic play/pause toggle. (Full scrubbing/speed/step controls are issue 012.)
- Camera pan via click-drag, zoom via wheel (range 0.25×–4×, centered on cursor), "Fit to grid" reset button.
- Cross-version banner: replay with `sim_version != current` plays anyway with a banner per §8.5.
- ESLint + Prettier + Vitest + tsc all green.

## Acceptance criteria

- [ ] `pnpm dev` (or equivalent) launches the dev server.
- [ ] Drag-dropping `out.json` (the Phase 0 tracer replay) loads and visually plays the attack.
- [ ] Top-down view shows: 50×50 grid with deploy ring distinct, buildings as colored rectangles with type abbreviations, troops as colored circles, HP bars on damaged entities.
- [ ] Play/pause toggle works; sim advances at the recorded 10 Hz pace.
- [ ] Render is ~60 fps with linear interpolation of troop positions.
- [ ] Camera pan/zoom/reset works.
- [ ] `pnpm lint && pnpm typecheck && pnpm test && pnpm build` all green.

## Blocked by

- Blocked by `issues/open/002-typescript-schema-generation.md`

## User stories addressed

- FR-W1 (top-down portion).
- FR-W8 (no live IPC; reads JSON only).
- AC-S0.2 (Phase 0 visual demo).
