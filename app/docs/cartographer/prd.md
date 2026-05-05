# The Cartographer — PRD

**Status: design committed. Implementation begins after MVP-Real (v2 milestone, per `app/docs/prd.md` §4 and `app/docs/roadmap.md`).**

This PRD supersedes the prior stub. It commits the v2 design at a level of detail sufficient to begin implementation issues. It is the output of a dedicated grilling session and should be read alongside the architecture-level commitments already in `app/docs/prd.md` §5.3 and `app/docs/technical.md` §7.

## 1. Problem Statement

The agent trained under MVP-Real plays only synthetic bases — hand-built TH6 layouts and their mutations. The headline research question for v2 is whether that agent transfers to real bases. To answer it we need real bases in the simulator, which means turning Clash of Clans base screenshots into `BaseLayout` JSONs that the Sandbox can load.

Manually authoring each scraped base in the sandbox-web editor is too slow to support a meaningful real-base eval set (target: tens to low hundreds of bases), and manual transcription introduces the same human bias the synthetic-to-real experiment is supposed to control for. There is no automated path today.

## 2. Solution

A single-screenshot ingestion pipeline that reads one TH6 home-village screenshot (captured under controlled conditions defined in §6.1) and emits a `BaseLayout` JSON. The pipeline:

1. Detects every building with a Roboflow object-detection model trained on real screenshots, using a type-only class taxonomy (no level discrimination).
2. Derives the per-image grid `(pitch, origin)` by analysing the light/dark grass checker pattern in non-building regions, exploiting CoC's fixed 2:1 isometric projection (angles are constant, only pitch and origin vary per image).
3. Snaps each detection to an integer tile origin using the derived grid and a class-driven footprint catalog.
4. Classifies wall tiles by stone-vs-grass color matching on the per-tile crops not covered by buildings.
5. Assembles a `BaseLayout` (with new `provenance` metadata under bumped `schema_version: 2`), validates it through Pydantic, and writes the JSON.
6. Always emits a diagnostic PNG showing the inferred grid, accepted detections, dropped low-confidence detections, and classified wall tiles, regardless of success or failure.

Failure modes are loud: ambiguous grid, overlapping placements, schema violations, or zero detections raise a typed exception and produce no JSON. The pipeline does not silently degrade; the diagnostic PNG is the recovery affordance, not an automated retry.

## 3. User Stories

