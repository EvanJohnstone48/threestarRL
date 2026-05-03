# 021 — Author 30 training bases

**GitHub Issue:** #21

## Parent PRD

`app/docs/sandbox/prd.md` (§10, AC-S1.6)

## What to build

**HITL.** Author 30 training bases at `app/data/sample_bases/base_01.json` through `base_30.json` per §10.

Workflow recommendation: author 10-15 originals, then use the editor's mirror/rotate/clear mass actions (issue 018) to expand to 30 with intentional variety. Tags should reflect the style or the author's intent (e.g., `["compound-th", "compartmentalized"]`).

Distribution should cover the typical TH6 archetypes:

- ~10 compound-TH style.
- ~5 war-base style.
- ~10 farming-base style.
- ~5 mixed / experimental.

The barracks curriculum config (in barracks-land, not this PRD's concern) will enumerate which of these belong to which training round.

## Acceptance criteria

- [ ] 30 base files committed: `base_01.json` through `base_30.json`.
- [ ] Each validates against `BaseLayout`.
- [ ] Each has full metadata.
- [ ] Distribution covers the four archetypes listed above (verified by tag inspection).
- [ ] Each loads in sandbox-web without rendering errors.
- [ ] Each base is sim-runnable — a smoke check (full-roster + Lightning plan) terminates cleanly.

## Blocked by

- Blocked by `issues/open/015-manual-editor-placement-and-validation.md`
- Blocked by `issues/open/020-author-frozen-eval-bases.md` (eval-first ordering rule)

## User stories addressed

- AC-S1.6 (training set authored).
- §10 (sample-base conventions).
