# threestarRL — Roadmap

This roadmap organizes the project into phases tied to the milestone ladder in `prd.md`. Each phase has a goal, exit criteria, and a list of high-level issue clusters that the agentic ralph loop expands into individual issues. The roadmap is structured around the three subsystems: **The Sandbox**, **The Cartographer**, **The Barracks**.

## Phasing summary

| Phase | Name | Headline result | Subsystems active |
|---|---|---|---|
| 0 | Foundation | Tracer bullet: deploy one troop, watch it walk and attack, see it on the screen | Sandbox-core (skeleton), Sandbox-web (skeleton) |
| 1 | Sandbox content + MVP-Tiny RL | "PPO agent beats random baseline on the tracer base" | Sandbox-core (full TH6), Sandbox-web (viewer + editor), Barracks (env + first PPO) |
| 2 | MVP-Real | "PPO agent three-stars 50% of curated TH6 bases" | All three of the above, full integration |
| 3 | Cartographer + generalization | "Agent attacks scraped real bases" | Cartographer (Roboflow pipeline), Barracks (transfer eval) |
| 4 | Continuation — beyond TH6 | "Agent operates across higher town halls with full troop and hero rosters" | All subsystems, scope-expanded to TH7+ content |

Phases overlap in practice. Phase 1 sandbox-content authoring runs in parallel with Phase 1 RL work because the simulator is data-driven (FR-S3). The roadmap below describes the ideal completion order; ralph-driven issues land in the order that unblocks the most downstream work.

---

## Phase 0 — Foundation (tracer bullet)

**Goal.** Prove the end-to-end path from input to output works. Deploy one troop on a tiny base, simulate the attack, write a replay, render it in the browser. Roughly 1–2 weeks.

**Why this phase exists.** Per `agent.md`'s tracer-bullet philosophy, the architecture must be touched end-to-end before any subsystem is fleshed out. This phase de-risks every architectural decision from the grilling sessions.

### 0.1 Sandbox-core skeleton

- Set up Python package, `pyproject.toml`, `uv.lock`, `ruff.toml`, `pyrightconfig.json`.
- Define Pydantic schemas in `sandbox_core/schemas.py`: `BuildingType`, `TroopType`, `BuildingPlacement`, `BaseLayout`, `DeploymentAction`, `DeploymentPlan`, `Replay`, `TickFrame`, `WorldState`, `Event`, `Score`. Frozen at `schema_version: 1`.
- Implement `Grid` with footprint occupancy bookkeeping.
- Implement `Sim` with bare `step_tick()`: scheduled deployments + troop spawn + linear movement toward target tile, no targeting AI yet.
- Implement minimal `combat.py`: troop attacks adjacent building, building loses HP, building destroyed when HP ≤ 0.
- Implement `replay.py` writer: Sim emits `Replay` JSON with full per-tick state.
- Implement `cli.py`: `python -m sandbox_core.cli run --base ... --plan ... --out ...`.
- Author `app/data/buildings.json` and `app/data/troops.json` with just two entries each: TH, Cannon, Barbarian, Giant. Stats can be approximate.
- Author `app/data/sample_bases/tracer.json`: TH at center, one Cannon, four wall segments, the rest empty.

### 0.2 Sandbox-web skeleton

- Set up Vite + React + TypeScript project at `app/sandbox_web/`.
- Implement minimal Pixi-based renderer: load a `Replay` JSON, draw the grid, draw buildings as colored squares with HP bars, draw troops as colored circles, animate troop positions by interpolating between tick snapshots.
- Implement minimal timeline scrubber + play/pause.
- Wire up TypeScript schema generation from Pydantic models (`make types` script).

### 0.3 Pre-commit + CI scaffolding

- `.pre-commit-config.yaml` with ruff, ruff-format, pyright, pytest fast.
- `.github/workflows/ci.yml` with lint, typecheck, test jobs.
- Smoke test: load tracer base, deploy one Barbarian, run sim to completion, assert no exceptions.

### 0.4 Documentation

- Per-subsystem PRD stubs under `app/docs/{sandbox,barracks,cartographer}/prd.md` (placeholders, filled out in the future grilling sessions for each subsystem).
- `app/docs/ubiquitous-language.md` glossary of project terms.

