# 031 — 5-screenshot eval set + integration tests

**GitHub Issue:** #31

## Parent PRD

`app/docs/cartographer/prd.md` (§5.2, §5.3, §3 user stories 2/3/15)

## What to build

**HITL.** The empirical bar. Captures the screenshots, hand-labels ground truth, wires the integration test suite, and verifies the v2 acceptance criteria against real data.

**Eval data:**

- Source 5 TH6 home-village screenshots covering the input scope from PRD §4.11. The pool of available screenshots lives in `app/data/base_screenshots/` (50 TH6 home-village JPGs already committed). Pick 5 distinct from whatever subset issue 026 used for training; if issue 026's training subset overlaps everything in the directory, capture additional screenshots per PRD §4.11 to maintain the train/eval split. These 5 are the empirical bar for AC-C1, AC-C3, AC-C4, AC-C5.
- For each, hand-label the ground-truth `BaseLayout` (tile-precise placements **including every wall tile**) using the sandbox-web editor's "Load screenshot…" feature for side-by-side reference, then commit the screenshot + exported JSON as a paired `<name>.jpg` + `<name>.json` in `app/data/cartographer_eval/`.
- Author 3 negative-test fixtures for AC-C6: (i) a screenshot designed to fail grid cross-validation, (ii) a synthetic input engineered to produce two overlapping detections, (iii) a screenshot with zero detections. Commit alongside the eval fixtures or under a `negatives/` subdirectory.

**Note on eval-set size:** The PRD §5.3 originally specified 20 hand-labelled bases. This issue narrows the empirical bar to 5 because wall labelling per base is the dominant cost and 5 hand-labelled bases are sufficient to validate pipeline correctness end-to-end. Beyond the empirical bar, the broader real-base eval set for the trained agent is grown by running the calibrated Cartographer over additional screenshots — those outputs do not have ground truth and do not count toward AC-C3/C4/C5. If 5 proves statistically insufficient, expansion is a follow-up issue, not a blocker for this one.

**Tests:**

- Add a `requires_roboflow_api_key` pytest marker (skips cleanly when env var absent).
- `tests/integration/cartographer/` contains end-to-end tests that load each eval fixture, run `pipeline.run()`, and assert against ground truth. All marked `@pytest.mark.slow` and `@pytest.mark.requires_roboflow_api_key`.
- These tests hit the live model endpoint configured in `detect.py` (issue 027) — `https://detect.roboflow.com/{project_name}/{dataset_version}` via `requests`, NOT the `inference-sdk` package and NOT the Roboflow workflow URL. See issue 027 for the reasoning (Python 3.13 wheel gap + workflow router 404s). Do not reintroduce `inference-sdk` here.
- AC-C1: every successful ingestion produces a `BaseLayout` that loads in the Sandbox without error.
- AC-C3: ≥90% F1 on building class, ≥95% IoU on bounding box (against the 5-screenshot eval ground truth).
- AC-C4: derived `(pitch, origin)` within ±0.5 tile of hand-labeled ground truth on all 5.
- AC-C5: wall classification on the 5 hand-labeled bases hits ≥95% precision and ≥90% recall.
- AC-C6: 3 negative tests assert no JSON written + typed exception raised + diagnostic PNG produced.
- AC-C7: `provenance` is fully populated and round-trips through Pydantic on every successful ingestion.

## Acceptance criteria

- [ ] 5 eval screenshots committed under `app/data/cartographer_eval/` with hand-labeled ground-truth `BaseLayout` JSONs (paired `<name>.jpg` + `<name>.json`), each layout including every wall tile.
- [ ] 3 negative-test fixtures committed (grid failure, overlap, zero detections).
- [ ] `requires_roboflow_api_key` pytest marker registered and skips cleanly when unset.
- [ ] AC-C1 met (every ingestion loads in sim).
- [ ] AC-C3 met (≥90% F1 class, ≥95% IoU bbox).
- [ ] AC-C4 met (grid within ±0.5 tile on all 5).
- [ ] AC-C5 met (wall ≥95% precision, ≥90% recall).
- [ ] AC-C6 met (3 negative tests pass).
- [ ] AC-C7 met (provenance round-trip on every success).

## Blocked by

- Blocked by `issues/open/027-cartographer-real-roboflow-detection.md`.
- Blocked by `issues/open/028-cartographer-grass-grid-derivation.md`.
- Blocked by `issues/open/029-cartographer-detection-grid-alignment.md`.
- Blocked by `issues/open/030-cartographer-wall-classification.md`.

## User stories addressed

Parent PRD user stories: 2, 3, 5, 15.
