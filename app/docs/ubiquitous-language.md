# Ubiquitous Language

The shared glossary for threestarRL. Every doc, issue, commit message, and code identifier should use these terms consistently. When you see an alias listed below, prefer the canonical term.

## Subsystems and project structure

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **The Sandbox** | The simulator subsystem — owns world state and produces replays. Refers to the *whole* subsystem (core + web). | "the sim", "the engine", "Clash sim" |
| **Sandbox-core** | The pure-Python simulator package at `app/sandbox_core/`. Headless, deterministic, RL-importable. | "the core", "sim core" |
| **Sandbox-web** | The TypeScript + React + PixiJS frontend at `app/sandbox_web/`. Replay viewer and manual base editor. Never drives simulation live. | "the frontend", "the viewer" (when also editing) |
| **The Barracks** | The RL subsystem — the Gymnasium environment, training loop, and eval pipeline. | "the RL", "the trainer", "the env" |
| **The Cartographer** | The CV subsystem — turns a screenshot into a `BaseLayout` JSON via a Roboflow-based pipeline. Deferred to v2. | "the CV pipeline", "image-to-grid" |

## Milestones and process

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **MVP-Tiny** | First milestone — agent on one hand-built base with one troop type beats a random-deploy baseline. | "v0", "tracer goal" |
| **MVP-Real** | Second milestone — agent achieves ≥50% three-star rate on training, ≥30% on the held-out eval set, with full TH6 roster. | "v1 RL", "the real one" |
| **v2** | Third milestone — Cartographer ingests real screenshots, agent attacks scraped bases. | "MVP-Wild", "phase 3 milestone" (use Phase 3 for the *roadmap* stage, v2 for the *milestone*) |
| **Tracer bullet** | A thin, working slice through the full system that proves the architecture end-to-end. The Phase 0 deliverable. | "spike", "POC", "skeleton" |
| **Phase** | A roadmap stage (Phase 0, 1, 2, 3). Distinct from milestones — phases are time-boxed work, milestones are headline results. | "stage", "iteration" |
| **Ralph loop** | The issue-execution loop driven by `ralph/prompt.md`. Picks an open issue, executes it, commits, marks it done. | "the agent", "the runner" |
| **Issue** | A markdown task file in the root `issues/open/` queue. Moves to `issues/done/` when complete. All subsystems share the single queue. | "ticket", "todo" |

## Clash / TH6 game domain

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **TH6** | Town Hall level 6 — the entire content scope for v1. | "th-six", "level 6" |
| **Town Hall** (TH) | The central building of every base. Destroying it grants 1 star. | "the throne", "main" |
| **Defense** | Any building with attack behavior. At TH6: Cannon, Archer Tower, Mortar, Air Defense, Wizard Tower. | "tower" (Cannon is not a tower), "shooter" |
| **Splash damage** | Area-of-effect damage applied within `splash_radius` of an impact point. Only Mortar, Wizard Tower, and Wizard inflict it at TH6. | "AoE" (acceptable in code, prefer "splash" in prose) |
| **Wall** | A 1×1 destructible tile that blocks pathfinding. Modeled with an `is_wall` flag in v1, not as edge-walls. | "fence", "barrier" |
| **Troop** | An attacker unit deployed by the player (or agent). At TH6: Barbarian, Archer, Goblin, Giant, Wall Breaker, Wizard. | "unit" (use "troop"; "unit" is a generic that drifts) |
| **Target preference** | A troop's targeting bias: Goblin→resources, Giant→defenses, Wall Breaker→walls. Implemented as a `target_preference` data field, never as polymorphism. | "AI", "behavior" |
| **Housing space** | The capacity cost a troop occupies in army camps. Used to mask invalid deploys when capacity is exhausted. | "supply", "slot" |
| **Spell** | A one-shot ability cast at a tile. Only Lightning Spell at TH6. | "ability", "magic" |
| **Stars** | The 0–3 score earned per attack: 50% destruction, TH destroyed, 100% destruction. | "score" (use Score for the schema, stars for the count) |
| **Three-star** | Verb or noun for destroying 100% of a base (earning all 3 stars). | "max", "perfect attack" |
| **Destruction percent** | Fraction of base HP destroyed, weighted by building. Drives the smooth Δ-reward signal. | "damage %", "destroyed %" |
| **Clan Castle** (CC) | A defensive building. In v1 it is *building-only* (no defending troops). Filled CC is a v2 concern. | "fortress", "donation building" |
| **Heroes** | King, Queen, etc. Out of scope project-wide for v1. | "champions" |

