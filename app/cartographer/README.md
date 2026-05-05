# Cartographer

**Status: deferred to v2.**

This package is a stub in v1. Its architectural contract is committed in `app/docs/technical.md` §7 and `app/docs/prd.md` §5.3. Implementation does not begin until the MVP-Real milestone is complete.

## Pipeline (planned, v2)

```
screenshot.png
  → Stage 1: Image preprocessing (cartographer/preprocess.py)
  → Stage 2: Roboflow object detection (cartographer/detect.py)
  → Stage 3: Bbox-to-grid alignment (cartographer/align.py)
  → Stage 4: Schema emission (cartographer/emit.py)
  → BaseLayout JSON (same schema as hand-built bases)
```

## Roboflow integration (planned)

- Model training happens off-codebase in Roboflow's UI.
- Repo only contains inference glue + `BaseLayout` emission.
- Project + dataset version pinned in `app/data/cartographer_config.json`.
- Hosted inference reads the Roboflow API key from `ROBOFLOW_API_KEY`.
- Keep the key in a local root `.env` file or shell environment; never commit it.

Example `.env`:

```dotenv
ROBOFLOW_API_KEY=your_roboflow_api_key_here
```

PowerShell setup for the current terminal:

```powershell
$env:ROBOFLOW_API_KEY = "your_roboflow_api_key_here"
```

Issue 027's real detector should fail with a clear setup message when
`ROBOFLOW_API_KEY` is unset.

## v1 commitments

The `BaseLayout` schema is **frozen at v1**. v2 Cartographer needs are satisfied by adding optional fields under a new `schema_version`, never by introducing a separate Cartographer-specific layout type. This is the universal-contract guarantee that makes v2 a purely additive feature.