1. As the project owner, I want to drop a screenshot file into a CLI command and get back a validated `BaseLayout` JSON, so that I can grow my real-base eval set without manual transcription.
2. As the project owner, I want every successful ingestion to be reproducible from inputs alone, so that re-running the pipeline on the same screenshot produces the same JSON byte-for-byte (modulo timestamps in `provenance`).
3. As the project owner, I want pipeline failures to halt loudly and write a diagnostic PNG, so that I can see exactly which stage failed and why without re-running the pipeline in a debugger.
4. As the project owner, I want the pipeline to tolerate scale variation (the same base captured at slightly different zoom levels), so that I do not have to standardise zoom across screenshots.
5. As the project owner, I want the pipeline to refuse to produce output rather than produce wrong output, so that no garbage `BaseLayout` ever enters the eval set.
6. As the project owner, I want a per-image grid overlay visualised on the diagnostic PNG, so that I can verify by eye that the grid landed on the right tile boundaries.
7. As the project owner, I want sub-threshold detections shown in a different color on the diagnostic PNG, so that I can see what Roboflow nearly accepted and decide whether to retrain or relax the threshold.
8. As the project owner, I want to override the output filename via a CLI flag, so that I can name a base when I have a specific identifier in mind.
9. As the project owner, I want the default output filename to mirror the input basename, so that batch ingestion of many screenshots in a directory needs no naming logic.
10. As the project owner, I want all Roboflow class names to equal keys in `app/data/buildings.json` exactly, so that the alignment stage requires no translation table and class drift is caught by a CI test.
11. As the project owner, I want Roboflow API access gated by a single environment variable, so that the API key never touches the repo and contributors without a key still pass non-network tests.
12. As the project owner, I want the pipeline to consume the existing hosted Roboflow inference endpoint by default, so that I do not maintain weights or a local inference container.
13. As the project owner, I want the pipeline to be swappable to local inference without rewriting downstream stages, so that future offline ingestion is a single-module change.
14. As the project owner, I want grid derivation, alignment, wall classification, and emission to each be unit-testable on synthetic fixtures with no Roboflow dependency, so that I can iterate on each stage independently and CI does not require a network.
15. As the project owner, I want integration tests that exercise the full pipeline on real screenshots gated on the API key, so that they run in CI when the key is present and skip cleanly when it is not.
16. As the project owner, I want the `BaseLayout` schema to remain backward-compatible after the v2 bump, so that v1-trained agents and v1 sandbox-web continue to load both old and new bases through the migration path.
17. As the project owner, I want every Cartographer-emitted `BaseLayout` to carry provenance (source screenshot, ingest timestamp, dataset version, derived grid params, per-placement confidence), so that when the agent fails on an ingested base I can retrospectively diagnose why without re-running the pipeline.
18. As the project owner, I want the simulation to receive bases at canonical TH6-max stats regardless of the real base's actual building levels, so that the v2 eval is an honest test of the trained agent's policy on synthetic-distribution stats.
19. As the project owner, I want the wall classifier to use only the derived grid and a stone-color test, so that wall labelling is not a Roboflow class and dataset labelling cost stays in the low thousands of boxes per dataset version.
20. As the project owner, I want the pipeline to assume a fixed CoC isometric projection (2:1 axes) and a fixed playable grid size (44×44), so that I do not pay implementation cost to detect them per image.
21. As the project owner, I want the per-image grid pitch and origin derived from the grass checker pattern, so that mild zoom variation between screenshots does not break ingestion.
22. As a future contributor reading the code cold, I want each pipeline stage in its own module with a stable function-level interface, so that I can understand and modify any one stage without paging in the others.
23. As a future contributor, I want a `pipeline.py` module that orchestrates the seven stages in a fixed order with explicit data flow, so that the control plane is in one file and not scattered across stage modules.
24. As the Sandbox, I want every Cartographer output to validate against the same Pydantic schema as hand-built bases, so that I do not branch loading logic on origin.
25. As the Barracks, I want Cartographer-emitted bases to be drop-in interchangeable with hand-built bases for `env.reset()`, so that no env-side changes are needed to incorporate scraped bases into the eval distribution.

## 4. Implementation Decisions

### 4.1 Pipeline shape

The pipeline is seven sequential stages, each in its own module, orchestrated by `pipeline.py`:

1. **preprocess** — load the screenshot and convert to HSV.
2. **detect** — call Roboflow inference, return a list of `Detection` records (class, bbox, confidence).
3. **grid** — derive `(pitch, origin)` from the light/dark grass checker pattern in non-building regions.
4. **align** — convert each detection's bbox center to fractional tile coordinates via the iso basis, subtract half-footprint (looked up by class), round to the nearest integer tile origin, and reverse-project to sanity-check the result.
5. **walls** — for every tile inside the convex hull of detections that is not covered by a building footprint, classify wall vs. non-wall by stone-color match.
6. **emit** — assemble a `BaseLayout` (with `provenance`), validate via Pydantic, and write JSON.
7. **diagnostic** — render an annotated PNG showing the inferred grid, accepted detections, sub-threshold detections, and classified walls. Always runs, even on failure.

### 4.2 Coordinate system

The pipeline operates in iso pixel space throughout. CoC's 2:1 isometric projection has fixed basis angles (`±atan(1/2) ≈ ±26.565°`), hardcoded as a constant. Per-image free parameters are pitch (a scalar, in pixels) and origin (a 2D pixel coordinate). Pixel-to-tile conversion uses `inv([v1 v2]) · (p − origin)` where `v1` and `v2` are the two iso basis vectors scaled to pitch length.

No homography or perspective warp is applied. No resampling. The grid extent is hardcoded at 44×44 tiles per `BaseLayout` schema.

### 4.3 Grass-grid derivation

Algorithm:

1. **Grass mask.** HSV hue-range filter for CoC's grass green, restricted to the convex hull of Roboflow bboxes (so unplayable surroundings are excluded), with all bbox interiors plus a small dilation margin removed.
2. **Light/dark labelling.** Otsu threshold on the V channel within the grass mask, producing a binary checker map.
3. **Pitch and phase per axis.** For each iso axis, project labelled pixels onto the perpendicular direction, build a 1D autocorrelation of the binary signal, and extract pitch from the dominant non-zero-lag peak and origin offset from the phase.
4. **Cross-validation.** Pitch estimates from axis-1 and axis-2 must agree within ±2%. If they do not, the stage raises and the pipeline aborts with a diagnostic PNG.

