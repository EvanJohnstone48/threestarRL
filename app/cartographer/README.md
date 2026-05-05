# Cartographer

Converts TH6 home-village screenshots into `BaseLayout` JSON via a seven-stage ML pipeline.

See `app/docs/cartographer/prd.md` for the full design. CLI entry point: `app/cartographer/cli.py`.

## Pipeline

```text
screenshot.png
  -> Stage 1: preprocess.py   - load + normalise image
  -> Stage 2: detect.py       - Roboflow object detection (requests to detect.roboflow.com)
  -> Stage 3: grid.py         - iso-grid derivation (pitch + origin)
  -> Stage 4: align.py        - bbox -> tile origin (calibrated offsets + iso-basis inversion)
  -> Stage 5: walls.py        - wall tile classification (convex-hull + colour threshold)
  -> Stage 6: emit.py         - BaseLayout schema emission
  -> Stage 7: diagnostic.py   - co-located .diag.png overlay
  -> BaseLayout JSON
```

## Setup

```dotenv
ROBOFLOW_API_KEY=your_key_here
```

PowerShell:

```powershell
$env:ROBOFLOW_API_KEY = "your_key_here"
```

Git Bash:

```bash
export ROBOFLOW_API_KEY="your_key_here"
```

## Ingest

```powershell
python -m cartographer ingest --in path/to/screenshot.png
```

Output defaults to `app/data/scraped_bases/<stem>.json`. Override with `--out`.

## Calibrate

Run the HITL calibration workflow to align per-class offsets:

```powershell
python -m cartographer calibrate
```

By default this loads every `.jpg`, `.jpeg`, and `.png` in
`app/data/base_screenshots`. You can still pass a specific file or folder:

```powershell
python -m cartographer calibrate --in app/data/base_screenshots/base_01.jpg
python -m cartographer calibrate --in app/data/base_screenshots
```

This:

1. Calls Roboflow once per screenshot and caches detections in memory.
2. Boots a local FastAPI API server on a free port.
3. Opens sandbox-web at `http://localhost:5173/?tab=cartographer&mode=calibrate&api=http://127.0.0.1:<port>`.
4. In the browser: drag each blue dot onto the center of that building's ground footprint.
5. Click **Save & next** to write calibration samples, recompute offsets, and move to the next screenshot.
6. Click **Save & stop** when you want to finish early, or **Save & finish** on the last screenshot.

Start sandbox-web first if it is not already running:

```powershell
cd app/sandbox_web
npm run dev
```

Then run the Cartographer command from the repo root in a second terminal.

Set `SANDBOX_WEB_URL` if the sandbox-web dev server is not on `http://localhost:5173/`.

### Manual Smoke Test

1. Set `ROBOFLOW_API_KEY`.
2. In `app/sandbox_web/`, run `npm run dev` if the Vite server is not already running.
3. From the repo root, run `python -m cartographer calibrate`.
4. Browser opens automatically; at least one detection bbox should appear.
5. Drag a blue dot to the correct footprint center and click **Save & next**.
6. Verify `app/data/cartographer_calibration.json` is updated with non-zero offsets and a `sample_counts` entry.

### What The Blue Dot Means

The orange rectangle is the Roboflow visual detection box. The blue dot is the
human-marked center of the building's footprint on the grass grid:

- 2x2 and 4x4 buildings: place the dot on the shared inner border point of the
  middle tiles.
- 3x3 buildings: place the dot at the center of the middle footprint tile.

The saved offset is:

```text
footprint_center_pixel - detection_bbox_bottom_center_pixel
```

When a previous calibration file exists for the same dataset version, new
calibration sessions start each blue dot at `bbox bottom-center + saved offset`
for that class. On save, new offset samples are merged with previous samples and
the per-class median is recomputed. This makes calibration iterative: each new
batch should require smaller adjustments.

## Calibration File Format

`app/data/cartographer_calibration.json` follows `CalibrationFile` (see `calibration.py`):

```json
{
  "dataset_version": "1",
  "offsets": { "cannon": [0.0, -8.5], "archer_tower": [0.0, -10.2] },
  "calibrated_at_utc": "2026-05-05T12:00:00+00:00",
  "sample_counts": { "cannon": 12, "archer_tower": 7 },
  "samples": [
    { "class_name": "cannon", "offset": [0.0, -8.5] }
  ]
}
```
