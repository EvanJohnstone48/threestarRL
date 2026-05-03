# 018 — Manual editor: mass actions (mirror, rotate, clear)

**GitHub Issue:** #18

## Parent PRD

`app/docs/sandbox/prd.md` (§8.6 editor — quality-of-life)

## What to build

Quality-of-life mass actions in the editor toolbar. Useful for authoring symmetric or rotated bases quickly.

- **Clear all** button (with confirmation). Empties the placement list. Undoable.
- **Mirror horizontal** — reflects all placements across the vertical center axis (col 25). Re-validates; if the result violates any constraint, refuses with an error toast.
- **Mirror vertical** — reflects across horizontal center axis (row 25). Same validation rule.
- **Rotate 90° clockwise** — rotates all placements clockwise around the grid center. Same validation rule.
- All operations push to the undo history (issue 017).

## Acceptance criteria

- [ ] Clear-all button (with "Are you sure?" confirmation) empties the placement list; undoable.
- [ ] Mirror H reflects placements across vertical center axis; symmetry verified by a unit test on a known input.
- [ ] Mirror V reflects across horizontal center axis.
- [ ] Rotate 90° rotates clockwise; refuses if any rotated placement falls outside the buildable region with a clear error toast.
- [ ] Each operation is undoable via `Ctrl+Z`.
- [ ] Vitest tests for each transformation function with deterministic input/output pairs.

## Blocked by

- Blocked by `issues/open/017-manual-editor-export-import-autosave-undo.md`

## User stories addressed

- FR-W4 (extension — placement quality-of-life).
- §8.6 mass-actions paragraph.