### 4.4 Roboflow class taxonomy

One class per TH6 building type with no level discrimination. Walls are intentionally not a class (handled in §4.5). Class set, locked to the keys in `app/data/buildings.json`:

`cannon`, `archer_tower`, `mortar`, `air_defense`, `wizard_tower`, `town_hall`, `clan_castle`, `army_camp`, `barracks`, `lab`, `spell_factory`, `gold_mine`, `elixir_collector`, `gold_storage`, `elixir_storage`, `builders_hut`.

Class-name parity with `buildings.json` is enforced by a unit test (AC-C8). Roboflow class renames or additions break CI before they break inference.

All detected buildings are simulated at TH6-max stats. The level field on `BuildingType` is not populated from the screenshot.

### 4.5 Wall handling

Walls are not detected by Roboflow. After grid derivation and bbox alignment, every tile inside the convex hull of accepted detections that is not covered by a placed building's footprint is a wall candidate. Each candidate's pixel region is sampled and classified wall vs. non-wall by RGB distance to a calibrated stone-color centroid. Tiles classified as walls are added to the `BaseLayout.placements` list with type `wall`. Tiles classified as non-wall (open ground, decorations, obstacles) are left empty.

This composes naturally with the grass-grid step: walls break the grass pattern locally but enough surrounding grass exists to derive the lattice. The classifier requires no ML and no Roboflow data labelling cost.

### 4.6 Detection-to-grid alignment

Footprint comes from class label, not bbox dimensions. Each class maps deterministically to a footprint (e.g., `cannon → 3×3`, `town_hall → 4×4`) loaded from `app/data/buildings.json`.

