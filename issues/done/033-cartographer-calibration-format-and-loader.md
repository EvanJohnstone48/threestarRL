# 033 — Cartographer calibration data format and align loader

**GitHub Issue:** #33

## Parent PRD

`app/docs/cartographer/prd.md` (§4.6, §4.7-bis)

## What to build

**AFK.** Define the calibration file format and a loader that the `align` stage (issue 029) can call. No UI in this issue; UI lands in 034.

### File format

`app/data/cartographer_calibration.json`:

```json
{
  "dataset_version": "1",
  "offsets": {
    "cannon": [0.0, -3.5],
    "archer_tower": [0.0, -8.2]
  },
  "calibrated_at_utc": "2026-05-05T12:34:56Z",
  "sample_counts": {
    "cannon": 12,
    "archer_tower": 7
  }
}
```

- `dataset_version` — the Roboflow dataset version this calibration was performed against (matches `cartographer_config.json#dataset_version`).
- `offsets` — per-class screen-pixel offset `(dx, dy)` from `bbox_bottom_center` to the user-placed footprint anchor (positive `dy` = pixels downward).
- `calibrated_at_utc` — ISO-8601 UTC timestamp.
- `sample_counts` — number of detections used to compute each class's median.

Define a Pydantic model `CalibrationFile` in `app/cartographer/calibration.py` that validates the schema and round-trips cleanly when the calibration UI from issue 034 writes the file.

### Loader

Implement `cartographer.calibration.load_offsets(config_dataset_version: str) -> dict[str, tuple[float, float]]`:

- File missing → returns `{}`, logs `WARN cartographer: no calibration file found at <path>, using zero offsets`.
- File present but malformed (JSON parse fail, or Pydantic validation fail) → returns `{}`, logs `WARN cartographer: calibration file at <path> is malformed (<reason>), using zero offsets`.
- File present and valid but `dataset_version` does not match `config_dataset_version` → returns `{}`, logs `WARN cartographer: calibration is for dataset_version <X>, current is <Y>, using zero offsets`.
- File present, valid, version match → returns `{class_name: (dx, dy), ...}` and logs `INFO cartographer: loaded calibration for <N> classes (dataset_version <X>)`.

The loader logs each warning at most once per process (use a module-level guard) so re-loading inside long-lived servers (issue 034/035) does not spam logs.

The `align` stage from issue 029 calls `load_offsets(...)` once at entry and uses `offsets.get(class_name, (0.0, 0.0))` per detection.

### Tests

Unit tests for each of the four loader cases above plus a Pydantic round-trip test on a synthetic valid file. No CI freshness check is added; the design choice (calibration is advisory, never blocks) is documented in the module docstring.

## Acceptance criteria

- [ ] `app/cartographer/calibration.py` exists with `CalibrationFile` Pydantic model and `load_offsets(...)`.
- [ ] All four loader cases return `{}` or a dict with the documented log lines.
- [ ] One-warning-per-process behaviour holds across repeated calls.
- [ ] Unit tests cover: missing file, malformed JSON, version mismatch, valid file, Pydantic round-trip.
- [ ] No CI freshness check; design rationale in module docstring.

## Blocked by

- Blocked by `issues/open/025-cartographer-package-skeleton-cli-tracer.md`.

## User stories addressed

Parent PRD user stories: 14, 17.
