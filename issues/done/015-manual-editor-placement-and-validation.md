# 015 — Manual editor: placement + validation

**GitHub Issue:** #15

## Parent PRD

`app/docs/sandbox/prd.md` (§8.6 editor; §5.7 placement rules)

## What to build

A new editor route in sandbox-web with the three-panel layout per §8.6 — palette (left), 50×50 grid (center, using the active view mode), validation+metadata panel (right).

- **Palette.** Categorized sections: Defenses, Resources, Army, Builder's Hut, Town Hall + CC, Walls. Each entry shows count placed / TH6 cap. Disabled at cap with tooltip "TH6 cap: N of N placed."
- **Click-place workflow.** Click palette item → enters "place" mode for that entity. Hover over the grid → ghost preview tile (green if legal, red if illegal — illegal includes overlap, out-of-buildable-region, cap-exceeded). Click a tile → places the building with origin at that tile. `Esc` cancels place mode.
- **Live validation.** The validation panel re-runs the `BaseLayout` validator on every mutation. Shows a list of constraints with ✓/✗:
  - "TH placed (1/1 required)"
  - "Walls X/75"
  - "No footprint overlap"
  - "All footprints inside buildable region"
  - "Total non-wall buildings: N"
- **Metadata panel.** Required form fields: `name`, `tags` (free-form chip input), `notes`, `author`, `created_at` (auto-populated UTC).
- **Cannot export when invalid.** Export button disabled if validation has any ✗.

## Acceptance criteria

- [ ] Editor route renders the three-panel layout.
- [ ] Palette shows all building types categorized; each shows count placed / TH6 cap; disabled at cap with tooltip.
- [ ] Click-place mode: ghost preview tile shows green (legal) or red (illegal) on hover; clicking places (or shows brief error animation).
- [ ] Validation panel updates live on every mutation; constraint list ✓/✗.
- [ ] Failed entries are clickable and highlight the conflicting tiles in red.
- [ ] Metadata form: required fields validated; missing fields block export.
- [ ] `Esc` cancels place mode.
- [ ] Vitest unit tests for the validator and the place-mode state machine.

## Blocked by

- Blocked by `issues/open/003-sandbox-web-tracer.md`

## User stories addressed

- FR-W4 (placement portion).
- FR-W5 (live validation, refuses invalid export).
