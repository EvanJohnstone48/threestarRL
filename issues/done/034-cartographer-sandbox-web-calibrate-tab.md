# 034 — Sandbox-web Cartographer tab: calibrate mode

**GitHub Issue:** #34

## Parent PRD

`app/docs/cartographer/prd.md` (§4.7-bis)

## What to build

A new fourth tab in `app/sandbox_web/` named `cartographer`, plus a small FastAPI server in `app/cartographer/server.py` that the CLI uses to host the SPA and round-trip data. This issue covers calibrate mode only; review mode is issue 035.

### Backend (`app/cartographer/server.py`)

A FastAPI application with these endpoints:

- `GET /api/screenshots` → `[{ filename, image_url, detections: [{class_name, bbox_xyxy, confidence}, ...] }, ...]` for the screenshots passed via CLI.
- `GET /api/buildings` → footprint sizes from `app/data/buildings.json` (so the frontend knows each class's `N×N`).
- `GET /api/config` → current `app/data/cartographer_config.json` contents (the frontend needs `dataset_version` to write into the calibration file).
- `POST /api/calibration` → accepts a list of `{ filename, class_name, bbox_xyxy, placed_anchor_xy }` records; per class, computes `offset_i = placed_anchor_xy - bbox_bottom_center`, takes the median across instances, writes `app/data/cartographer_calibration.json` (per the schema in issue 033) with the current `dataset_version`, returns 200, then triggers shutdown.
- Static-serves the built sandbox-web SPA at `/`.

The Roboflow inference call from issue 027 is invoked **once per screenshot at server startup** and cached in memory; the GET endpoint serves from the cache so frontend interactions cost no inference quota. The server reuses `cartographer.detect.run` (or whatever public function issue 027 lands) — it does NOT make its own HTTP call and does NOT import `inference-sdk`. See issue 027 for why: Python 3.13 wheel gap + the Roboflow workflow router 404s, so the underlying model endpoint is called directly via `requests`.

### CLI subcommand

`uv run python -m cartographer calibrate --in <path>...`:

1. Build the sandbox-web SPA if not already built (or document the prerequisite of running `npm run build` in `app/sandbox_web/`).
2. Boot the FastAPI server on a free localhost port.
3. Open the user's default browser at `http://localhost:<port>/?tab=cartographer&mode=calibrate` (use `webbrowser.open`).
4. Block until `POST /api/calibration` arrives, then shut down cleanly.

### Frontend (sandbox-web)

- Add `"cartographer"` to the `Tab` union in `app/sandbox_web/src/App.tsx`; render a new `CartographerPage` when active.
- New file `app/sandbox_web/src/cartographer/CartographerPage.tsx`:
  - Reads `?mode=` query param. This issue handles `mode=calibrate`; `mode=review` is a stub that issue 035 fills in.
  - Calibrate mode:
    - Fetches `/api/screenshots`, `/api/buildings`, `/api/config` on mount.
    - Renders the active screenshot (with thumbnail strip if multiple).
    - Overlays each detection's bbox on the screenshot.
    - For each detection, renders a draggable `N×N` footprint highlight (size from `/api/buildings`) initially anchored at the bbox bottom-center.
    - User drags a footprint by clicking and moving (mouse events on a canvas or an overlay div); release commits the placed anchor pixel.
    - "Save & exit" button POSTs the full `{ filename, class_name, bbox_xyxy, placed_anchor_xy }[]` payload to `/api/calibration`.
- Reuse styling and any iso/footprint rendering helpers from the existing editor (`app/sandbox_web/src/editor/`) and sprite calibrator (`app/sandbox_web/src/sprites/`) where reasonable, but a new page module is fine — calibration is a distinct enough flow.

### Aggregation logic (backend)

Per-class median, not mean. For class `C` with `K_C` instances in the POST payload, compute `[(placed.x - bbox_bottom_center.x), (placed.y - bbox_bottom_center.y)]` for each, then take the median across `x` and `y` independently. Write `offsets[C] = [median_dx, median_dy]` and `sample_counts[C] = K_C`. Classes with zero instances in the payload are omitted from `offsets` (the loader from issue 033 returns zero for missing keys).

### Tests

- Backend unit test on the median aggregator with synthetic POST payloads (single instance, multiple instances, mixed classes).
- Backend smoke test that stands up the FastAPI app with a mocked Roboflow detect call, hits each GET endpoint, and POSTs a synthetic calibration payload, asserting the resulting JSON file matches expectations and the server shuts down.
- Frontend smoke (manual, documented): run `cartographer calibrate --in <example screenshot>`, drag at least one footprint, save, verify `cartographer_calibration.json` updates. Sample screenshots for the smoke test live in `app/data/base_screenshots/` (50 TH6 home-village JPGs).

## Acceptance criteria

- [ ] Sandbox-web has four tabs: `viewer`, `editor`, `sprites`, `cartographer`.
- [ ] `app/cartographer/server.py` exposes all four endpoints documented above.
- [ ] `cartographer calibrate --in <path>...` boots the server, opens a browser, accepts POST, writes `cartographer_calibration.json`, shuts down.
- [ ] Calibrate mode renders bbox overlays and draggable footprint highlights for every detection.
- [ ] Per-class offsets are stored as medians; sample counts are recorded.
- [ ] Backend unit + smoke tests pass.
- [ ] Manual smoke test documented in `app/cartographer/README.md`.

## Blocked by

- Blocked by `issues/open/026-cartographer-roboflow-dataset-and-model.md` (need real Roboflow detections).
- Blocked by `issues/open/027-cartographer-real-roboflow-detection.md` (need the inference call wired up).
- Blocked by `issues/open/033-cartographer-calibration-format-and-loader.md` (file format + Pydantic model).

## User stories addressed

Parent PRD user stories: 11, 14.
