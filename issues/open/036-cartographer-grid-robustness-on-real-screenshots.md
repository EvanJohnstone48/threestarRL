# 036 — Cartographer grid robustness on real screenshots

**GitHub Issue:** #36

## Parent PRD

`app/docs/cartographer/prd.md` (§4.3 grass-grid derivation; §5.3 AC-C1/C3/C4/C5/C7)

## What to build

Make `cartographer.grid.run` succeed on the 5 hand-labelled screenshots in `app/data/cartographer_eval/`. The synthetic-checker unit tests (`tests/unit/cartographer/test_grid.py`) already pass; the algorithm fails specifically on small real screenshots where grass coverage is broken up by walls and dense buildings.

## Observed failure (issue #31, with `ROBOFLOW_API_KEY` set)

`pipeline.run()` raises `GridCrossValidationError` on every fixture. The §4.3 cross-check requires the two iso-axis pitch estimates to agree within 2 %; observed disagreements:

| Fixture | Axis-1 pitch (px) | Axis-2 pitch (px) | Disagreement |
| ------- | ----------------- | ----------------- | ------------ |
| th6_eval_01 | 187 | 101 | 59.7 % |
| th6_eval_02 | 29  | 40  | 31.9 % |
| th6_eval_03 | 41  | 34  | 18.7 % |
| th6_eval_04 | 36  | 34  | 5.7 %  |
| th6_eval_05 | 175 | 20  | 159 %  |

All 5 screenshots are 640×~480 px. Expected projected pitch on this resolution is ~18-22 px; fixtures 03 and 04 land near that range on at least one axis but the two axes disagree, while 01/02/05 lock onto sub-harmonic noise peaks before reaching the true period.

## Probable root cause

`_first_significant_peak` in `app/cartographer/grid.py:170` returns the smallest lag with a local-maximum ACF value above 30 % of the peak. On clean synthetic checkers this finds the fundamental. On real screenshots with sparse grass masks the ACF has noise spikes well below the true period, and the heuristic locks onto them.

## What to investigate / try

In rough order of cost:

1. **Constrain pitch range from detection bbox widths.** Roboflow gives building bboxes with known footprint (cannon → 3×3, town_hall → 4×4, etc.). The median bbox width / footprint-tiles is a strong prior on tile pitch. Search the ACF only within ±25 % of that prior, not in the full `[_MIN_PROJ_PITCH, n // 3]` range.
2. **Demand axis agreement at peak-finding time, not only at cross-check.** Find the top-K peaks per axis and pick the pair (one per axis) that minimises their disagreement, instead of independently picking each axis's first peak.
3. **Smooth the ACF more aggressively** before peak detection (current kernel `[0.25, 0.5, 0.25]` is mild for noisy real data).
4. **Raise the cross-check threshold** to a calibrated value (5-10 %) only after the above. Today's 2 % was tuned for synthetic inputs; it is too tight for real screenshots and should be relaxed once pitch detection is reliable.

Each fix is independently testable against the synthetic unit tests (must still pass) and the eval-set integration tests (must start passing).

## Acceptance criteria

- [ ] `pipeline.run()` succeeds (no exception) on all 5 fixtures in `app/data/cartographer_eval/`.
- [ ] `tests/unit/cartographer/test_grid.py` continues to pass (no regression on synthetic inputs).
- [ ] All 5 AC tests in `tests/integration/cartographer/test_eval_set.py` go green with `ROBOFLOW_API_KEY` set:
  - AC-C1 — every ingestion loads through Pydantic.
  - AC-C3 — per-class F1 ≥ 0.90 on building placements.
  - AC-C4 — max placement drift ≤ 0.5 tile vs ground truth.
  - AC-C5 — wall precision ≥ 0.95, recall ≥ 0.90.
  - AC-C7 — provenance fully populated and round-trips.
- [ ] If a metric AC fails because the underlying detector or wall classifier is the bottleneck (not grid), the failure is documented in this issue and a follow-up filed against the responsible stage rather than silently weakening the AC bar.

## Blocked by

- Blocked by `issues/open/031-cartographer-eval-set-and-integration-tests.md` (the eval set + integration test scaffold this issue measures against).

## User stories addressed

Parent PRD user stories: 2, 3, 5, 6, 14, 15, 21.
