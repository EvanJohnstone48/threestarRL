# threestarRL — Technical Design

This document defines the technical architecture, tech stack, repo layout, data contracts, and cross-cutting infrastructure for threestarRL. It complements `prd.md` (what gets built and why) and `roadmap.md` (in what order). Subsystem-deep technical details live in per-subsystem design docs (e.g., `app/docs/barracks/design.md`).

## 1. Tech stack at a glance

| Layer | Choice |
|---|---|
| Sandbox core | Python 3.12 (single language across sandbox-core, barracks, cartographer) |
| Web frontend | TypeScript + React + PixiJS, built with Vite |
| Package manager (Python) | `uv` with `uv.lock` |
| Lint/format (Python) | `ruff` (linter + formatter) |
| Type checker (Python) | `pyright` |
| Test runner (Python) | `pytest`, with `hypothesis` for property tests |
| Lint/format (web) | `eslint` + `prettier` |
| RL library | Stable-Baselines3 + `sb3-contrib` `MaskablePPO` |
| Tensor lib | PyTorch (provided by SB3) |
| RL env interface | Gymnasium |
| Schemas / config | Pydantic v2 |
| Experiment tracking | TensorBoard locally; W&B optional via SB3 callback |
| CV pipeline (v2) | Roboflow (off-codebase model training, on-codebase inference) |
| Pre-commit | `pre-commit` framework |
| CI | GitHub Actions, Linux runners |

## 2. Repo layout

