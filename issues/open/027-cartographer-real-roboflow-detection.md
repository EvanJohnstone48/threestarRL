# 027 — Real Roboflow detection module

**GitHub Issue:** #27

## Parent PRD

`app/docs/cartographer/prd.md` (§4.7, §4.8, §4.12)

## What to build

**AFK.** Replace the `detect` stage stub from issue 025 with a real Roboflow client call.

The module reads `project_name` and `dataset_version` from `app/data/cartographer_config.json`, reads the API key from the `ROBOFLOW_API_KEY` env var, calls the hosted Roboflow Inference SDK with the preprocessed image, parses the response into the local `Detection` dataclass (`class_name`, `bbox`, `confidence`), filters by `confidence_threshold`, and returns two lists: accepted detections (≥ threshold) and sub-threshold detections.

Accepted detections feed forward to alignment per PRD §4.6. Sub-threshold detections are passed to the diagnostic stage and rendered in a contrasting color per PRD §4.7. They are not emitted to JSON.

Mock-based unit tests cover Roboflow response parsing and confidence filtering. The integration path (real network call) is exercised in issue 031, gated on `requires_roboflow_api_key`.

If `ROBOFLOW_API_KEY` is unset, the module raises a typed exception with a clear message ("Set ROBOFLOW_API_KEY to run real detection. To run with stub detections instead, …"). The pipeline still runs end-to-end against synthetic inputs in unit tests via mocks.

## Acceptance criteria

- [ ] `detect.py` calls hosted Roboflow inference via the official SDK.
- [ ] `Detection` dataclass populated from real responses.
- [ ] Confidence filtering produces two lists (accepted, sub-threshold).
- [ ] Sub-threshold detections rendered on the diagnostic PNG in a contrasting color.
- [ ] Sub-threshold detections never appear in the emitted JSON.
- [ ] Mock-based unit tests for response parsing and threshold filtering pass without network.
- [ ] Missing `ROBOFLOW_API_KEY` raises a typed exception with an actionable message.
- [ ] When `ROBOFLOW_API_KEY` is set, end-to-end pipeline runs on a real screenshot from issue 026's dataset and produces detections.

## Blocked by

- Blocked by `issues/open/025-cartographer-package-skeleton-cli-tracer.md`.
- Blocked by `issues/open/026-cartographer-roboflow-dataset-and-model.md`.

## User stories addressed

Parent PRD user stories: 7, 11, 12, 13, 14, 18.
