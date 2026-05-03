# The Barracks — RL Design

This document captures the reinforcement-learning design for threestarRL: observation space, action space, reward function, training distribution, eval protocol, library integration. It complements `app/docs/technical.md` (architecture-only) and the future `app/docs/barracks/prd.md` (per-subsystem PRD, written in a later grilling session).

## 1. Problem framing

The Barracks wraps the Sandbox in a Gymnasium-compliant RL environment. The agent's job: pick a sequence of deployments and spell casts during a single TH6 attack to maximize stars + destruction.

**Episode definition.** One episode = one full attack on one base. Episode terminates when: 3 stars achieved, attack timer expires (180 s = 1800 ticks at 10 Hz), or the agent voluntarily ends the attack.

**Decision-point episodes, not per-tick.** The agent does not act every tick. It acts only when a decision is needed: at episode start, after each deploy, and on agent-requested wakeups. Between decisions, the simulator fast-forwards. This collapses the effective horizon from ~1800 to ~30 actions per episode.

Why this matters: per-tick agents have to learn that ≥99% of actions should be no-ops, which is a brutal sparse-credit-assignment problem. Decision-point framing skips that entirely.

## 2. Action space

### 2.1 Conceptual structure

At each decision point the agent picks one of:

- **Deploy** a troop type at a perimeter cell.
- **Cast** a spell at any base cell.
- **Wait** a fixed-bucket number of ticks before the next decision.
- **End** the attack.

### 2.2 Concrete encoding

Single flattened `gym.spaces.Discrete(C_act * 44 * 44 + n_scalar)`:

- The first `C_act * 44 * 44` indices encode `(action_channel, row, col)` triples:
  - Channels 0..K_TROOP-1: deploy each troop type at this cell.
  - Channels K_TROOP..K_TROOP+K_SPELL-1: cast each spell at this cell.
  - Total spatial channels: `C_act = K_TROOP + K_SPELL`. For TH6 with 6 troops and 1 spell, `C_act = 7`.
- The trailing `n_scalar` indices encode non-spatial actions:
  - `wait_50_ticks` (5 s)
  - `wait_100_ticks` (10 s)
  - `wait_200_ticks` (20 s)
  - `end_attack`
  - Total `n_scalar = 4`.

Total action space size = `7 * 44 * 44 + 4 = 13 556`. Tractable for masked PPO.

### 2.3 Action masking

Action mask is exposed in the observation as `action_mask_spatial: (C_act, 44, 44)` and `action_mask_scalar: (n_scalar,)`. The flattened mask is the concatenation. SB3 `MaskablePPO` consumes it via the `action_masks` info-dict key on each `step()` return.

**Spatial mask rules:**

- A `(troop_channel, row, col)` cell is *valid* iff:
  - `(row, col)` is a perimeter / deploy-zone tile,
  - the cell is not occupied by a building or wall,
  - the agent has at least one of that troop type remaining in housing,
  - the troop has not been previously deployed at this exact cell within the last `K` ticks (anti-jitter; optional).
- A `(spell_channel, row, col)` cell is *valid* iff:
  - `(row, col)` is inside the playable area (not red border),
  - the agent has at least one of that spell type remaining,
  - the cell is not on a destroyed-building tile (cosmetic — spells still cast on rubble are wasted).

**Scalar mask rules:**

- `wait_*` always valid except at episode start (must deploy first action) — implementation detail.
- `end_attack` always valid (gives the agent the option to terminate early; small bonus through the time-saved channel).

### 2.4 Why this design

- **Spatial action mirrors spatial observation.** A CNN policy can map directly from "what's at cell (r,c)?" to "what to do at cell (r,c)?". This is the inductive bias that made AlphaStar tractable for similar grid-shaped problems.
- **Single flattened `Discrete`** keeps SB3 `MaskablePPO` happy without custom action distributions.
- **Wait buckets are coarse** (5 / 10 / 20 s) — enough to express tactical pacing ("drop the next wave when the Giants tank the Cannon") without forcing millisecond-level timing learning.
- **`end_attack`** is included so the agent can choose to stop wasting troops once it has 3 stars or has stalled.

## 3. Observation space

### 3.1 Top-level structure

```python
observation_space = spaces.Dict({
    "spatial":              Box(0, 1, shape=(C_obs, 44, 44), dtype=float32),
    "scalar":               Box(-1, 1, shape=(N_SCALAR,),    dtype=float32),
    "action_mask_spatial":  Box(0, 1, shape=(C_act, 44, 44), dtype=int8),
    "action_mask_scalar":   Box(0, 1, shape=(n_scalar,),     dtype=int8),
})
```

### 3.2 Spatial channels (C_obs ≈ 30)

Channels are pre-decoded semantic features, not raw pixels. The agent does not have to learn what a Cannon "looks like" — channel 4 *is* the cannon-presence map.

