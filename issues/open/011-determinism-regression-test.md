# 011 — Determinism regression test

**GitHub Issue:** #11

## Parent PRD

`app/docs/sandbox/prd.md` (§11.4, §12.2)

## What to build

A standalone integration test at `tests/integration/test_replay_determinism.py` that asserts the simulator is byte-deterministic across re-runs. Catches regressions caused by accidental dict-iteration-order dependencies, RNG slips, or non-deterministic floating-point operations.

- For each of three reference `(base, plan)` pairs (`tracer_smoke`, `mortar_splash`, `full_th6_attack`):
  - Instantiate a fresh `Sim`, run to termination, capture the `Replay`.
  - Repeat with another fresh `Sim`.
  - Assert byte-identical `Replay` JSON (after canonicalization) and matching `config_hash`.
- Marked `@pytest.mark.slow` (run in CI, not pre-commit).
- The test should fail loudly with a structured diff (first 20 differing field paths) when divergence occurs.

## Acceptance criteria

- [ ] Test file committed and passes against the current main-branch sim.
- [ ] Tests all three pairs.
- [ ] Asserts both byte-identical Replay JSON and matching `config_hash`.
- [ ] Failure output names which scenario diverged and shows the first ~20 differing field paths.
- [ ] CI workflow (`.github/workflows/ci.yml`) includes this test in the slow suite.
- [ ] Marker `@pytest.mark.slow` excludes it from pre-commit.
- [ ] Manual verification: deliberately introducing a non-determinism (e.g., set-based iteration) causes the test to fail with a clear diff. Reverted before commit.

## Blocked by

- Blocked by `issues/open/001-sandbox-core-tracer.md`

## User stories addressed

- FR-S1 (deterministic, no RNG).
- FR-S8 (validation discipline).
- AC-S0.4 (Phase 0 golden + this regression test together cover determinism).
