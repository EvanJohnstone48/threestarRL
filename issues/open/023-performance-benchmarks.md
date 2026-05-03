# 023 — Performance benchmarks

**GitHub Issue:** #23

## Parent PRD

`app/docs/sandbox/prd.md` (§12.1)

## What to build

A benchmark suite at `tests/performance/` that measures sandbox-core throughput and asserts the §12.1 budgets.

- `test_throughput_tracer.py`: runs the tracer attack repeatedly, measures **episodes/sec** on a single core, asserts ≥ **100 ep/sec**.
- `test_throughput_full_th6.py`: runs the full TH6 attack repeatedly, asserts ≥ **50 ep/sec**.
- `test_replay_size_full_th6.py`: serializes the full TH6 replay in both pretty and minified modes; asserts pretty ≤ **3 MB**, minified ≤ **1.5 MB**.
- `test_sim_startup_time.py`: measures `Sim` instantiation time (loader + content merge + base validation); asserts ≤ **100 ms**.
- All marked `@pytest.mark.slow` (run in CI, not pre-commit).
- Failure messages name the affected scenario and report observed vs threshold.
- Benchmark results recorded as JSON to `tests/performance/results/<git_sha>.json` for trend tracking; failure does NOT depend on past results, only on the threshold.

## Acceptance criteria

- [ ] All four test files committed and passing on the user's reference hardware.
- [ ] `@pytest.mark.slow` excludes them from pre-commit.
- [ ] Failure messages include the observed value and the threshold.
- [ ] Benchmark results JSON written per run (gitignored — committed only as needed for analysis).
- [ ] CI runs the slow suite including these.
- [ ] Documented in repo README: how to run the perf suite locally.

## Blocked by

- Blocked by `issues/open/010-full-th6-integrative-golden-replay.md`

## User stories addressed

- §12.1 performance budgets.