## Sandbox simulation

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **Tick** | The atomic unit of simulated time. 100 ms at v1 (10 Hz). All speeds, cooldowns, and durations are tick-denominated. | "frame" (use **TickFrame** for the schema, tick for the time unit) |
| **Tick rate** | The fixed simulation frequency. 10 Hz in v1. | "framerate" (rendering is 60 fps; tick rate is sim-only) |
| **World state** | The complete simulator state at one tick — buildings, troops, projectiles, spells, score, tick number. The single source of truth. | "the state", "snapshot" (use **WorldState** for schema, "world state" in prose) |
| **Step (sim)** | Advancing the simulator one tick via `step_tick()`. | overloaded with **Step (env)** |
| **Step (env)** | One call to `env.step()`. Advances simulation from the current decision point to the next. May span many sim ticks. | overloaded with **Step (sim)** |
| **Step (training)** | One PPO gradient step. Distinct from env step and sim step. | "iteration" |
| **Decision point** | The moment when the agent must act: episode start, after each deploy, on agent-requested wakeup. | "turn", "action moment" |
| **Decision-point action model** | The framing where the agent acts only at decision points, not every tick. Reduces the effective horizon from ~1800 to ~30 actions per attack. | "tactical timing", "event-driven actions" |
| **Determinism / deterministic-no-RNG** | The v1 rule that the simulator uses no randomness. Ties resolve by canonical ordering. | "reproducible" (use only in the experiment-tracking sense) |
| **Footprint** | A building's multi-tile occupancy `(h, w)`. Walls = 1×1, Cannon = 3×3, Town Hall = 4×4. | "size", "extent" |
| **Grid** | The 44×44 tile world. | "map", "board" |
| **Perimeter** | Tiles in the deploy zone — where troops may spawn. Computed from the base layout. | "border", "edge", "deploy zone" (acceptable synonym, but prefer perimeter) |
| **Episode** | One full simulated attack. Same thing the game calls an "attack." Use **episode** in RL contexts; **attack** is acceptable in game prose. | "match", "round" |
| **Pathfinding** | A* with cached paths, recomputed on target death or wall break. | "navigation" |
| **Event** | A typed in-attack moment emitted per tick: `deploy`, `attack_start`, `projectile_fired`, `damage`, `destroyed`, `spell_cast`. | "log entry", "message" |
| **Replay** | The complete record of one attack: initial state + per-tick frames + final score. The interchange format between the simulator and the web viewer. | "log", "trace" |
| **TickFrame** | One tick's payload inside a Replay: full `WorldState` + list of `Event`s. | "frame", "snapshot" (when in code) |
| **Hybrid replay format** | The chosen replay encoding: full state per tick *plus* an events list per tick. Phased: Phase 1 ships full-state-per-tick; deltas added later only if needed. | "snapshot format" (ambiguous) |
| **Golden replay** | A frozen `(base.json, plan.json) → expected_replay.json` fixture in `tests/golden/replays/`. The architectural keystone for regression testing in a deterministic sim. | "snapshot test", "regression fixture" |