### Exit criteria for Phase 0

- A user can run `uv run python -m sandbox_core.cli run --base tracer.json --plan single_barb.json --out out.json` and the resulting `out.json` validates against the `Replay` schema.
- The user can drag `out.json` into the browser and watch the Barbarian walk to the Cannon and destroy the TH.
- CI passes on lint, typecheck, and tests.
- One golden-replay fixture committed (the tracer scenario).

---

## Phase 1 — Sandbox content + MVP-Tiny RL

**Goal.** Two parallel workstreams.
- **Sandbox content.** Land the full TH6 entity roster in the data-driven core: all defenses with splash, all six troops with target preferences, Lightning Spell, all non-defense buildings.
- **MVP-Tiny RL.** Stand up the Barracks env, train the first PPO agent on the tracer base with a single troop type, beat the random-deploy baseline.

Roughly 6–10 weeks.

### 1.1 Sandbox content (parallel track)

#### 1.1.1 Defenses + splash damage
- Add Cannon, Archer Tower, Mortar (with splash radius), Air Defense, Wizard Tower (with splash) to `buildings.json`.
- Implement defense targeting: range check, `target_filter` (any/ground/air/resources), pick by canonical tie-break (lowest id, lowest distance).
- Implement projectile travel for ranged defenses with `projectile_arc_ticks > 0`.
- Implement splash damage: damage falls on all entities within `splash_radius` of impact point.
- Golden-replay: Mortar splash hits multiple troops.

#### 1.1.2 Troops with targeting preferences
- Add Archer (ranged ground), Goblin (resource preference), Wall Breaker (wall preference, suicide damage), Wizard (ranged splash) to `troops.json`.
- Implement `target_preference`: troops first scan for preferred building class, fall back to nearest valid target.
- Implement Wall Breaker AI: pathfinder allows walls as high-cost waypoints; on adjacency, WB self-destructs and deals splash damage to nearby walls.
- Golden-replay: Wall Breaker breaches a wall, Goblin runs to a Storage past unguarded buildings.

#### 1.1.3 Lightning Spell
- Add Lightning to `spells.json`: radius, damage_per_hit, hits, hit_interval_ticks.
- Implement spell scheduling, spell active state, per-hit damage application.
- Golden-replay: Lightning destroys a low-HP Mortar.

#### 1.1.4 Non-defense buildings
- Add CC (building only), Army Camp, Barracks, Lab, Spell Factory, Mines, Collectors, Storages, Builder's Huts to `buildings.json`.
- These have HP and contribute to % destruction; no defensive behavior.
- Author `th6_rules.json`: caps for each building type, total housing space, spell capacity.

#### 1.1.5 Hand-author MVP-Real training set
- Author `app/data/sample_bases/base_01.json` … `base_30.json` using the manual editor.
- Author `app/data/sample_bases/eval_01.json` … `eval_05.json` (frozen eval set).
- Categorize each base by hand into easy/medium/hard for curriculum.

#### 1.1.6 Sandbox-web manual editor
- React UI for placing buildings: building palette, drag-and-drop on grid, footprint preview, validation against TH6 rules.
- Wall-paint mode (drag to paint segments).
- Export authored base as `BaseLayout` JSON (download as file).

### 1.2 MVP-Tiny RL track (parallel)

#### 1.2.1 Barracks env scaffolding
- Implement `barracks/env.py` Gymnasium env wrapping `Sim`.
- Implement `obs.py`: build the spatial + scalar obs from `WorldState` (initial channels, rest added incrementally).
- Implement `action.py`: decode flattened action index to `DeploymentAction` or wait/end; build action mask from current state.
- Implement `reward.py`: per-step layered reward; coefficients from `data/reward_weights.json`.
- Verify Gymnasium API conformance with `gymnasium.utils.env_checker`.

#### 1.2.2 Random baseline
- `barracks/baselines.py`: random-deploy policy that uniformly samples valid masked actions.
- Run 100 episodes on tracer base; record mean stars + mean destruction. This is the bar to beat.

