# 027 — Real Roboflow detection module

**GitHub Issue:** #27

## Parent PRD

`app/docs/cartographer/prd.md` (§4.7, §4.8, §4.12)

## What to build

**AFK.** Replace the `detect` stage stub from issue 025 with a real Roboflow client call.

The module reads `project_name` and `dataset_version` from `app/data/cartographer_config.json`, reads the API key from the `ROBOFLOW_API_KEY` env var, calls the hosted Roboflow detection model via direct HTTPS POST with the preprocessed image, parses the response into the local `Detection` dataclass (`class_name`, `bbox`, `confidence`), filters by `confidence_threshold`, and returns two lists: accepted detections (≥ threshold) and sub-threshold detections.

### Endpoint and transport

Call the **model endpoint directly**, not the Roboflow workflow wrapper:

```
POST https://detect.roboflow.com/{project_name}/{dataset_version}?api_key=$ROBOFLOW_API_KEY
Content-Type: application/x-www-form-urlencoded
Body: <base64-encoded image bytes>
```

Response shape: `{"predictions": [{"class": str, "x": float, "y": float, "width": float, "height": float, "confidence": float}, ...], "image": {"width": int, "height": int}}`. Note `(x, y)` is the bbox **center**, not top-left; convert to `(x1, y1, x2, y2)` as `(x - w/2, y - h/2, x + w/2, y + h/2)` when populating `Detection.bbox_xyxy`.

### Why not `inference-sdk` and not the workflow URL

- **No `inference-sdk` dependency.** The repo runs on Python 3.13 (`pyproject.toml` `requires-python = ">=3.12"`, current venv is 3.13.x). `inference-sdk>=0.9` has no wheel for 3.13 and fails to install via `uv sync --extra cartographer`. Use `requests` instead. Update `pyproject.toml` `[project.optional-dependencies].cartographer` to drop `inference-sdk` and add `requests` (already a transitive dep, but make it explicit for the extra).
- **Not the workflow wrapper.** The Roboflow workflow `evans-workspace-drjsi/detect-count-and-visualize` (configured in the project's Roboflow UI) wraps the same model and adds `count_objects` + `annotated_image` outputs, but `serverless.roboflow.com/infer/workflows/{ws}/{id}`, `detect.roboflow.com/infer/workflows/...`, and `infer.roboflow.com/infer/workflows/...` all return 404 / 405 for this workspace+workflow as of 2026-05-05. The workflow's two extra outputs are also redundant with `diagnostic.py`. Call the underlying model `home-village-building-detector/3` directly.

Reference smoke test: `scripts/roboflow_smoke.py` (committed) demonstrates the working call shape and is the canonical "API key works" check.

Accepted detections feed forward to alignment per PRD §4.6. Sub-threshold detections are passed to the diagnostic stage and rendered in a contrasting color per PRD §4.7. They are not emitted to JSON.

Mock-based unit tests cover Roboflow response parsing and confidence filtering. The integration path (real network call) is exercised in issue 031, gated on `requires_roboflow_api_key`.

If `ROBOFLOW_API_KEY` is unset, the module raises a typed exception with a clear message ("Set ROBOFLOW_API_KEY to run real detection. To run with stub detections instead, …"). The pipeline still runs end-to-end against synthetic inputs in unit tests via mocks.

Accepted detections feed forward to alignment per PRD §4.6. Sub-threshold detections are passed to the diagnostic stage and rendered in a contrasting color per PRD §4.7. They are not emitted to JSON.

Mock-based unit tests cover Roboflow response parsing and confidence filtering. The integration path (real network call) is exercised in issue 031, gated on `requires_roboflow_api_key`.

If `ROBOFLOW_API_KEY` is unset, the module raises a typed exception with a clear message ("Set ROBOFLOW_API_KEY to run real detection. To run with stub detections instead, …"). The pipeline still runs end-to-end against synthetic inputs in unit tests via mocks.

## Acceptance criteria

- [ ] `detect.py` calls `https://detect.roboflow.com/{project_name}/{dataset_version}` directly via `requests.post` (no `inference-sdk` import, no workflow URL).
- [ ] `pyproject.toml` `[project.optional-dependencies].cartographer` drops `inference-sdk` and lists `requests` explicitly.
- [ ] `Detection` dataclass populated from real responses (bbox-center → xyxy conversion verified in unit tests).
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