The alignment anchor is the bbox **bottom-center** pixel `(bbox_x_center, bbox_y_max)`, not the bbox center. Sprite vertical heights vary widely by class (Town Hall is tall, builder's hut is short), but every CoC sprite's base sits flush with the bottom apex of its tile-footprint diamond, so bottom-center is the most class-invariant pixel anchor. A per-class screen-pixel offset `(dx, dy)` from `app/data/cartographer_calibration.json` is added to the bottom-center to recover the true footprint anchor pixel; the offset table is calibrated once per Roboflow `dataset_version` via the sandbox-web Cartographer tab (§4.7-bis). A missing or stale calibration table is non-fatal — `align` falls back to zero offsets with a warning, never blocks ingestion.

The footprint anchor pixel is converted to fractional tile coordinates via the iso basis + derived `(pitch, origin)`. For an `N×N` footprint, the top-left tile is at `round(anchor_tile_frac − (N, N))`. The integer origin is reverse-projected back to a predicted anchor pixel; predicted vs. observed distance is asserted ≤ 0.5 tile. This works uniformly for 2×2, 3×3, 4×4, and 5×5 footprints — no even/odd parity special-case is required.

If two detections round to overlapping tile origins, the stage raises and the pipeline aborts with a diagnostic PNG. There is no automated tie-breaking by confidence or any other heuristic.

The grid frame derived from grass tiles is local — it pins pitch and a phase, but not an absolute (0,0) on the 44×44 schema grid. After alignment, the convex-hull centroid of all placed building footprints is translated to grid `(22, 22)` to commit to the schema frame. This is contracted only for TH6 bases, which never extend close to the playable boundary (§4.11). Future TH-level expansion will need an explicit boundary-derivation strategy. Edge-pushed TH6 bases land off-center in the resulting JSON; this is acceptable for the v2 eval set. If centering would push any placement outside the 44×44 grid, the stage raises and the pipeline aborts.

This decision overrides the wording in `technical.md` §7.1 ("infer footprints from bbox size + class-specific footprint catalog"). Footprints are class-driven; bbox size is sanity-check only. `technical.md` will be updated as part of v2 rollout.

### 4.7 Confidence handling

A single global `confidence_threshold` applies to all classes, defaulting to `0.5` and stored in `app/data/cartographer_config.json`. Detections at or above threshold are emitted to JSON; below-threshold detections are omitted from JSON but rendered onto the diagnostic PNG in a contrasting color so a human reviewer can decide whether a class is systematically weak and warrants more training data.

There is no auto-completeness check. The pipeline does not assert "this base must contain exactly one Town Hall" or similar. Missing buildings appear as holes in the resulting layout; the diagnostic PNG is the only mitigation.

### 4.7-bis Calibration and review

Per-class screen-pixel offsets `(dx, dy)` from bbox bottom-center to footprint anchor (§4.6) are calibrated once per Roboflow `dataset_version` through a new "Cartographer" tab in `app/sandbox_web/`. The CLI subcommand:

```
uv run python -m cartographer calibrate --in <screenshot.png>...
```

boots a small FastAPI server (`app/cartographer/server.py`) on a free localhost port, runs Roboflow inference once for each input screenshot and caches results in memory, opens the user's default browser at `http://localhost:<port>/?tab=cartographer&mode=calibrate`, and blocks until the user posts their calibration. The page renders each detection's bbox over the screenshot with a draggable `N×N` footprint highlight (size from `buildings.json`); the user drags the highlight until it sits flush with the sprite base. On "Save & exit", the server computes the per-class **median** offset across all detections of that class (median is more robust than mean for the few-shot case), writes `app/data/cartographer_calibration.json`, returns 200, and shuts down.

Calibration file schema:

```
{
  "dataset_version": str,
  "offsets": { class_name: [dx, dy] },
  "calibrated_at_utc": str,
  "sample_counts": { class_name: int }
}
```

A missing, malformed, or `dataset_version`-mismatched calibration table is non-fatal: `align` logs a warning (once per ingest) and uses zero offsets. There is no CI freshness check; recalibration is on the project owner when they bump dataset versions.

The optional `--review` flag on `ingest` invokes the same server pattern in "review" mode after the alignment stage. The server boots with the candidate `BaseLayout` pre-loaded, the browser opens at `?mode=review`, the user drags any wrong placements to their correct tile origin, and on save the server runs walls + emit on the corrected layout and writes the final JSON with `provenance.reviewed = true`. Per-instance review corrections do NOT update `cartographer_calibration.json` — they are one-off fixes for a single base, not training signal for the offsets.

Detection rejection is via the existing global `confidence_threshold` only. Neither calibration nor review mode provides a per-detection reject affordance; missing or unwanted detections are managed by retraining, threshold tuning, or manual sandbox-web edit after emission.

### 4.8 Inference

Hosted Roboflow inference by default. Per-ingest HTTPS call to the project's hosted endpoint. API key loaded from `ROBOFLOW_API_KEY` env var, never committed. `app/data/cartographer_config.json` carries `{ project_name, dataset_version, confidence_threshold }`. Hosted vs. local choice is encapsulated entirely inside the `detect` module; downstream stages depend only on the `Detection` data type.

The `detect` module calls the model directly at `https://detect.roboflow.com/{project_name}/{dataset_version}` with the API key as a query param and the image as base64 in the body. The Roboflow Inference SDK (`inference-sdk`) is unavailable on Python 3.13 wheels as of v0.9; a direct HTTPS POST via `requests` is the supported path until SDK 3.13 wheels land. The Roboflow workflow wrapper `evans-workspace-drjsi / detect-count-and-visualize` (which adds count + annotated image outputs) is intentionally not used — its outputs are duplicated by `diagnostic.py`, and the workflow router currently 404s on every `serverless|detect|infer.roboflow.com/infer/workflows/{ws}/{id}` permutation we tried. Use the model endpoint.

Reference assets for the API call live in `app/cartographer/resources/`:
- `apicall.png` — the Roboflow-generated Python snippet shown in the workspace UI (workspace `evans-workspace-drjsi`, workflow `detect-count-and-visualize`, underlying model `home-village-building-detector/3`).
- `workflow.png` — the Roboflow workflow graph: `image → object detection model → bounding box visualization + property definition (count) → label visualization → outputs (count_objects, output_image, predictions)`.
- `roboflow_example_image.png` — annotated bbox + confidence visualization from a workflow run, useful as a reference for what well-aligned detections look like.
- `roboflow_example_fullimage.png` — a TH6 home-village screenshot used as the smoke-test input by `scripts/roboflow_smoke.py`. On model `home-village-building-detector/3` it returns 46 detections covering all expected TH6 classes (1× town_hall, 1× clan_castle, 2× archer_tower, 3× cannon, 1× mortar, 2× air_defense, 1× wizard_tower, 1× air_sweeper, 6× gold_mine, 6× elixir_collector, 2× gold_storage, 2× elixir_storage, 3× army_camp, 3× barracks, 1× lab, 1× spell_factory, 4× builders_hut, 3× bomb, 2× giant_bomb, 1× air_bomb) with mean confidence ≈0.75. Use this as the canonical "live API works" check.

### 4.9 Output bundle and naming

A successful ingestion produces two files in `app/data/scraped_bases/`:

- `<basename>.json` — the validated `BaseLayout`.
- `<basename>.diag.png` — the annotated diagnostic image.

Default `<basename>` mirrors the input screenshot stem. The CLI accepts an `--out` override for the JSON path (the diagnostic is co-located with the JSON regardless). On failure no JSON is written but the diagnostic PNG is.

### 4.10 Schema impact

`BaseLayout.schema_version` bumps from 1 to 2. The bump introduces a single optional additive field:

- `provenance: CartographerProvenance | None = None`

`CartographerProvenance` carries `{ source_screenshot: str, ingest_timestamp_utc: str, dataset_version: str, confidence_threshold: float, derived_pitch_px: float, derived_origin_px: tuple[float, float], per_placement_confidence: dict[placement_id, float], calibration_dataset_version: str | None, reviewed: bool }`. The two trailing fields default to `None` and `False` respectively for backward-compatibility with the v2 schema bump in issue 024. Hand-built bases continue to write `provenance: None` (or omit). v1 readers that ignore unknown fields continue to load v2 bases; the migration `migrate_baselayout_v1_to_v2` is the no-op identity.

### 4.11 Input scope and assumptions

The v2 pipeline is contracted on screenshots that meet all of:

- Captured by the project owner from the home village (green grass, no custom scenery).
- Scout view (pre-attack).
- Full playable area visible in frame.
- Default device aspect ratio (the project owner's capture device, pinned in `cartographer_config.json` as a sanity-check field).
- Zoom is not pinned; the per-image grid derivation absorbs zoom variation.
- The visible base is roughly screen-centered. The pipeline translates the convex-hull centroid of accepted placements to grid `(22, 22)` to commit to the 44×44 schema frame (§4.6); edge-pushed bases land off-center in the resulting JSON. This contract holds for TH6, which never extends close to the playable boundary; later TH levels will require an explicit boundary-derivation strategy.

Screenshots violating these conditions are out of contract — the pipeline may fail loudly or, worse, succeed with wrong output. Detecting violation automatically (e.g., asserting the screenshot is from the contracted device) is out of scope.

### 4.12 Module structure

```
app/cartographer/
├── __init__.py
├── preprocess.py    # image load, HSV convert
├── detect.py        # Roboflow client + Detection dataclass
├── grid.py          # grass-edge → (pitch, origin)
├── align.py         # bbox → integer tile origin + reverse-projection check
├── walls.py         # per-tile stone-vs-grass classifier
├── emit.py          # BaseLayout assembly, Pydantic validation, JSON write
├── diagnostic.py    # annotated PNG renderer
├── pipeline.py      # orchestration
├── cli.py           # argparse wrapper around pipeline.run()
└── README.md
```

Each stage module exposes a single top-level function with a typed signature. `pipeline.py` calls them in fixed order; on any stage's typed exception it triggers `diagnostic.render(...)` with whatever partial state exists, then re-raises. No state is shared between stages except via return values.

### 4.13 CLI

```
uv run python -m cartographer ingest \
    --in <path/to/screenshot.png> \
    [--out <path/to/output.json>] \
    [--review]

uv run python -m cartographer calibrate \
    --in <path/to/screenshot.png>...
```

`ingest` runs the seven-stage pipeline and writes JSON + diagnostic PNG. `--review` (off by default — preserves user story 1) opens the sandbox-web Cartographer tab in review mode after alignment and lets the user correct individual placements before emit (§4.7-bis).

`calibrate` boots the same server in calibrate mode against one or more screenshots and writes `app/data/cartographer_calibration.json` on save (§4.7-bis).

No batch mode in v2 (single-screenshot per §4.11). No `--no-diagnostic` flag — the diagnostic PNG is always produced.

### 4.14 Training data

Real screenshots only. The project owner captures and labels at least 50 TH6 base screenshots with at least 20 instances per defense class (cannon, archer_tower, mortar, air_defense, wizard_tower) before the model is considered trained. Labelling happens in the Roboflow UI. Synthetic data via sandbox-web is not used and is out of scope; the v1 placeholder geometry is not a useful training distribution for real-screenshot inference.

## 5. Testing Decisions

A good test in this codebase exercises external behavior — the JSON contract, the diagnostic invariants, the failure-mode contract — and avoids asserting on the implementation details of any single stage. Where a stage's behavior *is* the contract (e.g., grid extraction's accuracy), the test asserts on a numerical property (pitch within tolerance), not on intermediate signal shapes.

### 5.1 Unit tests

Each stage module gets unit tests with synthetic fixtures and no Roboflow dependency:

- **grid** — synthesise a checker raster of known pitch and origin, assert recovered values within tolerance. Includes degenerate inputs that must trigger the cross-validation failure.
- **align** — known bbox + known grid → known integer tile origin. Includes an overlapping-detection fixture that must raise.
- **walls** — synthesised stone-textured tile and grass-textured tile fixtures, assert classifier output.
- **emit** — given a synthetic detection list and grid, assert the produced `BaseLayout` round-trips through Pydantic and contains a fully-populated `provenance` field.
- **detect** — Roboflow client mocked; tests exercise response parsing and confidence filtering.

These run in pre-commit (under the `not slow` marker, per `technical.md` §9.6).

Prior art: see existing unit tests for the Sandbox grid helpers (`tests/unit/sandbox_core/`) and reward calculation (`tests/unit/barracks/`). The same fixture style applies — synthesise inputs in-test, assert on outputs.

### 5.2 Integration tests

The full pipeline runs end-to-end on the 20-screenshot eval set, asserting the produced `BaseLayout` matches a hand-labeled ground-truth fixture (with bounded tolerance on per-placement origin). These tests:

- Are marked `@pytest.mark.slow`.
- Are gated on `ROBOFLOW_API_KEY` via a custom `@pytest.mark.requires_roboflow_api_key` marker — they skip cleanly when the env var is absent so contributors without keys still pass locally.
- Run in CI when the secret is configured.

Prior art: the golden replay tests in `tests/golden/replays/` are the closest analogue — frozen fixtures, full-pipeline runs, equality assertions with float tolerance.

### 5.3 Acceptance criteria (v2)

The original AC-C1, AC-C2, AC-C3 in `app/docs/prd.md` §5.3 stand. New ACs from this design:

- **AC-C4 (alignment).** On the 20-screenshot eval set, every accepted detection's tile origin matches the hand-labeled ground-truth origin exactly (zero-tile tolerance) when run with a fresh per-dataset-version calibration. The reverse-projection check fires on the engineered bad-bbox failure fixture and on no others.
- **AC-C5 (walls).** Wall classification on a 5-screenshot wall-labeled subset achieves ≥95% precision and ≥90% recall.
- **AC-C6 (failure handling).** Negative tests covering (i) a screenshot designed to fail grid cross-validation, (ii) two detections engineered to overlap, (iii) a screenshot with zero detections, and (iv) a placement that would be pushed outside the 44×44 grid by hull-centroid centering — assert no JSON is written, the typed exception is raised, and the diagnostic PNG is produced.
- **AC-C7 (provenance).** Every successful ingestion produces a JSON whose `provenance` is fully populated (including `calibration_dataset_version` and `reviewed`) and round-trips through Pydantic v2 cleanly.
- **AC-C8 (class naming parity).** A CI test loads the Roboflow class list and the keys of `app/data/buildings.json` (excluding `wall`) and asserts set equality.
- **AC-C9 (calibration roundtrip).** Calibrating against a synthetic detection set with known ground-truth offsets produces a `cartographer_calibration.json` whose recovered per-class offsets match ground truth within ±2 pixels.
- **AC-C10 (review roundtrip).** Invoking `--review` on a screenshot with one engineered misalignment, then dragging the footprint to the correct tile, produces a `BaseLayout` whose corrected placement matches ground truth and whose `provenance.reviewed` is `True`.
- **AC-C11 (calibration fallback).** Running `ingest` with no `cartographer_calibration.json` present logs a single warning and proceeds with zero offsets, producing valid JSON.

## 6. Out of Scope

### 6.1 Out of scope for v2

- Multi-screenshot ingestion or multi-zoom stitching for one base.
- Auto-cropping, auto-zoom-detection, or device-agnostic ingestion. v2 contracts on the project owner's capture conditions only.
- Custom scenery, skins, or non-grass home-village backgrounds.
- Detecting building levels, troop levels, hero levels, or any non-layout metadata. All buildings simulate at TH6-max.
- Roboflow as a wall detector. Walls go through the post-grid color classifier.
- Synthetic training data via sandbox-web. Training is real-only.
- Local Roboflow inference. Hosted only in v2; the swap point is the `detect` module.
- Manual-recovery integration into sandbox-web. Failed ingestions produce a diagnostic PNG; the recovery path is "author this base manually in sandbox-web" or "fix the input."
- Auto-id generation, counter files, or batch ingestion modes. One screenshot, one CLI invocation.
- Auto-completeness checks (e.g., "every TH6 base has exactly one Town Hall"). Holes are visible in the diagnostic PNG and that is the mitigation.
- Base-archetype classification (ring vs compartment vs anti-three-star). Out of scope; orthogonal CV problem.
- Per-class confidence thresholds. Single global threshold for v2; per-class is a future tuning lever.
- Detecting in-progress attacks. Static scout-view screenshots only.

### 6.2 Out of scope project-wide (still applies)

Per `app/docs/prd.md` §9 — multiplayer, war, leagues, Builder Base, non-TH6 levels, Supercell-IP assets, mobile/networked play.

## 7. Further Notes

### 7.1 Side-effects on other documents

When v2 implementation begins, these documents need updates:

- `app/docs/technical.md` §7.1 — pipeline diagram updated to seven stages (add `grid` and `walls`); the wording "infer footprints from bbox size + class-specific footprint catalog" is replaced with "footprints are class-driven; bbox size is sanity-check only" (§4.6 of this PRD).
- `app/docs/prd.md` §5.3 — extended with AC-C4 through AC-C11 and the "Out of scope for v2" additions in §6.1 of this PRD.
- `app/sandbox_core/schemas.py` — `BaseLayout.schema_version` bumped to 2, `provenance: CartographerProvenance | None = None` added, identity migration `migrate_baselayout_v1_to_v2` registered. `CartographerProvenance` extended with `calibration_dataset_version: str | None = None` and `reviewed: bool = False`.
- `app/cartographer/README.md` — replaced with the v2-implemented README when the package ships.
- `app/sandbox_web/src/App.tsx` — gains a fourth `cartographer` tab.
- `app/cartographer/server.py` — new FastAPI module that hosts sandbox-web for calibrate and review modes (§4.7-bis).
- `app/data/cartographer_calibration.json` — new committed file written by the calibration tool (created on first calibration run, may be absent before then).

### 7.2 Phasing

v2 implementation does not begin until MVP-Real meets AC-B2. Until then `app/cartographer/` stays a stub. The `BaseLayout` schema bump to v2 may happen earlier as a pure-additive change if it simplifies sandbox-web work, but it is not a blocker for MVP-Real.

### 7.3 Risks specific to v2

- **R-C1.** The user-supplied screenshot distribution is too narrow to train a robust detector. *Mitigation:* the labelling-volume targets in §4.14 are a floor; if the model underperforms AC-C3, expand the dataset before pursuing other interventions.
- **R-C2.** Grass-grid derivation fails on screenshots with low grass coverage (dense bases with walls and buildings filling most of the area). *Mitigation:* the cross-validation check in §4.3 fails loudly when this happens; affected bases are authored manually. If this becomes common, a fallback that uses building-edge alignment to derive the grid is a v3 escalation.
- **R-C3.** Roboflow's hosted inference quota or pricing changes. *Mitigation:* the `detect` module isolates the inference call. Swapping to local inference is a contained change, planned as a non-blocking option.
- **R-C4.** Real-base distribution differs from synthetic-base distribution enough that the MVP-Real-trained agent generalises poorly even on cleanly-ingested bases. This is the actual research question v2 exists to answer — not a risk to mitigate but an outcome to measure.
