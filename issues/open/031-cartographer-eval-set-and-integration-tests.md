# 031 — 20-screenshot eval set + integration tests

**GitHub Issue:** #31

## Parent PRD

`app/docs/cartographer/prd.md` (§5.2, §5.3, §3 user stories 2/3/15)

## What to build

**HITL.** The empirical bar. Captures the screenshots, hand-labels ground truth, wires the integration test suite, and verifies the v2 acceptance criteria against real data.

**Eval data:**

- Source 20 TH6 home-village screenshots covering the input scope from PRD §4.11. The pool of available screenshots lives in `app/data/base_screenshots/` (50 TH6 home-village JPGs already committed). Pick 20 distinct from whatever subset issue 026 used for training; if issue 026's training subset overlaps everything in the directory, capture additional screenshots per PRD §4.11 to maintain the train/eval split. These 20 are the eval set for AC-C1, AC-C3, AC-C4.
- For each, hand-label the ground-truth `BaseLayout` (tile-precise placements) and commit the expected JSON next to the screenshot fixture.
- Within those, mark a 5-screenshot subset for the wall-accuracy bar (AC-C5). Hand-label every wall tile in those 5 screenshots.
- Author 3 negative-test fixtures for AC-C6: (i) a screenshot designed to fail grid cross-validation, (ii) a synthetic input engineered to produce two overlapping detections, (iii) a screenshot with zero detections.

**Tests:**

- Add a `requires_roboflow_api_key` pytest marker (skips cleanly when env var absent).
- `tests/integration/cartographer/` contains end-to-end tests that load each eval fixture, run `pipeline.run()`, and assert against ground truth. All marked `@pytest.mark.slow` and `@pytest.mark.requires_roboflow_api_key`.
- These tests hit the live model endpoint configured in `detect.py` (issue 027) — `https://detect.roboflow.com/{project_name}/{dataset_version}` via `requests`, NOT the `inference-sdk` package and NOT the Roboflow workflow URL. See issue 027 for the reasoning (Python 3.13 wheel gap + workflow router 404s). Do not reintroduce `inference-sdk` here.
- AC-C1: every successful ingestion produces a `BaseLayout` that loads in the Sandbox without error.
- AC-C3: ≥90% F1 on building class, ≥95% IoU on bounding box (against the 20-screenshot eval ground truth).
- AC-C4: derived `(pitch, origin)` within ±0.5 tile of hand-labeled ground truth on all 20.
- AC-C5: wall classification on the 5-screenshot subset hits ≥95% precision and ≥90% recall.
- AC-C6: 3 negative tests assert no JSON written + typed exception raised + diagnostic PNG produced.
- AC-C7: `provenance` is fully populated and round-trips through Pydantic on every successful ingestion.

## Acceptance criteria

- [ ] 20 eval screenshots committed with hand-labeled ground-truth `BaseLayout` JSONs.
- [ ] 5-screenshot wall-labelled subset committed.
- [ ] 3 negative-test fixtures committed (grid failure, overlap, zero detections).
- [ ] `requires_roboflow_api_key` pytest marker registered and skips cleanly when unset.
- [ ] AC-C1 met (every ingestion loads in sim).
- [ ] AC-C3 met (≥90% F1 class, ≥95% IoU bbox).
- [ ] AC-C4 met (grid within ±0.5 tile on all 20).
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