#### 1.2.3 First PPO training
- `barracks/policy.py`: `ThreestarFeatureExtractor` (CNN + scalar MLP + fuse).
- `barracks/train.py`: SB3 `MaskablePPO` setup, 16-worker `SubprocVecEnv`, tensorboard logging, checkpointing, eval callback.
- Training config `app/experiments/configs/mvp_tiny.json`: tracer base only, single troop type (Barbarian), 1M timesteps target.
- Run training; check learning curves; iterate on reward coefficients in dedicated tuning sessions.

#### 1.2.4 Replay export from training rollouts
- Eval callback writes the best/worst eval rollout's `replay.json` to the run directory.
- Verify the replay opens in sandbox-web and renders the agent's attack.

### Exit criteria for Phase 1

- All TH6 entities present in `data/*.json` and respected by the simulator.
- Six golden-replay scenarios passing (vanilla movement, splash Mortar, Wizard splash, WB pathing, Lightning, full TH6 attack).
- ~30 hand-built bases + 5 eval bases authored.
- Sandbox-web manual editor functional.
- MVP-Tiny acceptance criterion (AC-B1): trained agent beats random baseline by ≥30 percentage points on tracer base.
- A replay of the trained agent's attack is visualizable in sandbox-web.

---

## Phase 2 — MVP-Real

**Goal.** Train an agent that achieves ≥50% three-star rate on the 30-base training set and ≥30% three-star rate on the 5-base frozen eval set, using the full TH6 troop roster + Lightning.

Roughly 8–12 weeks.

### 2.1 Full action space activation
- Expand the action space to include all 6 troop channels + Lightning channel (`C_act = 7`).
- Validate action-mask correctness with property tests (no out-of-housing deploys, no out-of-spell casts, no perimeter violations).

### 2.2 Full observation space
- Land all spatial channels enumerated in `barracks/design.md` §3.2.
- Land all scalar fields in `barracks/design.md` §3.3.
- Tune `C_obs` based on first ablations.

### 2.3 Curriculum
- Implement `curriculum.py` callback.
- Round 1: train on 5 easy bases, promote at training mean stars ≥ 2.0.
- Round 2: train on full 30-base set, promote at training mean stars ≥ 2.0.
- Round 3: train on full set + mutations.

### 2.4 Mutation pipeline
- `app/data/mutations.py`: rotate, mirror, jitter, wall-edits.
- Verify each mutation produces a valid `BaseLayout` (TH6-rules-compliant, no overlap, fits grid).
- Wire mutations into `EnvConfig`: `mutation_probability`, `mutation_kinds`.

### 2.5 Reward tuning sessions
- Dedicated A/B sessions on `building_weights`, `troop_loss_coeff`, `time_penalty_per_tick`.
- Tune on training metrics only; eval set is read-only measurement.
- Each weight version committed as `reward_weights_v<n>.json`; configs reference by path.

### 2.6 Hyperparameter sweep
- Sweep `learning_rate`, `gamma`, `clip_range`, `ent_coef`, `n_steps`, `batch_size`, network depth/width.
- Bayesian optimization or grid search over a tractable subset; document results in `app/experiments/sweeps/`.

### 2.7 Eval automation
- Eval callback at every 50k training steps against the 5 frozen eval bases.
- Per-base metrics + aggregate: `eval_mean_stars`, `eval_mean_destruction_pct`, `eval_three_star_rate`, `train_eval_gap`.
- Publish a summary HTML report per run via simple template (`eval_results.html`).

### 2.8 Procedural generator (escalation if needed)
- Build only if Phase 2 shows `train_eval_gap` exceeds threshold (eval mean < 60% of train mean) — heuristic for catastrophic overfit.
- Implementation: `app/data/generator.py` with constrained random placement.
- Otherwise: deferred to v2.

### 2.9 Replay-driven debugging
- Implement a "diff replays" tool: run the same agent on the same base, compare two replays, surface differences (useful for non-determinism regressions).
- Implement an "attribution heatmap" overlay in sandbox-web: per-tick, show which obs channels had high gradient norm to the chosen action (research-grade, optional).

### Exit criteria for Phase 2

