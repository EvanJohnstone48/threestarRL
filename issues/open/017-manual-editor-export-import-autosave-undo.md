# 017 — Manual editor: export/import + autosave + undo/redo

**GitHub Issue:** #17

## Parent PRD

`app/docs/sandbox/prd.md` (§8.6 editor)

## What to build

The persistence layer of the editor: export-to-file, import-from-file, localStorage autosave, undo/redo history.

- **Export.** "Export base.json" button downloads a validated `BaseLayout` JSON via the browser file-save API. Disabled when validation has any ✗. The user manually copies the file into `app/data/sample_bases/`.
- **Import.** "Open base.json" file-picker button loads an existing layout for editing. Schema-migrates if needed (forward-compatible).
- **Autosave.** Every editor mutation persists the current layout to `localStorage`. On editor route reopen, if a saved draft exists, prompt: "Continue editing the last base? [Continue / Start fresh]".
- **Undo / redo.** `Ctrl+Z` undoes; `Ctrl+Shift+Z` (or `Ctrl+Y`) redoes. 50-step history. History stored as full `BuildingPlacement[]` snapshots per step (simpler than diffs; ample at 50×50). Validation runs on every undo/redo.

## Acceptance criteria

- [ ] Export button downloads a `BaseLayout` JSON; file content validates against the schema.
- [ ] Export button disabled when validation fails; tooltip shows reason.
- [ ] Open base.json file picker loads a layout; switching layouts mid-edit prompts to save current draft first.
- [ ] Autosave runs on every mutation; verified by reloading the page mid-edit and seeing the prompt.
- [ ] Continue/Start-fresh prompt works correctly on reopen.
- [ ] `Ctrl+Z` undoes the last mutation; `Ctrl+Shift+Z` redoes.
- [ ] Up to 50 history steps held; older steps drop off when exceeded.
- [ ] Validation re-runs after undo/redo; visual state reflects correctly.
- [ ] Vitest tests cover the history-state machine and autosave round-trip.

## Blocked by

- Blocked by `issues/open/015-manual-editor-placement-and-validation.md`

## User stories addressed

- FR-W6 (export/import).
- FR-W7 (autosave + continue prompt).
- §8.6 (undo/redo).
