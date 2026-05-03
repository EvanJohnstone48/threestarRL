# threestarRL — Product Requirements Document

## 1. Vision

threestarRL is a research project that builds a Clash of Clans-style attack simulator, **The Sandbox**, and uses it as a reinforcement learning environment, **The Barracks**, to study whether an agent can learn base-attacking strategy through repeated simulated attacks. A computer-vision pipeline, **The Cartographer**, eventually allows the agent to attack bases captured from real screenshots.

The success goal is research insight, not a shippable game: *can an RL agent, given a faithful TH6 simulator, learn deployment timing, troop placement, pathing awareness, spell usage, and target prioritization well enough to consistently three-star?*

## 2. Research question

> Can a reinforcement learning agent learn useful attack strategy — including deployment timing, troop placement, pathing awareness, spell usage, and target prioritization — inside a custom base-attack simulator restricted to Town Hall 6 content?

## 3. Audience and stakeholders

- **Primary user:** the project owner (sole researcher and developer).
- **Secondary user:** future contributors who consume artifacts (replays, trained models, bases).
- **Audience for results:** the project owner; secondarily the broader RL/research community via writeups.

## 4. Milestone ladder

The project advances through three named milestones. Each is a distinct *result*, not a feature list.

### MVP-Tiny — "an agent learned something"
A trained agent on a single hand-built TH6 base, using a single troop type, that beats a random-deploy baseline by a clear margin on % destruction.

**Why this milestone:** proves the loop end-to-end. Sandbox produces valid simulations, the Barracks env wraps them correctly, SB3 trains a policy to convergence, and the replay pipeline visualizes what the agent learned. If MVP-Tiny succeeds, the rest of the project is a matter of scale.

### MVP-Real — "an agent three-stars curated TH6 bases"
A trained agent on a curated set of ~30 hand-built TH6 bases (plus mutations), using the full TH6 troop and spell roster, evaluated against a frozen 5-base held-out set.

**Why this milestone:** answers the research question for in-distribution synthetic bases. Demonstrates the agent learned generalizable strategy, not just memorized one base.

### v2 — "agent generalizes via Cartographer"
The Cartographer ingests real Clash base screenshots, emits `BaseLayout` JSON, and the MVP-Real-trained agent attacks those bases. Includes optional fine-tuning on real bases.

**Why this milestone:** proves the synthetic-to-real transfer. Out of scope for v1 — explicitly deferred.

## 5. Subsystem requirements

The project has three subsystems. Each has independent FRs but they share data contracts.

### 5.1 The Sandbox

**Purpose.** A deterministic, headless simulator of TH6 attacks. Owns all game state.

**v1 functional requirements.**