```
threestarRL/
├── .claude/                              # Claude Code config and skills
├── app/
│   ├── docs/                             # All project documentation
│   │   ├── idea.md                        # Original project pitch
│   │   ├── agents/
│   │   │   ├── agent.md                   # Agent operating process
│   │   │   └── sessions/                  # Per-grilling-session notes
│   │   ├── prd.md                         # Full project PRD
│   │   ├── technical.md                   # This file
│   │   ├── roadmap.md                     # Phased roadmap
│   │   ├── ubiquitous-language.md         # Glossary
│   │   ├── sandbox/
│   │   │   ├── prd.md                     # (later) per-subsystem PRD
│   │   │   └── design.md                  # (later) per-subsystem design
│   │   ├── barracks/
│   │   │   ├── design.md                  # RL design doc (obs/action/reward/training)
│   │   │   └── prd.md                     # (later)
│   │   └── cartographer/
│   │       └── prd.md                     # (later)
│   ├── sandbox_core/                     # Pure simulator (Python package)
│   │   ├── __init__.py
│   │   ├── schemas.py                     # Pydantic models for all data contracts
│   │   ├── content.py                     # Loads + validates buildings/troops/spells JSON
│   │   ├── grid.py                        # Grid + footprint + tile-occupancy logic
│   │   ├── building.py
│   │   ├── troop.py
│   │   ├── projectile.py
│   │   ├── spell.py
│   │   ├── pathfinding.py
│   │   ├── combat.py                      # Damage application, target selection
│   │   ├── scoring.py                     # Stars, % destruction
│   │   ├── sim.py                         # The Sim class — owns world state, step_tick(), advance_to()
│   │   ├── replay.py                      # Replay writer + reader
│   │   └── cli.py                         # CLI for running attacks from JSON
│   ├── sandbox_web/                      # Web frontend (Node project)
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   ├── tsconfig.json
│   │   ├── public/sprites/                # User-supplied sprite assets (gitignored)
│   │   └── src/
│   │       ├── main.tsx
│   │       ├── App.tsx
│   │       ├── viewer/                    # Replay viewer (Pixi-driven)
│   │       ├── editor/                    # Manual base editor
│   │       ├── components/                # React UI panels
│   │       └── generated_types.ts         # Auto-generated from Pydantic schemas
│   ├── barracks/                         # RL env + training (Python package)
│   │   ├── __init__.py
│   │   ├── env.py                         # Gymnasium env wrapping sandbox_core
│   │   ├── obs.py                         # Observation builder
│   │   ├── action.py                      # Action decoder + mask builder
│   │   ├── reward.py                      # Layered reward calculator
│   │   ├── policy.py                      # Custom CNN feature extractor for SB3
│   │   ├── train.py                       # SB3 MaskablePPO entry point
│   │   ├── eval.py                        # Eval callback against held-out bases
│   │   ├── curriculum.py                  # Base-set scheduling across training rounds
│   │   └── baselines.py                   # Random-deploy baseline for MVP-Tiny
│   ├── cartographer/                     # v2 — package stub in v1
│   │   ├── __init__.py
│   │   └── README.md                      # "Deferred to v2"
│   ├── data/                             # Game content + bases + reward weights
│   │   ├── buildings.json                 # All TH6 building stats
│   │   ├── troops.json                    # All TH6 troop stats
│   │   ├── spells.json                    # Lightning Spell stats
│   │   ├── th6_rules.json                 # Caps: max walls, max cannons, troop capacity, etc.
│   │   ├── reward_weights.json            # Tunable reward coefficients
│   │   ├── sample_bases/
│   │   │   ├── tracer.json                # MVP-Tiny base
│   │   │   ├── base_01.json … base_30.json   # MVP-Real training set
│   │   │   └── eval_01.json … eval_05.json   # Frozen held-out eval set
│   │   ├── mutations.py                   # Base-mutation pipeline
│   │   ├── cartographer_config.json       # (v2) Roboflow project + dataset pin
│   │   └── scraped_bases/                 # (v2) Cartographer outputs
│   └── experiments/
│       └── runs/<run_id>/                 # Self-contained per-run directory (gitignored)
│           ├── config.json
│           ├── checkpoints/
│           ├── eval_results/
│           ├── replays/
│           └── tensorboard/
├── tests/
│   ├── unit/
│   │   ├── sandbox_core/
│   │   ├── barracks/
│   │   └── cartographer/
│   ├── integration/
│   │   ├── test_full_episode.py
│   │   └── test_replay_roundtrip.py
│   └── golden/
│       └── replays/                       # Frozen replay fixtures
├── ralph/
│   ├── afk.sh                             # Multi-iteration ralph loop
│   ├── once.sh                            # Single-iteration ralph
│   └── prompt.md                          # Issue execution loop prompt
├── issues/
│   ├── open/                              # Active issues (ralph reads via cat issues/open/*.md)
│   └── done/                              # Completed issues (ralph moves them here)
├── .github/
│   └── workflows/
│       └── ci.yml                         # Lint + typecheck + test
├── pyproject.toml                         # Single Python package config
├── uv.lock
├── ruff.toml
├── pyrightconfig.json
├── .pre-commit-config.yaml
├── .gitignore
└── README.md
```

### 2.1 Why a single Python package, not multi-package

Solo developer; a research project where rapid cross-subsystem refactors are common. The boundary discipline of multi-package would cost more than it gives. If a subsystem ever needs to be published standalone (e.g., releasing `sandbox_core` as a public CoC RL benchmark), the split is mechanical at that point.

### 2.2 Why `app/sandbox_core/` (underscore) and `app/sandbox_web/` (underscore)

Python package names cannot contain hyphens. The web project was renamed from `sandbox-web` (idea.md draft) to `sandbox_web` for filesystem consistency. Inside the web project, conventional JS naming applies (`kebab-case` for files where appropriate).

## 3. Determinism, time, and the simulation tick

- **Tick rate.** Fixed at 10 Hz. One tick = 100 ms of simulated time. All speeds, cooldowns, projectile travel, and spell durations are expressed in tick units.
- **No RNG.** v1 simulation has no random calls. Tie-breaks (e.g., target selection between two equidistant buildings) resolve by canonical ordering: lowest building id, then lowest `(row, col)`. A `seed` field is reserved in `Replay` JSON for forward compatibility but is unused in v1.
- **Continuous troop position on a discrete grid.** Buildings occupy integer-tile footprints. Troops have float `(row, col)` positions. Pathfinding operates on the discrete grid; movement advances the troop along the cached path by `speed_tiles_per_tick` per tick.
- **Per-tick update order** (fixed for determinism):
  1. Resolve in-flight projectiles → hit events.
  2. Apply scheduled deployments queued for this tick.
  3. Update troop targeting (re-pick on dead/destroyed target).
  4. Advance troop positions one substep along their cached path.
  5. Troops attack in range with cooldown ready.
  6. Update defense targeting.
  7. Defenses attack in range with cooldown ready.
  8. Apply accumulated damage events; mark destroyed; emit `destroyed` events.
  9. Update score (stars, % destruction).
  10. Increment `tick`.