Indicative ordering (final count finalized during MVP-Tiny implementation):

| Block | Channels | Description |
|---|---|---|
| Per-building footprint | K_BLD ≈ 12 | Binary mask, 1.0 on every tile occupied by that building type. One channel per type (TH, Cannon, Archer Tower, Mortar, Air Defense, Wizard Tower, Wall, CC, storages, collectors, mines, other). |
| Per-building HP percent | K_BLD ≈ 12 | HP / max_HP, smeared over footprint cells. |
| `is_destroyed` | 1 | Binary mask of destroyed building tiles. |
| `is_wall` | 1 | Convenience copy from footprint channels for fast Wall-Breaker reasoning. |
| `is_perimeter` | 1 | Static deploy-zone mask. |
| `is_blocked` | 1 | Tile is occupied by anything (building or wall). |
| Per-troop density | K_TROOP = 6 | Count of attacker troops of each type at each tile, smeared. |
| Per-troop HP percent | K_TROOP = 6 | Mean HP percent of troops of that type at the tile. |
| `defense_attacking` | 1 | 1 where defenses are mid-attack this tick. |
| `projectile_in_flight` | 1 | 1 where a projectile currently overlaps the cell. |
| `spell_active` | 1 | 1 where a spell's AoE is currently active. |

Total ≈ 12 + 12 + 1 + 1 + 1 + 1 + 6 + 6 + 1 + 1 + 1 = **43**. Final number tuned during MVP-Tiny implementation; channel additions/removals are configuration changes, not architecture changes.

### 3.3 Scalar globals (N_SCALAR ≈ 16)

| Field | Range | Description |
|---|---|---|
| `time_remaining_pct` | [0, 1] | Ticks remaining / 1800. |
| `current_stars` | {0, 1, 2, 3} | One-hot encoded (4 floats). |
| `destruction_pct` | [0, 1] | Total destruction percent. |
| `troops_left_pct[K_TROOP]` | [0, 1] | Per-troop housing space remaining. |
| `spells_left[K_SPELL]` | {0, 1} | Per-spell remaining count. |
| `decision_point_idx_pct` | [0, 1] | Capped at e.g. 60. |
| `elapsed_ticks_pct` | [0, 1] | Redundant with time_remaining but easy. |

### 3.4 Why pre-decoded semantic channels

- The agent doesn't need to learn Clash visuals from scratch.
- HP smeared over footprint lets a CNN see "this 3×3 cannon at 30% HP" in a single conv.
- Per-troop density (instead of per-troop instance) keeps channel count constant regardless of troop count.
- Static masks (perimeter, blocked) repeated every step are wasteful in bytes but trivial for the policy network.

### 3.5 Frame stacking?

**Not in v1.** Decision-point framing means consecutive observations are temporally distant (often 5–20 s apart). Stacking adjacent frames would mix snapshots from very different game states. If temporal context proves insufficient, add an LSTM head before frame stacking.

## 4. Reward function

### 4.1 Formula

Per-step reward (where Δ denotes the change since the last step):

```
reward(step) =
    + 100 * Δ stars_earned
    +   1 * Δ destruction_pct
    +  20 * Δ town_hall_destroyed         # one-time +20 when TH falls
    + Σ b_i * Δ destroyed[building_type_i]  # per-building weights
    -   ε * Δ ticks_elapsed                 # tiny time penalty
    -   λ * Δ troop_value_lost              # troop-loss penalty
```

Plus a one-time end-of-episode bonus:

```
final_bonus =
    +500 if 3 stars
    +200 if 2 stars
    + 50 if 1 star
       0 otherwise
```

### 4.2 Coefficients

All coefficients live in `app/data/reward_weights.json`, overridable per training config.

```json
{
  "schema_version": 1,
  "delta_star": 100.0,
  "delta_destruction_pct": 1.0,
  "delta_town_hall_destroyed": 20.0,
  "time_penalty_per_tick": 0.001,
  "troop_loss_coeff": 0.5,
  "final_bonus_per_star": [0, 50, 200, 500],
  "building_weights": {
    "town_hall": 0.0,
    "cannon": 0.0,
    "archer_tower": 0.0,
    "mortar": 0.0,
    "wizard_tower": 0.0,
    "air_defense": 0.0,
    "clan_castle": 0.0,
    "wall": 0.0,
    "army_camp": 0.0,
    "storage": 0.0
  }
}
```

`building_weights` start at zero and are dialed in during MVP-Tiny eval sessions. Likely ending values bias toward defenses (e.g., Mortar = +5, Wizard Tower = +5, Cannon = +1) since defense destruction enables further troop survival.

### 4.3 Why layered shaping