- FR-S1. The simulator advances a world state in fixed 100 ms ticks (10 Hz) with no randomness.
- FR-S2. The simulator supports the full TH6 entity roster: all defenses (Cannon, Archer Tower, Mortar, Air Defense, Wizard Tower), Town Hall, Clan Castle (building-only, no defending troops), Walls, all non-defense buildings (Army Camp, Barracks, Lab, Spell Factory, mines, collectors, storages, Builder's Huts), all six TH6 troops (Barbarian, Archer, Goblin, Giant, Wall Breaker, Wizard) with their target preferences and splash mechanics, and the Lightning Spell.
- FR-S3. Simulation is fully data-driven from JSON content files. No hardcoded entity stats.
- FR-S4. The simulator produces a replay artifact for every attack: an initial state, a per-tick stream of state snapshots, and a per-tick list of typed events (`deploy`, `attack_start`, `projectile_fired`, `damage`, `destroyed`, `spell_cast`).
- FR-S5. The simulator is exposed both as a Python library (importable from the Barracks RL env) and as a CLI (run an attack from `base.json` + `plan.json` → `replay.json`).
- FR-S6. The simulator computes a final score: stars (0–3), % destruction, ticks elapsed, and TH-destroyed flag.
- FR-S7. The Sandbox includes a web frontend (sandbox-web) that renders replays from JSON, supports timeline scrubbing and playback speed control, and supports manual base authoring exported to `BaseLayout` JSON.
- FR-S8. The simulator must produce bit-identical replays for the same `(base, plan)` input — replay determinism is testable via golden-replay regression tests.

**v1 acceptance criteria.**

- AC-S1. Running the CLI on the tracer base produces a `replay.json` that opens in sandbox-web and renders the full attack visually.
- AC-S2. The full TH6 roster is supported in `data/buildings.json`, `data/troops.json`, `data/spells.json` with stat values approximating the source game.
- AC-S3. Six golden-replay scenarios pass: vanilla movement, splash-damage Mortar, Wall Breaker pathing, Wizard splash, Lightning Spell, full-roster TH6 attack.
- AC-S4. Sandbox-web manual editor allows the user to author and export a TH6 base in under 10 minutes.
- AC-S5. Defense targeting respects target filters (e.g., Air Defense ignores ground troops; Goblin prioritizes resource buildings).

**Out of scope for v1.**

- Heroes (Barbarian King at TH7, Archer Queen at TH9).
- Air units and anti-air-only mechanics (Air Defense exists as an inert tower with HP).
- Filled Clan Castle with defending troops.
- TH7+ content (Healer, Hidden Tesla, additional spells).
- Stochastic mechanics or seeded RNG.
- Live in-browser interactive attacks (replay viewer only; manual attack mode runs in Python, not the browser).

### 5.2 The Barracks

**Purpose.** A reinforcement learning environment built on top of the Sandbox, where agents learn to attack bases.

**v1 functional requirements.**

- FR-B1. The Barracks exposes a Gymnasium-compliant environment whose `reset()` initializes a TH6 attack and whose `step()` advances the simulation to the next decision point.
- FR-B2. The action space is a flattened `Discrete(C_act * 44 * 44 + n_scalar)` where the first segment encodes spatial deploys/spells per tile and the trailing segment encodes wait/end actions. Invalid actions are masked via an action-mask tensor exposed as part of the observation.
- FR-B3. The observation space is a `Dict` of:
  - a `(C_obs, 44, 44)` spatial tensor with semantic channels (per-building-type masks, HP percent, destruction state, troop density, projectiles, spell areas, perimeter mask),
  - a scalar globals vector (time remaining, current stars, destruction percent, troops remaining per type, spells remaining),
  - the spatial and scalar action masks.
- FR-B4. The reward function is a layered shaped reward dominated by sparse star bonuses, with smooth Δ-destruction signal between thresholds, a TH-destroyed bonus, a per-building weight table, a small time penalty, and a small troop-loss penalty. All coefficients are loaded from `data/reward_weights.json`.
- FR-B5. The training pipeline uses Stable-Baselines3 with `MaskablePPO` from `sb3-contrib`, a custom CNN feature extractor over the spatial obs, and a 16-worker `SubprocVecEnv` for throughput.
- FR-B6. Training runs are launched from a single config JSON. Each run produces a self-contained directory at `app/experiments/runs/<run_id>/` containing config snapshot, checkpoints, eval results, and tensorboard logs.
- FR-B7. The training distribution scales by milestone:
  - MVP-Tiny: 1 hand-built base, 1 troop type.
  - MVP-Real: ~30 hand-built bases plus rotation/mirror/jitter mutations, with 5 hand-built bases held out as a frozen eval set.
- FR-B8. An eval callback runs every K training steps against the frozen eval set and reports mean stars, mean destruction, and three-star rate.
- FR-B9. Training and eval are reproducible: every run logs `(git_sha, seed, config_hash, library_versions)`.

**v1 acceptance criteria.**

- AC-B1. (MVP-Tiny) An agent trained on the tracer base achieves higher mean destruction than a random-deploy baseline by a margin of at least 30 percentage points across 100 eval episodes.
- AC-B2. (MVP-Real) An agent trained on the curated bank achieves a three-star rate of at least 50% on the training set and at least 30% on the held-out eval set.
- AC-B3. Training and eval each emit replay artifacts that load and visualize correctly in sandbox-web.
- AC-B4. The smoke-training test (1000 steps on the tracer base, in CI) completes without crashes or NaNs.

**Out of scope for v1.**

- Algorithms other than masked PPO.
- Multi-agent or self-play / adaptive defenders.
- Imitation learning warm-starts from human attacks.
- Hierarchical policies.
- Auxiliary losses or representation pretraining.
- Procedural base generation (deferred until overfit is observed on the held-out set during MVP-Real).

### 5.3 The Cartographer

**Purpose.** A computer vision pipeline that turns a screenshot of a Clash base into a structured `BaseLayout` JSON consumable by the Sandbox and Barracks. Deferred to v2.

**v1 functional requirements (architecture only — no implementation).**

- FR-C1. Cartographer produces `BaseLayout` JSON conforming to the same schema as hand-built and procedurally-generated bases. The `BaseLayout` schema is frozen at v1 with a `schema_version` field; Cartographer must conform or migrate.
- FR-C2. The package directory `app/cartographer/` exists in v1 as a stub with `__init__.py` and a placeholder `README.md` noting deferral to v2.
- FR-C3. The architectural pipeline is committed to in this PRD: screenshot → Roboflow object detection (bounding boxes + class labels) → perspective/grid alignment → footprint reconstruction → `BaseLayout` JSON validation → emit.

**v2 functional requirements (specified for design clarity, not v1 work).**

- FR-C4. (v2) A Roboflow-trained object-detection model produces per-building bounding boxes with class labels. Model training happens off-codebase in Roboflow's UI.
- FR-C5. (v2) The pipeline maps detected bounding boxes to grid-aligned tile origins and footprints, handling isometric perspective.
- FR-C6. (v2) The pipeline validates emitted `BaseLayout` JSON against the Pydantic schema and fails loudly on uncertain or invalid detections.
- FR-C7. (v2) A CLI entry point: `python -m cartographer ingest path/to/screenshot.png --out app/data/scraped_bases/<id>.json`.
- FR-C8. (v2) Configuration includes Roboflow project name, dataset version, and inference endpoint, pinned in `app/data/cartographer_config.json`. The Roboflow API key is loaded from the `ROBOFLOW_API_KEY` environment variable.

**v2 acceptance criteria.**

- AC-C1. (v2) On a sample of 20 real TH6 base screenshots, Cartographer emits valid `BaseLayout` JSONs that, when loaded into the Sandbox, render without errors.
- AC-C2. (v2) An agent trained under MVP-Real successfully attacks at least 50% of Cartographer-ingested bases without crashing the env.
- AC-C3. (v2) Detection accuracy against a hand-labeled gold set of 10 screenshots exceeds 90% F1 on building class and 95% IoU on bounding box.

**Out of scope for v1.**

- Any Cartographer code beyond the package stub.

**Out of scope for v2.**

- Real-time screenshot capture from a phone or emulator.
- Detecting in-progress attacks (only static base layouts).
- Detecting troop levels, hero levels, or any non-layout metadata.

## 6. Cross-cutting requirements

### 6.1 Determinism and reproducibility

- The Sandbox is deterministic with no RNG in v1. The same `(base.json, plan.json)` always produces a bit-identical `replay.json`.
- All persisted JSON files include a `schema_version` field for forward compatibility.
- Every training run is reproducible from `(config.json, git_sha, seed)` alone.

### 6.2 File-based interchange

- All inter-subsystem communication is via JSON files validated by Pydantic v2 models. No live IPC, no sockets, no shared memory.
- Replays, base layouts, deployment plans, training configs, and content data are all on-disk artifacts.
- The web frontend reads JSON files via static-server or drag-drop; it never drives simulation live.

### 6.3 Single source of truth

- Schemas defined once in `sandbox_core/schemas.py` as Pydantic models.
- TypeScript types for the web frontend are auto-generated from those schemas.
- Content stats live exclusively in `app/data/*.json` files.

## 7. Dependencies between subsystems

```
                                       Sandbox-core
                                       /          \
                                      /            \
                              Sandbox-web        Barracks
                                                    |
                                                    |
                                              (consumes BaseLayout)
                                                    |
                                                    |
                                                Cartographer (v2)
                                                  produces BaseLayout
```

- Sandbox-core has zero dependencies on the other subsystems.
- Sandbox-web depends on Sandbox-core only via JSON artifacts (loose coupling).
- Barracks depends on Sandbox-core as a Python import.
- Cartographer (v2) depends on neither — it produces `BaseLayout` JSONs that any consumer accepts.

## 8. Risks

- **R-1.** RL agent fails to learn even MVP-Tiny. *Mitigation:* tracer-bullet philosophy means we discover this in weeks, not months. Reward shaping is a tunable JSON. Action masking removes a major source of exploration noise.
- **R-2.** Determinism is broken silently by a careless commit. *Mitigation:* golden-replay tests in CI catch any sim-output change.
- **R-3.** Sandbox content authoring (full TH6 roster) takes longer than estimated. *Mitigation:* data-driven core means content is JSON edits, not code. MVP-Tiny does not depend on full content.
- **R-4.** Overfitting on hand-built bases blocks MVP-Real. *Mitigation:* mutations expand effective distribution; procedural generator is the planned escalation if needed.
- **R-5.** Web-frontend rendering quality is poor enough to block debugging the sim. *Mitigation:* placeholder geometry is sufficient for v1 — the goal is correctness inspection, not aesthetics.
- **R-6.** SB3 hits a customization wall mid-MVP-Real. *Mitigation:* env, policy network, reward, and obs/action are all library-agnostic. Migration to CleanRL is approximately two days of trainer-glue work.

## 9. Out of scope (project-wide)

- Multiplayer or matchmaking.
- War mechanics, leagues, trophies.
- Builder Base.
- Any TH level other than TH6 in v1.
- Any Supercell-IP assets or sprites — all visuals come from user-supplied local folders or placeholder geometry.
- Mobile app, iOS or Android.
- Realtime or networked play.
