# 012 — Replay viewer: scrubbing, playback speed, step

**GitHub Issue:** #12

## Parent PRD

`app/docs/sandbox/prd.md` (§8.5 replay viewer)

## What to build

Adds the bottom-toolbar playback controls to the Phase 0 top-down viewer (issue 003).

- Scrub bar across the full tick range with current-tick marker. Dragging jumps playback to that tick instantly.
- Speed selector: 0.25×, 0.5×, 1×, 2×, 4×, 8×. Honored against the 10 Hz sim base; 60 fps render with interpolation respecting effective tick rate.
- Step ±1 tick buttons (active only when paused).
- Tick counter readout: `T_current / T_total`.
- Keyboard shortcuts: `Space` play/pause, `←/→` step ±1 tick when paused, `[/]` decrease/increase speed.

## Acceptance criteria

- [ ] Bottom toolbar visible in the replay viewer.
- [ ] Scrub bar: dragging jumps playback to that tick; current-tick marker tracks during play.
- [ ] All six speeds honored (0.25× to 8×).
- [ ] Step ±1 buttons advance/retreat the sim by exactly one tick when paused.
- [ ] Tick counter displays correctly.
- [ ] Keyboard shortcuts work as specified.
- [ ] Vitest tests cover the playback-controller hook (or equivalent state container) with simulated user events.

## Blocked by

- Blocked by `issues/open/003-sandbox-web-tracer.md`

## User stories addressed

- FR-W2.