## RL / Barracks

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **Observation** | The agent's input at a decision point: spatial tensor + scalar globals + action masks. | "state" (the **WorldState** is the sim's truth; the observation is the agent's encoded view — they are *not* synonyms) |
| **Spatial obs** | The `(C_obs, 44, 44)` channels-first tensor of grid-aligned semantic features. | "image", "frame" |
| **Scalar globals** | The non-spatial observation vector: time remaining, current stars, troops left, etc. | "metadata", "globals" (acceptable shortened) |
| **Action** | The agent's choice at a decision point. Encoded as a single flattened `Discrete(C_act * 44 * 44 + n_scalar)`. | "move", "command" |
| **Action mask** | The boolean tensor zeroing out invalid actions before softmax. Exposed as part of the observation. | "valid_actions", "legal mask" |
| **Spatial action** | An action indexed by `(action_channel, row, col)` — a deploy or spell at a tile. | "tile action" |
| **Scalar action** | A non-spatial action — `wait_50`, `wait_100`, `wait_200`, `end_attack`. | "meta action", "control action" |
| **Wait bucket** | A coarse-grained delay action (5 / 10 / 20 seconds). | "skip", "no-op" (no-op is wrong — wait is intentional) |
| **Reward** | The per-step scalar feedback the agent optimizes. | — |
| **Layered shaped reward** | The v1 reward design: a sum of star-bonus + Δ-destruction + TH-destroyed + per-building weights + small time/troop penalties. | "shaped reward" (ambiguous), "bonus reward" |
| **Sparse star bonus** | The dominant reward component — large terminal payouts at 1/2/3 stars. | "win bonus", "terminal reward" |
| **Reward weights** | The tunable coefficients in `data/reward_weights.json`. Tuned in dedicated sessions, never to game eval metrics. | "reward config" |
| **Per-building weight** | A coefficient that adjusts the reward earned for destroying a specific building type (e.g., destroying a Mortar gives more than destroying a Storage). | "priority", "value" |
| **Policy** | The neural network mapping observation → action distribution. SB3's `MaskablePPO` policy with a custom CNN feature extractor. | "model" (model is the SB3 wrapper around the policy; not synonyms) |
| **Feature extractor** | The custom CNN + scalar MLP module that produces `features_dim=512` for the policy and value heads. | "encoder" (acceptable in informal prose) |
| **Run** | One execution of the trainer, identified by a `run_id`. Has a self-contained directory at `app/experiments/runs/<run_id>/`. | "training session", "experiment" |
| **Run directory** | The folder containing a run's config snapshot, checkpoints, eval results, replays, tensorboard logs. | "output dir", "artifacts" |
| **Rollout** | One episode of policy execution (training or eval). | "trajectory", "playthrough" |
| **Vec env** | A vectorized Gymnasium environment — multiple env workers stepping in parallel. We use `SubprocVecEnv` with 16 workers. | "parallel env", "env pool" |
| **Worker** | One process inside a vec env. Holds its own `Sim` and steps independently. | "thread" (we don't use threads — GIL) |
| **Curriculum** | The base-set schedule across training rounds. Round 1: easy bases. Round 2: full set. Round 3: full + mutations. | "syllabus", "schedule" |
| **Training distribution** | The set of bases sampled during a training run, including mutations. | "dataset" (acceptable but biased toward supervised framing) |
| **Mutation** | A transformation applied to a `BaseLayout` to expand the training distribution: rotate, mirror, jitter, wall-edits. | "augmentation" (acceptable, but mutation is canonical here because it operates on layouts not images) |
| **Frozen eval set** | The 5 hand-built bases held out from training and used only for measurement. Never re-tuned. | "test set", "validation set" (avoid these — they have specific supervised meanings that don't apply here) |
| **Eval gap / train-eval gap** | `train_mean - eval_mean`. The overfit signal. | "generalization gap" (acceptable synonym in writeups) |
| **Smoke training** | The CI sanity training run (~1000 steps, no GPU). Asserts no crashes, no NaN losses. | "CI training" |

## Data contracts (schemas)

These are Pydantic v2 models in `app/sandbox_core/schemas.py`. They are first-class domain terms — when discussing data interchange, use the schema name, not a paraphrase.

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **BaseLayout** | The frozen description of a base: grid size, TH level, building placements, CC contents, schema version. The *universal contract* — hand-built, mutated, generated, and Cartographer-emitted bases all conform to this schema. | "base", "base config", "map" |
| **BuildingPlacement** | One placed building within a `BaseLayout`: `(building_type, origin, level)`. | "building entry" |
| **DeploymentPlan** | An ordered list of `DeploymentAction`s for a scripted attack. Used by the CLI; not used by the RL env (the agent emits actions directly at step time). | "script", "attack plan" |
| **DeploymentAction** | One scheduled deploy or spell: `(tick, kind, entity_type, position)`. | "command", "move" |
| **WorldState** | The full sim state at one tick. | "snapshot" (the schema is **WorldState**) |
| **Score** | The per-attack outcome: `(stars, destruction_pct, ticks_elapsed, town_hall_destroyed)`. | "result", "outcome" |
| **TrainingConfig** | The top-level config for one training run: env, policy, reward, schedule, eval, seed. | "run config", "params" |
| **RewardWeights** | The reward coefficient bundle. Loaded from `data/reward_weights.json`, snapshot per run. | "reward config" |
| **BuildingType / TroopType / SpellType** | Static stat definitions for each entity, loaded from `data/*.json` and exposed as immutable singletons via `sandbox_core.content`. Distinct from a placed instance (which is a **Building**, **Troop**, or **Spell**). | "BuildingDef", "Stats" |
| **Schema version** | An integer field on every persisted JSON (`schema_version: int = 1`). Drives forward-compatible migrations. | "format version" |

## Cartographer (v2)

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **Roboflow pipeline** | The Cartographer's chosen architecture: screenshot → Roboflow object detection → grid alignment → footprint reconstruction → BaseLayout emission. | "the CV model", "the detector" |
| **Detection** | A single bounding box + class label + confidence emitted by the Roboflow model. | "prediction", "bbox" |
| **Grid alignment** | The pipeline stage that maps detection bbox centers to grid tile coordinates. | "tile mapping" |
| **Footprint reconstruction** | The pipeline stage that infers a building's footprint from its bbox and class. | "shape inference" |

## Relationships

- A **Replay** belongs to one **BaseLayout** and one **DeploymentPlan** (or one agent rollout) and contains many **TickFrame**s in order.
- A **TickFrame** contains exactly one **WorldState** and zero-or-more **Event**s.
- A **WorldState** contains zero-or-more **Building**s, **Troop**s, **Projectile**s, **Spell**s, and exactly one **Score**.
- A **Building** has exactly one **BuildingType**, one origin tile, and one **Footprint**.
- A **Run** produces one config snapshot, many checkpoints, many eval results, and many **Replay**s.
- An **Episode** runs one **BaseLayout** sampled from the active **training distribution**, produces one **Replay**, and yields one terminal **Score**.
- A **BaseLayout** comes from one of: a hand-built source, a **Mutation** of a hand-built source, the deferred procedural generator, or the **Cartographer**.
- The **Action mask** is a function of the current **WorldState**: it depends on perimeter, occupancy, troops remaining, and spells remaining.
- A **Decision point** triggers exactly one **Step (env)** call, during which the agent emits one **Action**.

## Example dialogue

> **Dev:** "When the agent emits a spatial **action** at a non-perimeter tile, what happens?"

> **Domain expert:** "It can't — the **action mask** zeros that index out before softmax. The agent only ever samples valid actions. The mask is rebuilt from the **WorldState** at every **decision point**."

> **Dev:** "OK, so on `env.step()` — that's one **step (env)**, which advances the **Sim** through many **step (sim)** calls until the next **decision point**?"

> **Domain expert:** "Right. The **Sim** runs at 10 Hz, but the agent only sees the world at decision points. Between them, the simulator emits **TickFrame**s into the **Replay** — the agent doesn't see those, but the web viewer does."

> **Dev:** "And the **reward** the agent receives on that step is the sum of all the per-tick deltas during the fast-forward?"

> **Domain expert:** "Exactly. The **layered shaped reward** is computed by diffing the **WorldState** at the start and end of the step — Δ-destruction, Δ-stars, building-by-building Δs weighted by the **reward weights**. The **sparse star bonus** lands at episode end."

> **Dev:** "If we trained on a **mutation** of `base_07` and evaluated on `eval_03`, the **eval gap** measures whether the agent generalized?"

> **Domain expert:** "Yes — and `eval_03` is in the **frozen eval set**, so it never sees gradient updates, and we never tune the **reward weights** to make it look better. That set is read-only measurement."

## Flagged ambiguities

These are terms that drifted in the conversation. Each lists the canonical resolution.

- **"Step"** was used for three distinct things: `Sim.step_tick()` (one sim tick), `env.step()` (one env step that may advance many sim ticks), and a "training step" (one PPO gradient update). Always qualify: **step (sim)**, **step (env)**, **step (training)**.

- **"State"** was used both for the simulator's truth (`WorldState`) and the agent's encoded view. These are distinct concepts: **WorldState** is the simulator's full truth; **observation** is the agent's encoded view. They are *not* synonyms.

- **"Frame"** was used for both `TickFrame` and informal "rendered frames." Use **TickFrame** when referring to the schema or per-tick payload; use **render frame** if discussing the 60fps web viewer.

- **"The Sandbox"** is the whole subsystem; **sandbox-core** is the Python package; **sandbox-web** is the web project. Always pick one — never just say "the sandbox" when you mean only the core or only the web.

- **"Action"** vs **"Deployment"** vs **"DeploymentAction"**: an **Action** is what the *agent* emits (one decision-point output); a **Deployment** is the *side effect* on the world (a troop spawning); a **DeploymentAction** is the schema for a *scripted* deploy in a `DeploymentPlan`. The RL env converts the agent's actions into deployments at step time; it does not emit `DeploymentAction`s.

- **"Score"** vs **"stars"**: **Score** is the schema (`stars`, `destruction_pct`, `ticks_elapsed`, `town_hall_destroyed`). **Stars** is one specific field of Score (and the headline metric). Don't say "the score" when you mean the star count.

- **"Run"** vs **"episode"**: a **run** is one execution of the trainer (potentially millions of episodes). An **episode** is one attack. Don't say "training run" when you mean one episode and vice versa.

- **"Test set"** / **"validation set"** vs **"frozen eval set"**: the supervised-learning terms don't fit cleanly here. Use **frozen eval set** for the 5 hand-built bases held out from training. Use **eval set** as shorthand once it's clear from context.

- **"Phase"** vs **"milestone"**: a **phase** is a roadmap stage (Phase 0, 1, 2, 3 — time-boxed work). A **milestone** is a headline result (MVP-Tiny, MVP-Real, v2 — outcome-based). They line up imperfectly: Phase 0 has no milestone of its own; Phase 1 contains both content work and the MVP-Tiny RL milestone in parallel.

- **"v2"** is the **Cartographer milestone**. **Phase 3** is the *roadmap stage* that delivers v2. They are related but not synonyms — Phase 3 is the work, v2 is the result.

- **"Wait"** vs **"no-op"**: **Wait** is an intentional, agent-chosen scalar action with a fixed duration. It is not a no-op. The agent expressing patience is a real strategic choice.