- AC-B2 satisfied: trained agent achieves ≥50% three-star rate on training set and ≥30% on the held-out eval set.
- Full TH6 action space and observation space active.
- Curriculum and mutations integrated and validated.
- Replays of representative agent attacks (best 3-star, worst failure) loaded into sandbox-web for human inspection.
- A short writeup published at `app/experiments/notes/mvp_real_results.md` summarizing what the agent learned, what surprised the researcher, and what failure modes remain.

---

## Phase 3 — The Cartographer + generalization (v2)

**Goal.** Build the Roboflow-based pipeline that turns a real Clash base screenshot into a `BaseLayout` JSON. Evaluate the MVP-Real-trained agent's performance on scraped bases.

Roughly 6–10 weeks. *Cartographer-specific architecture details will be revisited in a per-subsystem grilling session before this phase begins.*

### 3.1 Cartographer scaffolding
- Promote `app/cartographer/` from stub to full package.
- Implement `cartographer/preprocess.py`: image loading, crop-to-play-area, perspective correction (homography or learned).
- Set up Roboflow project off-codebase: define class taxonomy, label initial dataset, train detection model.

### 3.2 Detection
- Implement `cartographer/detect.py`: thin wrapper around Roboflow Inference SDK.
- Configure via `app/data/cartographer_config.json` (project, dataset_version, endpoint, confidence_threshold).
- Hosted vs local inference choice; default to hosted in v1 of Cartographer.

### 3.3 Bbox-to-grid alignment
- Implement `cartographer/align.py`: map bbox centers to tile coords, infer footprints from bbox dimensions + class-specific footprint catalog, resolve overlaps.

### 3.4 Schema emission
- Implement `cartographer/emit.py`: build `BaseLayout` from aligned detections, validate against schema, fail loudly on uncertain inputs.
- CLI: `python -m cartographer ingest --in screenshot.png --out scrape_001.json`.

### 3.5 Roboflow training-data pipeline
- Decide synthetic vs real labeling (or hybrid). The user's choice; codebase doesn't need to know.
- Optional: sandbox-web "headless screenshot" mode that renders synthetic bases at deterministic camera angles for synthetic training data.

### 3.6 Transfer evaluation
- Run the MVP-Real-trained agent on Cartographer-scraped bases.
- Measure star rate vs the synthetic eval set; the gap is the synthetic-to-real transfer cost.
- Optional: fine-tune the agent on a small set of scraped bases.

### Exit criteria for Phase 3

- AC-C1, AC-C2, AC-C3 satisfied.
- ≥20 scraped bases ingested and rendered correctly in sandbox-web.
- A writeup at `app/experiments/notes/cartographer_results.md` summarizing detection accuracy, transfer performance, and ergonomic notes on the Roboflow workflow.

---

## Phase 4 — Continuation (beyond TH6)

**Goal.** Scale the simulator and the agent past the TH6 ceiling locked into v1. Town Hall progression brings new defenses, new troops, new spells, heroes with active abilities, and air mechanics — each a meaningful addition to the strategic surface area. *Phase 4 is open-ended; specific TH levels and content cuts will be planned in dedicated grilling sessions before each sub-phase begins.*

**Indicative content directions** (each lands as its own sub-phase or grilling session):

