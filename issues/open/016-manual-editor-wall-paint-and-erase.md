# 016 — Manual editor: wall paint + erase + context menu

**GitHub Issue:** #16

## Parent PRD

`app/docs/sandbox/prd.md` (§5.3 wall editor UX, §8.6 editor)

## What to build

Adds three editor interaction modes to issue 015's editor.

- **Wall-paint mode** (`W` shortcut). User holds mouse-down on a tile and drags; walls paint along the **straight orthogonal line** from start to current. Non-axial drags resolve to L-shape (first-horizontal-then-vertical or vice versa, picked by drag-direction heuristic). Painting over an existing wall is idempotent. Painting that exceeds the 75-wall cap stops at the cap with a tooltip.
- **Erase mode** (`E` shortcut). Click any building or wall to remove. Visual feedback: hovered entity highlights in red.
- **Right-click context menu.** Right-clicking any placed entity shows a menu: Erase / Copy / Inspect.
  - Erase: removes the entity.
  - Copy: enters place-mode for that type at the cursor.
  - Inspect: opens the entity inspector (already exists from issue 013).

All three modes are mutually exclusive with click-place mode from issue 015.

## Acceptance criteria

- [ ] `W` shortcut enters wall-paint mode; cursor changes to a paint cursor.
- [ ] Drag from tile A to tile B paints walls along orthogonal line; non-axial drags resolve to L-shape.
- [ ] Painting over an existing wall is a no-op (no error, no double-placement).
- [ ] Painting that would exceed the 75-wall cap stops at the cap with a tooltip "TH6 wall cap: 75 of 75 placed."
- [ ] `E` shortcut enters erase mode; hovered entities highlight; click removes.
- [ ] Right-click on any placed entity shows context menu with Erase / Copy / Inspect.
- [ ] Each context menu action works correctly.
- [ ] All modes are mutually exclusive with each other and with click-place mode.
- [ ] `Esc` always exits the current mode.
- [ ] Vitest tests for the paint-state machine and L-shape line resolution.

## Blocked by

- Blocked by `issues/open/015-manual-editor-placement-and-validation.md`

## User stories addressed

- FR-W4 (wall paint, erase, context menu).
