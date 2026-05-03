# 013 — Replay viewer: event marks + entity inspector

**GitHub Issue:** #13

## Parent PRD

`app/docs/sandbox/prd.md` (§8.5 replay viewer)

## What to build

Per §8.5, two final viewer features:

- **Event marks on the timeline.** Colored ticks under the scrubber: `deploy` (green), `damage` (yellow with size scaled to magnitude), `destroyed` (red), `spell_cast` (purple), `town_hall_destroyed` (gold star). Hover-tooltip shows event details (`type`, `tick`, payload summary).
- **Entity inspector.** Clicking any building or troop on the canvas opens a right-side inspector panel showing: type, level, HP/maxHP, position, current target (when applicable), per-entity stats from the loaded content data. Inspector content updates live as playback advances.
- Inspector closes on `Esc` or click outside the panel.

## Acceptance criteria

- [ ] Event marks rendered correctly along the scrub bar; positions correct relative to the tick axis.
- [ ] Hover-tooltip on each mark shows event type + tick + summary.
- [ ] Clicking a building or troop opens the inspector with correct content for the current tick.
- [ ] Inspector content updates as playback advances (e.g., HP changes reflect immediately).
- [ ] Pressing `Esc` or clicking outside closes the inspector.
- [ ] Vitest tests cover the inspector-state hook and the timeline-marks computation.

## Blocked by

- Blocked by `issues/open/012-replay-viewer-scrubbing-playback-step.md`

## User stories addressed

- FR-W3.