- **TH7 content.** Healer, Barbarian King (first hero), Hidden Tesla, Heal Spell, additional army camp slots. Air troops + air-defense interactions become live (Air Defense stops being inert).
- **TH8 content.** Dragon, P.E.K.K.A, Wizard Tower upgrades, Rage Spell, dark-elixir economy hooks (Minion, Hog Rider, Valkyrie, Golem).
- **TH9 content.** Archer Queen (second hero), X-Bow, Witch, Lava Hound, Jump Spell, Freeze Spell, Skeleton Spell. Two-hero coordination becomes part of the action space.
- **TH10+ content.** Inferno Tower, Grand Warden, Bowler, Eagle Artillery, additional spells, deeper hero ability trees.
- **Heroes and hero abilities.** Heroes are persistent, single-instance units with HP that regenerates between attacks (off-sim concern) and a *hero ability* — an active, agent-triggered cooldown skill (King's Iron Fist, Queen's Royal Cloak, Warden's Eternal Tome, etc.). Adds a new action class to the action space and a new obs channel for ability cooldowns.
- **Air units and anti-air mechanics.** Activate the inert Air Defense behavior wired in v1. Distinguish ground vs air targeting in defense `target_filter` (already a data field). Add air-only troops (Healer, Dragon, Minion, Lava Hound).
- **Filled Clan Castle.** Defender troops spawn from the CC when the attacker enters trigger range. Adds defender-side troop AI — a meaningful but bounded extension of the existing troop AI.
- **Procedural generator with TH-aware constraints.** Generalize the deferred procedural generator from §2.8 to respect TH-level cap counts and unlocks.
- **Cross-TH agent generalization.** Train a single agent that selects strategy across TH levels, or train per-TH specialists and study transfer.

**Why this phase is open-ended.** Each TH level adds 2–6 new entities and 0–2 new mechanics. Every addition is a JSON edit to the data-driven core (FR-S3) plus minor obs-channel and action-channel extensions. The architecture committed in v1 is *intended* to absorb this scope without re-design — this phase is the test of that claim. If any sub-phase requires breaking changes to `BaseLayout` or `Replay` schemas, those go through the `schema_version` migration path (see `technical.md` §4.4).

**Exit criteria for Phase 4 (per sub-phase, not phase-wide).**

- New TH-level content lands data-driven, with golden replays for any new mechanic (heroes, hero abilities, air units, filled CC).
- Agent achieves a comparable star rate on the new TH level's hand-built eval set.
- The Cartographer (if invoked at the new TH level) successfully ingests bases at that level, gated by retraining the Roboflow model on TH-level-appropriate labeled data.

---

## Cross-phase concerns

These run continuously across all phases and don't fit cleanly into any one of them.

- **Documentation maintenance.** Per-subsystem PRDs (`app/docs/{sandbox,barracks,cartographer}/prd.md`) get filled in via dedicated grilling sessions before their corresponding phase begins. The ubiquitous-language glossary grows as new terms are introduced.
- **Test discipline.** Every new mechanic, defense type, or troop ability lands with at least one unit test and at least one golden-replay fixture if it changes simulation output.
- **Reproducibility hygiene.** Training runs only ship from clean working trees (`--allow-dirty` exists for emergencies, but flagged in run metadata). Config snapshots are immutable post-run.
- **Reward-weight discipline.** Tuning happens in dedicated sessions; weights are versioned files, not ad-hoc edits.
- **Observability.** Every run writes tensorboard logs + a JSON eval-results trail. Cross-run comparison is via a simple `app/experiments/index.json` rolled up by a script.
- **Performance budget.** If Sandbox throughput drops below 50 episodes/sec/worker on full TH6 attacks, profile and optimize hot loops (Numba on `step_tick` inner pieces is the first escalation; Cython or Rust port is a Phase-2.5+ option only if profiling proves it's required).

## Issue authorship workflow

Each phase decomposes into issue clusters that the agentic ralph loop expands into individual issue files.

- High-level issue clusters live as headers in this roadmap (e.g., "1.1.1 Defenses + splash damage").
- Concrete issues are authored in `app/docs/{subsystem}/issues/open/*.md` per the structure described in `agent.md`.
- An issue's done state is marked by moving it to `app/docs/{subsystem}/issues/done/`.
- The `prd-to-issues` skill (`/prd-to-issues`) can decompose a per-subsystem PRD into a starting set of issues; that's the kickoff for each phase.

## Risks and contingencies (roadmap-specific)

- **Phase 0 takes longer than 2 weeks.** Likely because schema design or Pixi rendering hits a snag. Mitigate by aggressively cutting scope — the only Phase 0 deliverable is the tracer bullet running end-to-end, even if the renderer is just colored squares with HP numbers as text.
- **Phase 1 RL training fails to learn even with shaped reward.** The failure surface is multi-causal: bad reward, bad obs encoding, bad action mask, bad sim. Diagnose by progressively simplifying the env (single-tile attack, deterministic policy, manual reward inspection) until learning is observed, then re-add complexity.
- **Phase 2 eval gap is huge (catastrophic overfit).** Trigger the procedural generator escalation in 2.8. If still bad, expand the hand-built bank.
- **Phase 3 detection accuracy is too low for transfer.** This is a Cartographer-specific risk to be addressed in the dedicated grilling session before Phase 3 begins.
