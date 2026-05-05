# 035 — Sandbox-web Cartographer tab: review mode and `--review` CLI flag

**GitHub Issue:** #35

## Parent PRD

`app/docs/cartographer/prd.md` (§4.7-bis)

## What to build

Extend the Cartographer tab and FastAPI server from issue 034 with a "review" mode and wire it to a new `--review` flag on `cartographer ingest`. Review mode is a HITL gate between alignment and emission; it lets the user correct individual placements without touching the per-class calibration table.

### Backend extensions (`app/cartographer/server.py`)

Add two endpoints:

- `GET /api/review/baselayout` → `{ screenshot_url, candidate_baselayout, derived_pitch_px, derived_origin_px }`. The candidate is the `BaseLayout` produced by alignment (pre-walls, pre-emit).
- `POST /api/review/baselayout` → accepts `{ corrected_placements: [{ building_type, origin: [r, c] }, ...] }`. The server replaces the candidate's `placements` with the corrected list, runs the `walls` and `emit` stages, writes the final JSON to the configured output path with `provenance.reviewed = true`, returns 200, and triggers shutdown.

The server runs in one of three modes per CLI invocation: `calibrate` (issue 034), `review` (this issue), or `static` (no API, just SPA — not used yet, kept as a hook). Mode is set at boot.

### Pipeline integration

When `--review` is passed to `cartographer ingest`:

1. Run `preprocess → detect → grid → align` as normal.
2. Boot the server in `review` mode with the candidate `BaseLayout` (and the source screenshot path + derived grid params) pre-loaded.
3. Open the browser at `http://localhost:<port>/?tab=cartographer&mode=review`.
4. On `POST /api/review/baselayout`, run `walls` on the corrected placements and `emit` to produce the final JSON. `provenance.reviewed` is set to `true`. The diagnostic PNG is rendered against the corrected layout (not the original candidate).

If the server is closed without a POST (browser tab closed, ctrl-C), the pipeline aborts with a typed exception and writes the original candidate's diagnostic PNG. No JSON is emitted.

Per-instance review corrections do NOT update `cartographer_calibration.json`. Review corrections are one-off, not training signal — this matches PRD §4.7-bis.

### Frontend extensions

`app/sandbox_web/src/cartographer/CartographerPage.tsx`, `?mode=review`:

- Fetch `/api/review/baselayout` on mount.
- Render the screenshot with each candidate placement drawn as a draggable `N×N` footprint highlight (initial position from the candidate; size from `/api/buildings`).
- User drags any placement to a different tile; release commits the new tile origin.
- "Save corrected layout" button POSTs `{ corrected_placements }` to `/api/review/baselayout`. UI shuts down on success (200 response).
- A "Discard" affordance (closes the tab without POSTing) is acceptable but not required.

### Tests

- Backend unit test: synthesise a candidate `BaseLayout` and a simulated review-correction payload, hit `POST /api/review/baselayout`, assert the saved JSON has the corrected placements, `provenance.reviewed` is `true`, and `cartographer_calibration.json` was NOT modified.
- Backend smoke test: stand up the server in review mode against a fixture, hit GET, hit POST, assert shutdown.
- Frontend smoke (manual, documented): run `cartographer ingest --review --in <example>`, drag a placement, save, verify the resulting JSON.

## Acceptance criteria

- [ ] `cartographer ingest --review --in <path>` runs preprocess → detect → grid → align, boots server in review mode, opens browser at `?mode=review`.
- [ ] User can drag any placement to a new tile origin and save.
- [ ] Saved JSON has `provenance.reviewed = true` and the corrected placements.
- [ ] `cartographer_calibration.json` is NOT modified by review-mode saves.
- [ ] Closing the browser without saving aborts the pipeline cleanly (no JSON, diagnostic PNG produced).
- [ ] Backend unit + smoke tests pass.
- [ ] Manual smoke test documented in `app/cartographer/README.md`.

## Blocked by

- Blocked by `issues/open/034-cartographer-sandbox-web-calibrate-tab.md` (server + tab scaffolding).
- Blocked by `issues/open/030-cartographer-wall-classification.md` (review re-runs walls on corrected placements).

## User stories addressed

Parent PRD user stories: 5, 17.
