# 020 — Author 5 frozen eval bases

**GitHub Issue:** #20

## Parent PRD

`app/docs/sandbox/prd.md` (§10, AC-S1.6)

## What to build

**HITL.** Author the 5 frozen eval bases at `app/data/sample_bases/eval_01.json` through `eval_05.json` per §10. **Authored before the 30 training bases** per the AUTHORING.md guidance from issue 019 — the eval set is the read-only ruler and must be locked first.

Each base is hand-built using the editor and exported. Spread across stylistic variety:

- One compound-TH style (TH centralized, defenses clustered around it).
- One war-base style (asymmetric, anti-3-star design).
- One farming-base style (defenses inside, storages on edge).
- Two additional varied layouts (e.g., box-style, anti-funnel).

Once committed, **never modified.** This is convention only — no pre-commit hook in v1.

## Acceptance criteria

- [ ] 5 base files committed: `eval_01.json` through `eval_05.json`.
- [ ] Each validates against `BaseLayout`.
- [ ] Each has full metadata: name, th_level=6, tags reflecting style, notes, author, created_at.
- [ ] Stylistic variety: each represents a distinct TH6 archetype; tags reflect the style.
- [ ] Each base loads in sandbox-web without rendering errors.
- [ ] Each base is sim-runnable — a quick smoke check (full-roster + Lightning plan) terminates cleanly.

## Blocked by

- Blocked by `issues/open/015-manual-editor-placement-and-validation.md`
- Blocked by `issues/open/019-authoring-doc-and-tracer-base.md`

## User stories addressed

- AC-S1.6 (frozen eval set authored).
- §10 (sample-base conventions).