- **Star bonuses dominate.** No matter what shaping the agent finds, the 3-star end-bonus dwarfs anything else.
- **Δ-destruction smooths between stars.** Avoids the sparse-only "all-or-nothing" signal that makes early PPO training fail.
- **TH-destroyed sub-bonus** because the second star fires on `(50% destruction OR TH destroyed)` — both paths matter and the agent should learn either.
- **Time penalty** is tiny (0.001/tick × 1800 ticks max = 1.8 reward worst case). Just enough to break ties between equivalent strategies in favor of faster ones.
- **Troop-loss penalty** is *cautiously* included. Without it the agent learns "throw all troops at the wall." With too much of it the agent becomes risk-averse and never deploys. Coefficient (0.5 × housing space) is a guess to be A/B'd at MVP-Tiny.
- **Per-building weights** are zeroed at start; tuned in during MVP-Tiny eval based on observed agent behavior.

### 4.4 Potential-based shaping property

The Δ-quantities form a telescoping sum: cumulative shaped reward over an episode equals the terminal sparse reward (`stars_earned * 100 + final_bonus + per-building totals`) up to the time-and-troop penalty. This is the textbook safe-shaping pattern (Ng et al. 1999) — optimal policies are unchanged by adding telescoping potential-based shaping terms.

The non-telescoping terms (time penalty, troop-loss penalty) can in principle bias the optimal policy. They're kept tiny precisely because of this.

### 4.5 Reward-shaping discipline

- Coefficients are tuned in **dedicated tuning sessions**, not during feature work, and only based on observed training behavior on the eval set.
- Each tuning change creates a new `reward_weights_v<n>.json` file in version control. Old runs reference their config snapshot, which references the weights file by path; the snapshot resolves the file content into the snapshot at run start, so the run is reproducible even after future weight edits.
- Hard rule: **never tune the shaping to make eval numbers look better on the held-out set.** Eval is for measurement only. Tune on the training set, then accept the eval result.

## 5. Training distribution

### 5.1 Tiered plan

| Phase | Training set | Eval set | Mutations |
|---|---|---|---|
| MVP-Tiny | 1 hand-built tracer base | same base, multiple seeds | none |
| MVP-Real | ~30 hand-built bases | 5 frozen hand-built bases | rotation, mirror, jitter |
| MVP-Real+ (if needed) | ~30 hand-built + procedural | 5 frozen hand-built + 5 procedural | as above |
| v2 (Cartographer) | scraped real bases | held-out scraped + synthetic | as above |

### 5.2 Mutation pipeline

Implemented in `app/data/mutations.py`. Operates on a `BaseLayout`, returns a new `BaseLayout`:

- **Rotate** — 0°, 90°, 180°, 270° (4× expansion, free).
- **Mirror** — horizontal, vertical (additional 2× expansion).
- **Jitter** — translate each non-TH building by ±N tiles where the move stays valid (no overlap, fits on grid). Seed-controlled.
- **Wall edits** — randomly add or remove K wall segments while preserving connectivity of major compartments.

A 30-base training set with 4 rotations + 2 mirrors + jitter mutations expands to 240+ effective bases. Sufficient first-pass training distribution.

### 5.3 Procedural generator (deferred until MVP-Real shows overfitting)

A constrained random generator in `app/data/generator.py` (not built in v1). Constraints:

- Respect TH6 cap counts (1 TH, 3 cannons, 3 archer towers, 2 mortars, 2 air defenses, 1 wizard tower, 1 CC, 75 wall segments, X storages, X collectors).
- Wall connectivity: every interior compartment is closed.
- No overlapping footprints; every building inside the buildable area.

Built only if MVP-Real eval gap (train mean − eval mean) exceeds the threshold for catastrophic overfit (heuristic: eval drops below 60% of train).

### 5.4 Eval protocol

- The 5 hand-built eval bases are **frozen** at the start of MVP-Real. They never enter training. Ever.
- Eval callback runs every K training steps (K = 50k by default, tunable). For each eval base, run N rollouts (N = 5) under deterministic policy mode (greedy argmax over masked logits).
- Logs per-base mean stars, mean destruction, mean ticks-to-3-star (where applicable), three-star rate.
- Aggregates: `eval_mean_stars`, `eval_mean_destruction_pct`, `eval_three_star_rate`, `train_eval_gap = train_mean - eval_mean`.

### 5.5 Curriculum

For MVP-Real:

- **Round 1.** Train on 5 easy bases (categorized by hand). Promote when training mean stars ≥ 2.0.
- **Round 2.** Train on full 30-base set. Promote when training mean stars ≥ 2.0.
- **Round 3.** Train on full set + mutations. Run until convergence on training, eval at intervals.

Curriculum is a `curriculum.py` callback that modifies the active base set at promotion thresholds, not a hardcoded schedule.

## 6. Library integration

### 6.1 SB3 + sb3-contrib MaskablePPO

