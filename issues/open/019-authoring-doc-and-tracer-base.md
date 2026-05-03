# 019 — AUTHORING.md doc + tracer.json authored

**GitHub Issue:** #19

## Parent PRD

`app/docs/sandbox/prd.md` (§10.3, §10.5)

## What to build

**HITL.** Two artifacts:

1. `app/data/sample_bases/AUTHORING.md` — companion doc per §10.3 with:
   - Variety guidance (avoid all-clustered-corner bases; aim for compound-TH / war-base / farming-base styles).
   - Eval-set ordering rule (eval bases authored *before* training set, frozen forever after first commit).
   - File naming conventions and metadata field requirements.
   - Editor mass-actions workflow tips (mirror/rotate/clear).
   - Cross-reference to PRD §10.

2. `app/data/sample_bases/tracer.json` — the canonical Phase 0 tracer base. Small TH6 layout: 1 TH + 1 Cannon + a few wall segments + a couple of resource buildings to make the destruction percent meaningful. Authored using the editor (issue 015) and exported. Replaces any placeholder tracer.json that may have been hand-written in issue 001.

## Acceptance criteria

- [ ] `AUTHORING.md` committed at the right path with the four content areas listed above.
- [ ] `tracer.json` validates against `BaseLayout`.
- [ ] `tracer.json` metadata complete: `name="tracer"`, `th_level=6`, `tags`, `notes`, `author`, `created_at` ISO 8601.
- [ ] `tracer.json` works with the existing `single_barb.json` plan to produce a runnable replay (CLI + viewer both succeed).
- [ ] `tracer_smoke.json` golden replay still passes (re-record via `pytest --update-golden` if the new tracer differs from the placeholder one).

## Blocked by

- Blocked by `issues/open/015-manual-editor-placement-and-validation.md`

## User stories addressed

- §10.3 (authoring doc).
- AC-S1.6 (start of base authoring).
