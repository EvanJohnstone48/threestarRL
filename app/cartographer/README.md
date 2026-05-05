# Cartographer

Converts TH6 home-village screenshots into `BaseLayout` JSON via a seven-stage ML pipeline.

See `app/docs/cartographer/prd.md` for the full design. CLI entry point: `app/cartographer/cli.py`.

## Pipeline

```
screenshot.png
  → Stage 1: preprocess.py   — load + normalise image
  → Stage 2: detect.py       — Roboflow object detection (requests to detect.roboflow.com)
  → Stage 3: grid.py         — iso-grid derivation (pitch + origin)
  → Stage 4: align.py        — bbox → tile origin (calibrated offsets + iso-basis inversion)
  → Stage 5: walls.py        — wall tile classification (convex-hull + colour threshold)
  → Stage 6: emit.py         — BaseLayout schema emission
  → Stage 7: diagnostic.py   — co-located .diag.png overlay
  → BaseLayout JSON
```

## Setup

```dotenv
ROBOFLOW_API_KEY=your_key_here
```

PowerShell:
```powershell
$env:ROBOFLOW_API_KEY = "your_key_here"
```

## Ingest

```powershell
python -m cartographer ingest --in path/to/screenshot.png
```

Output defaults to `app/data/scraped_bases/<stem>.json`. Override with `--out`.

## Calibrate

Run the HITL calibration workflow to align per-class offsets:

```powershell
python -m cartographer calibrate --in app/data/base_screenshots/base_01.jpg
```

This:
1. Calls Roboflow once per screenshot and caches detections in memory.
2. Boots a local FastAPI server and opens `http://localhost:<port>/?tab=cartographer&mode=calibrate`.
3. In the browser: drag each coloured footprint highlight onto its true ground-truth anchor.
4. Click **Save & exit** — the server writes `app/data/cartographer_calibration.json` and shuts down.

### Manual smoke-test checklist

1. `$env:ROBOFLOW_API_KEY = "..."` — set key.
2. `python -m cartographer calibrate --in app/data/base_screenshots/base_01.jpg`
3. Browser opens automatically; at least one detection bbox should appear.
4. Drag a footprint highlight to the correct building anchor and click **Save & exit**.
5. Verify `app/data/cartographer_calibration.json` is updated with non-zero offsets and a `sample_counts` entry.

> If the sandbox-web SPA is not built yet, run `npm run build` in `app/sandbox_web/` first.
> The server serves static assets from `app/sandbox_web/dist/`.

## Calibration file format

`app/data/cartographer_calibration.json` follows `CalibrationFile` (see `calibration.py`):

```json
{
  "dataset_version": "1",
  "offsets": { "cannon": [0.0, -8.5], "archer_tower": [0.0, -10.2] },
  "calibrated_at_utc": "2026-05-05T12:00:00+00:00",
  "sample_counts": { "cannon": 12, "archer_tower": 7 }
}
```