```python
from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.utils import get_action_masks

model = MaskablePPO(
    policy=ThreestarPolicy,           # custom class — see §6.2
    env=vec_env,                       # SubprocVecEnv with 16 workers
    n_steps=2048,
    batch_size=512,
    learning_rate=3e-4,
    gamma=0.995,
    gae_lambda=0.95,
    clip_range=0.2,
    ent_coef=0.01,
    n_epochs=10,
    policy_kwargs=dict(features_extractor_class=ThreestarFeatureExtractor, ...),
    tensorboard_log=run_dir / "tensorboard",
)
model.learn(total_timesteps=10_000_000, callback=[EvalCallback(...), CurriculumCallback(...)])
```

### 6.2 Custom CNN feature extractor

```python
class ThreestarFeatureExtractor(BaseFeaturesExtractor):
    def __init__(self, observation_space, features_dim=512):
        super().__init__(observation_space, features_dim)
        c_obs = observation_space["spatial"].shape[0]
        self.conv = nn.Sequential(
            nn.Conv2d(c_obs, 64, 3, padding=1), nn.ReLU(),
            nn.Conv2d(64, 64, 3, padding=1), nn.ReLU(),
            nn.Conv2d(64, 128, 3, padding=1), nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4)),
            nn.Flatten(),
        )
        self.scalar = nn.Sequential(
            nn.Linear(observation_space["scalar"].shape[0], 64), nn.ReLU(),
        )
        self.fuse = nn.Sequential(
            nn.Linear(128 * 4 * 4 + 64, features_dim), nn.ReLU(),
        )

    def forward(self, obs):
        spatial_feat = self.conv(obs["spatial"])
        scalar_feat = self.scalar(obs["scalar"])
        return self.fuse(torch.cat([spatial_feat, scalar_feat], dim=-1))
```

The policy and value heads on top of `features_dim=512` are SB3 defaults. Action logits are masked using the obs's `action_mask_*` keys before softmax — handled by `MaskablePPO` automatically when the env exposes masks via `info["action_mask"]`.

Architectural notes:

- Conv stride 1 + AdaptiveAvgPool keeps spatial resolution information without forcing a specific input size.
- Spatial features collapse to 128 × 4 × 4 = 2048 floats; scalar features add 64. Fused dim = 512.
- Network depth/width tuning is a hyperparameter sweep, not architecture.

### 6.3 Vec env throughput

- `SubprocVecEnv` with 16 workers (one process per worker, fork model on Linux, spawn on Windows).
- Each worker holds a Sandbox `Sim` and runs at decision-point cadence.
- Aggregate target throughput: ≈800 episodes/sec (50 ep/sec/worker × 16 workers).
- GPU is dedicated to the policy network; sim runs on CPU.

### 6.4 Migration option

If MVP-Real uncovers a need for custom losses, hierarchical policies, imitation pretraining, or league play (none in v1 scope), migration to CleanRL is approximately 2 days: copy CleanRL's `ppo_atari.py`, point at our existing env, port the policy network. The env, obs builder, action mask, reward calculator, and replay format are all library-agnostic.

## 7. Reproducibility and experiment management

- Each run gets a unique `run_id` (timestamp + short hash).
- Run directory `app/experiments/runs/<run_id>/` contains: config snapshot, run metadata (git_sha, seed, library versions), checkpoints every K steps, eval results JSON per eval call, replays of best/worst eval episodes per round, tensorboard logs.
- Reproducing a run = `python -m barracks.train --config <run_dir>/config.json --seed <run_dir>/run_metadata.json:seed`.
- The training script refuses to start with uncommitted changes unless `--allow-dirty` is passed.

## 8. Key open questions for later barracks-grilling sessions

These were intentionally not resolved in the architecture grilling — they need their own session.

- **Action space shape variants.** Do we want a separate `head_select` head to make the (spatial vs scalar) choice explicit, or is the flattened single-`Discrete` sufficient? Trade-off: clarity vs simplicity.
- **Wait-bucket granularity.** 50/100/200 ticks — is this the right ladder? Should we add 25 ticks for fine-grained micro?
- **Observation channel ordering / consolidation.** Do we collapse the per-building-type channels into a single "type" channel with categorical encoding? Costs spatial inductive bias but saves ~12 channels.
- **Frame stacking vs LSTM vs single-frame.** Final call deferred to MVP-Tiny empirical results.
- **Curriculum specifics.** Round thresholds, base difficulty labeling, promotion criteria.
- **Reward weight tuning protocol.** How many runs per A/B, what eval metric is the optimization target during tuning sessions.
- **Hyperparameter sweep budget.** Bayesian optimization vs grid search; SB3 has tooling for both.
- **Augmentation at observation level.** Random rotation/mirror of obs at training time (separate from base mutation) for additional invariance.