## 4. Data contracts (Pydantic v2)

All inter-subsystem and inter-process communication uses JSON files validated by Pydantic v2 models defined in `app/sandbox_core/schemas.py`. TypeScript types for the web frontend are auto-generated from these schemas.

### 4.1 Static content schemas

`BuildingType`, `TroopType`, `SpellType` — define stats for each entity, loaded once at sim startup from `app/data/*.json` and exposed as immutable singletons via `sandbox_core.content`.

### 4.2 Per-base / per-attack schemas

- `BaseLayout` — a frozen base description: `(grid_size, th_level, placements, cc_contents, schema_version)`. Universal contract across hand-built, mutated, procedurally-generated, and Cartographer-emitted bases.
- `BuildingPlacement` — origin tile + building type reference.
- `DeploymentPlan` — an ordered list of `DeploymentAction`s (each with `tick`, `kind`, `entity_type`, `position`). Used by the CLI for canned attacks; not used by the RL env (the agent's actions are converted to deployments at step time).
- `Replay` — initial state + per-tick frames + final score. The single artifact every attack produces.
- `WorldState` — the complete state at one moment (buildings, troops, projectiles, spells, score). Used inside `TickFrame`.
- `Event` — typed event for animation triggers (`deploy`, `attack_start`, `projectile_fired`, `damage`, `destroyed`, `spell_cast`).

### 4.3 Training schemas

- `TrainingConfig` — top-level config for one training run: env config, policy config, reward weights, schedule, eval, seed.
- `RewardWeights` — coefficients for the layered reward (loaded from `app/data/reward_weights.json` and overridable per run).
- `EnvConfig`, `PolicyConfig`, `ScheduleConfig`, `EvalConfig` — per-component config blocks.

### 4.4 Schema versioning

Every persisted JSON has a `schema_version: int = 1` field. Migrations are functions in `schemas.py` named `migrate_baselayout_v1_to_v2(old: dict) -> dict`. The reader applies migrations transparently when loading. v1 is the frozen contract at project start.

### 4.5 Replay format (the core↔frontend contract)

Hybrid format: `Replay` contains the initial `WorldState`, then a list of `TickFrame`s. Each `TickFrame` contains the *full* `WorldState` at that tick plus an `events` list (Phase 1 simplicity). Phase 2 may switch to per-tick deltas if file size or RAM pressure justifies it; the schema accommodates this via an optional `state_delta` field added later.

For TH6, full-state-per-tick is approximately 1–3 MB per attack at 10 Hz over 3 minutes (1800 ticks). Acceptable both on disk and in browser memory.

## 5. The Sandbox

### 5.1 Sandbox-core architecture

The `Sim` class owns all world state. Public API:

```python
class Sim:
    def __init__(self, base: BaseLayout): ...
    def reset(self) -> WorldState: ...
    def step_tick(self) -> tuple[WorldState, list[Event]]: ...
    def advance_to(self, target_tick: int) -> list[TickFrame]: ...
    def schedule_deployment(self, action: DeploymentAction) -> None: ...
    def is_terminal(self) -> bool: ...
    def score(self) -> Score: ...
    def to_replay(self) -> Replay: ...
```

The `step_tick()` call follows the fixed update order in §3. Subsystems (`pathfinding`, `combat`, `scoring`) are pure-functional helpers that take and return state slices, not stateful objects — this keeps the sim trivially testable.

### 5.2 Pathfinding strategy

Each troop caches an A* path to its current target (computed in tile space, ignoring float positions). Movement substep advances the troop along the path by `speed_tiles_per_tick`. Path is invalidated and recomputed on:

- target destruction (re-pick target, recompute),
- wall destruction along the path (recompute on the new openings),
- spawn (initial path computation).

A* uses Manhattan heuristic with diagonals allowed at √2 cost. Wall tiles are blocked unless the troop is a Wall Breaker, in which case walls are allowed waypoints with extra-high cost (the WB attacks the wall when adjacent). Performance is fine at 44×44 because path recomputation is rare relative to ticks (most ticks reuse cached paths).

### 5.3 CLI

```
uv run python -m sandbox_core.cli run \
    --base app/data/sample_bases/tracer.json \
    --plan path/to/plan.json \
    --out path/to/replay.json
```

Used for golden-replay tests and for any human-canned attack the user wants to inspect in sandbox-web.

### 5.4 Sandbox-web architecture

- Vite + React + TypeScript app at `app/sandbox_web/`.
- PixiJS handles the isometric tile renderer, sprite atlas loading, troop/projectile animations, tweening between tick snapshots.
- React handles the app shell, base picker, replay timeline scrubber, entity inspector, editor toolbox.
- Replays loaded from disk via static-server or drag-drop file upload. No live connection to a Python process.
- Manual editor exports authored bases as `BaseLayout` JSON files; the user manually copies them into `app/data/sample_bases/`.
- v1 ships with placeholder geometry (colored shapes by entity type). User-supplied sprite atlases at `public/sprites/` are picked up automatically when present.

## 6. The Barracks (RL env + training)

Per the user's preference, RL specifics live in `app/docs/barracks/design.md`. Brief architectural summary here:

- **Env.** A Gymnasium-compliant env at `barracks/env.py`. `reset()` chooses a base from the active training distribution, instantiates a `Sim`, returns the initial obs. `step()` applies the agent's action (deploy / spell / wait / end), runs the sim forward to the next decision point, returns `(obs, reward, terminated, truncated, info)`.
- **Action space.** Single flattened `Discrete(C_act * 44 * 44 + n_scalar)`. Action masking via `MaskablePPO`.
- **Observation space.** `Dict` of spatial (`(C_obs, 44, 44)`), scalar globals, spatial mask, scalar mask.
- **Reward.** Layered shaped reward; coefficients loaded from `data/reward_weights.json`.
- **Library.** SB3 + `sb3-contrib`'s `MaskablePPO`. 16-worker `SubprocVecEnv` for throughput. Custom CNN feature extractor for the spatial obs.
- **Training entry point.** `python -m barracks.train --config app/experiments/configs/<config>.json`.
- **Run directory.** Each run gets `app/experiments/runs/<run_id>/` containing config snapshot, checkpoints, eval results, replays, tensorboard logs.
- **Reproducibility.** Each run logs `(git_sha, seed, config_hash, library_versions)` at start.

## 7. The Cartographer (v2 architecture)

In v1 the Cartographer is a package stub. The pipeline architecture is committed to here so v1 doesn't accidentally make assumptions that block v2.

### 7.1 Pipeline stages (Roboflow-based)

```
screenshot.png
  │
  ▼
┌──────────────────────────────────────┐
│ Stage 1 — Image preprocessing         │   cartographer/preprocess.py
│  - crop to play area                  │
│  - normalize lighting / colors        │
│  - (optional) perspective-correct     │
│    isometric tilt to top-down 44×44   │
└──────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────┐
│ Stage 2 — Roboflow object detection   │   cartographer/detect.py
│  - call Roboflow Inference SDK        │
│  - get bounding boxes + class labels  │
│    + confidence scores                │
│  - input: preprocessed image          │
│  - output: list[Detection]            │
└──────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────┐
│ Stage 3 — Bbox-to-grid alignment      │   cartographer/align.py
│  - map bbox centers to tile coords    │
│  - infer footprints from bbox size    │
│    + class-specific footprint catalog │
│  - resolve overlaps                   │
└──────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────┐
│ Stage 4 — Schema emission             │   cartographer/emit.py
│  - construct BaseLayout pydantic obj  │
│  - validate against schema            │
│  - fail loudly on uncertain detects   │
│  - write JSON                         │
└──────────────────────────────────────┘
  │
  ▼
BaseLayout JSON  (same schema as hand-built bases)
```

### 7.2 Roboflow integration

- Model training happens off-codebase in Roboflow's UI. The repo does not contain training code or labeled data — only inference glue.
- Model is loaded via Roboflow Inference SDK; either hosted endpoint (HTTPS API call per ingest) or local inference using downloaded weights. Choice deferred to v2.
- Configuration in `app/data/cartographer_config.json`: `{ project_name, dataset_version, inference_endpoint, confidence_threshold, ... }`.
- API key in `ROBOFLOW_API_KEY` environment variable, never committed.

### 7.3 CLI (v2)

```
uv run python -m cartographer ingest \
    --in path/to/screenshot.png \
    --out app/data/scraped_bases/scrape_001.json
```

### 7.4 v1 commitments

- `app/cartographer/__init__.py` exists.
- `app/cartographer/README.md` documents v2 deferral and references this section.
- `BaseLayout` schema is *frozen* at v1. Any v2 Cartographer needs are met by extending the schema with additive optional fields under a new `schema_version`, never by introducing a separate Cartographer-specific layout type.

## 8. Configuration management

- **No Hydra** in v1. Single config JSON per training run, validated by Pydantic.
- **Config locations:**
  - Run-time training configs: `app/experiments/configs/*.json` (e.g., `mvp_tiny.json`, `mvp_real.json`).
  - Reward weights: `app/data/reward_weights.json`. Per-run overrides specified inline in the training config.
  - Game content: `app/data/{buildings,troops,spells,th6_rules}.json`.
- **CLI overrides** via simple `--key.subkey=value` parsing. Each override is applied to the loaded config dict before re-validation.
- **Config snapshot.** When a training run starts, the resolved config (after overrides) is written to `app/experiments/runs/<run_id>/config.json`. Reproducing the run = `python -m barracks.train --config <run_dir>/config.json`.

## 9. Test strategy

The full pyramid plus golden-replay regression tests as the architectural keystone.

### 9.1 Unit tests (`tests/unit/`)

Pure-function tests for grid/footprint helpers, target-selection logic, damage-application math, action-mask construction, observation-tensor construction, reward computation. Each runs in milliseconds. Fast, run on every commit via pre-commit.

### 9.2 Property tests (`tests/unit/sandbox_core/test_invariants.py`)

`hypothesis`-driven invariants:

- After any sequence of valid `step_tick()` calls, total destruction percent is monotonically non-decreasing.
- No troop ever occupies a non-buildable tile.
- No two buildings overlap in their footprint placements.
- The `Sim`'s reported score is consistent with a from-scratch recompute over the current `WorldState`.

### 9.3 Golden replay tests (`tests/golden/replays/`)

The architectural keystone. For each canonical scenario (vanilla movement+attack, splash-damage Mortar, Wall Breaker pathing, Wizard splash, Lightning Spell, full-roster TH6 attack), a frozen `(base.json, plan.json) → expected_replay.json` fixture is committed.

- Test runs the sim and asserts the produced replay equals the golden one (with float tolerance for positional fields).
- Any unintended sim-output change breaks the test.
- Intentional changes regenerate via `pytest --update-golden`; the diff is part of the PR.

### 9.4 Integration tests (`tests/integration/`)

- Full-episode tests through the Barracks env: `env.reset() → loop env.step() → terminated`. Asserts final score, replay validity, no exceptions.
- Replay roundtrip test: write a replay, read it back via Pydantic, assert equality.

### 9.5 Smoke training test

A short SB3 run (~1000 steps, 1 vec worker, no GPU) on the tracer base. Asserts no crashes, no NaN losses. Catches integration breaks between env and SB3 in CI.

### 9.6 Test markers

- `@pytest.mark.slow` for golden replays, integration tests, and smoke training. Skipped by default in pre-commit.
- Pre-commit runs `pytest -m "not slow"` (target: under 10 seconds).
- CI runs the full suite.

## 10. CI / dev infrastructure

### 10.1 Pre-commit hooks (`.pre-commit-config.yaml`)

Run on every commit:

- `ruff check` (lint)
- `ruff format --check`
- `pyright` (type check)
- `pytest -m "not slow"` (fast unit tests)

### 10.2 GitHub Actions (`.github/workflows/ci.yml`)

Parallel jobs on push and PR, Linux runners only:

- **lint** — `uv run ruff check .` + `uv run ruff format --check .`
- **typecheck** — `uv run pyright`
- **test** — `uv run pytest` (full suite including golden replays, integration, smoke training)
- **web** — `cd app/sandbox_web && pnpm install && pnpm lint && pnpm typecheck && pnpm build`

No GPU jobs in CI. No real training runs in CI beyond the smoke test.

### 10.3 OS portability

The project is developed on Windows. CI runs on Linux. Path handling uses `pathlib.Path` exclusively. No raw string-concatenated paths anywhere in Python code.

## 11. Observability

- **TensorBoard** logs per run at `app/experiments/runs/<run_id>/tensorboard/`. Standard for SB3.
- **W&B** integration is optional via SB3's `WandbCallback`, gated by `WANDB_API_KEY` env var. Off by default.
- **Eval metrics** logged to `app/experiments/runs/<run_id>/eval_results/` as JSON (timestamps + metrics) for cross-run comparison.

## 12. Reproducibility

For every training run we record:

- `git_sha` (current commit)
- `git_dirty` (boolean — uncommitted changes flag, also fail if true unless `--allow-dirty`)
- `seed` (training RNG seed; sim is deterministic regardless)
- `config_hash` (sha256 of the resolved config JSON)
- `library_versions` (SB3, PyTorch, Gymnasium, etc.)
- `python_version`
- `platform`
- `start_timestamp_utc`

All written to `app/experiments/runs/<run_id>/run_metadata.json` at start.

## 13. Cross-cutting conventions

- **No hardcoded entity stats anywhere in code.** All stats live in `app/data/*.json`.
- **No `if entity.type == "wizard":` branches.** Special behaviors expressed as data fields (`target_filter`, `splash_radius`, `target_preference`, `is_wall`).
- **No naked `json.load()`.** Every JSON read goes through a Pydantic model.
- **No live IPC across subsystems.** All communication via on-disk JSON.
- **No magic file paths.** All paths configurable via `EnvConfig` or CLI flags; defaults relative to repo root.
- **Type hints everywhere in Python.** Pyright strict mode in CI.

## 14. Performance targets

- Sandbox-core: ≥100 episodes/sec on a single CPU core in pure Python for an MVP-Tiny-style attack. ≥50 episodes/sec for full TH6 attacks. (No optimization beyond clean NumPy usage in v1; profile-driven optimization only if bottlenecks block training.)
- Vec env throughput: 16 workers × 50 ep/sec ≈ 800 ep/sec aggregate. Sufficient for MVP-Real to converge in 1–3 days per run on a 16-core + RTX 3060+ workstation.
- Web frontend: 60fps replay playback on commodity hardware.
- Training memory: SB3 PPO with `n_steps=2048`, 16 envs, 30-channel obs at 44×44 = roughly 4 GB GPU; well within consumer-GPU budget.

## 15. Open technical decisions deferred to subsystem grilling

The following were intentionally not resolved in the architecture grilling and will be decided in subsystem-specific grilling sessions:

- **Sandbox** — exact balance numbers for each entity, exact splash-damage falloff curve, exact Wall Breaker AI rules, manual-editor UX details.
- **Barracks** — PPO hyperparameter starting values, exact eval cadence, curriculum-promotion thresholds, augmentation/mutation strategy tuning, custom feature extractor depth/width.
- **Cartographer** — Roboflow class taxonomy, perspective correction technique (homography-based vs ML-based), confidence threshold tuning, hosted vs local inference.
