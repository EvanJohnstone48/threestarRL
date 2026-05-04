# The Sandbox — PRD

This is the per-subsystem PRD for **The Sandbox** — the simulator subsystem of threestarRL. It complements:

- `app/docs/prd.md` — the whole-project PRD (the Sandbox is one of three subsystems).
- `app/docs/technical.md` — the cross-cutting technical architecture (this PRD inherits all of §3, §4, §5 and refines them).
- `app/docs/roadmap.md` — phased work breakdown (this PRD covers Phases 0 and 1).
- `app/docs/ubiquitous-language.md` — terminology used here is canonical per that doc.

The decisions locked into this PRD were resolved in a dedicated grilling session held during Phase 0; the session transcript lives at `app/docs/agents/sessions/` for provenance.

**Pathfinding and troop/defense targeting are explicitly deferred** to a follow-up grilling session (planned to happen after the issues from this PRD have been worked through). The schema fields they consume are present in v1 but their behavior is unspecified here. Where this PRD references "deferred targeting/pathing", the implementing engineer should leave a `NotImplementedError` (with TODO marker) and a fixture-level test asserting the deferred behavior is unreachable in Phase-0/1 scope.

---

## 1. Purpose & scope

The Sandbox is a deterministic, headless simulator of Town Hall 6 attacks plus a web frontend for replay viewing and manual base authoring. It owns all game state during an attack and produces a replay artifact per attack.

**The Sandbox is the foundation for the entire research project** — it is the environment the Barracks RL subsystem trains against and the consumer for every base produced by Cartographer in v2. Correctness, determinism, and faithfulness to real Clash mechanics matter more than visual polish.

**v1 scope = Phase 0 (tracer bullet) + Phase 1 (full TH6 content + sandbox-web viewer/editor).** End of Phase 1, the Sandbox is "essentially complete" — the full TH6 entity roster, the full simulator behavior (modulo deferred pathfinding/targeting), the full editor, and the full replay viewer.

The two subsystem packages:

| Package | Path | Language |
|---|---|---|
| Sandbox-core | `app/sandbox_core/` | Python 3.12 |
| Sandbox-web | `app/sandbox_web/` | TypeScript + React + PixiJS |

---

## 2. Phasing & exit criteria

### Phase 0 — Tracer bullet
End-to-end thread proving the architecture works: deploy one Barbarian on a TH+1 Cannon base, watch it walk to the Cannon, render in the browser. Roughly 1–2 weeks.

**Phase 0 exit criteria.**
- `python -m sandbox_core.cli run --base tracer.json --plan single_barb.json --out out.json` succeeds.
- `out.json` validates against the `Replay` schema.
- `out.json` opens in sandbox-web and renders the attack visually (top-down view).
- One golden-replay fixture committed (`tracer_smoke.json`).
- CI (lint + typecheck + tests) green.
- Pathfinding/targeting are stubbed with naive placeholder behavior sufficient for this single scenario only — the real implementation is deferred.

### Phase 1 — Full TH6 sandbox + MVP-Tiny RL parallel track
Two parallel work streams. The sandbox-content track is what this PRD covers; the MVP-Tiny RL track is owned by `app/docs/barracks/`. Roughly 6–10 weeks.

**Phase 1 exit criteria (sandbox-only).**
- All TH6 entities present in `data/buildings.json`, `data/troops.json`, `data/spells.json` with stats scraped from the Clash of Clans Fan Wiki and TH-cap progression in `data/th_caps.json`.
- All five TH6 defenses (Cannon, Archer Tower, Mortar, Air Defense, Wizard Tower) implemented including projectile travel, splash mechanics, and damage application. Targeting is the deferred half — Phase 1 ships with the deferred pathing/targeting MD doc resolved into implementation, OR with the deferred-grilling-session unblocking implementation by end of Phase 1; this PRD does not commit a date.
- All six TH6 troops (Barbarian, Archer, Goblin, Giant, Wall Breaker, Wizard) implemented including their damage multipliers (Wall Breaker vs walls, Goblin vs resources). Movement and target-acquisition deferred per above.
- Lightning Spell implemented including per-tick bolt cadence, target filter (`all_except_walls`), and friendly damage.
- Six golden-replay scenarios passing (see §11).
- Sandbox-web manual editor functional: place all building types, drag-paint walls, validate, export.
- Sandbox-web replay viewer functional: top-down view always works; isometric view loads user-supplied sprites with fallback.
- Around 30 authored training bases + 5 frozen eval bases authored (any mix of editor-authored and Cartographer-ingested-then-refined).

---

## 3. Functional requirements

### 3.1 Sandbox-core (simulator)

- **FR-S1.** The simulator advances world state in fixed 100 ms ticks (10 Hz) with no randomness. Every `(base, plan)` input pair yields a bit-identical `Replay` output.
- **FR-S2.** The simulator supports the full TH6 entity roster:
  - Defenses: Cannon, Archer Tower, Mortar, Air Defense, Wizard Tower.
  - Town Hall (1 per base, building-only).
  - Clan Castle (building-only in v1; no defending troops; `cc_contents` always empty).
  - Walls (all 75 placeable as 1×1 first-class blockers).
  - Non-defense buildings: Army Camp, Barracks, Laboratory, Spell Factory, Gold Mine, Elixir Collector, Gold Storage, Elixir Storage, Builder's Hut.
  - Troops: Barbarian, Archer, Goblin, Giant, Wall Breaker, Wizard.
  - Lightning Spell.
- **FR-S3.** The simulator is fully data-driven: no hardcoded entity stats, no `if entity.type == "..."` branches in code (special behaviors expressed as data fields).
- **FR-S4.** The simulator produces a `Replay` artifact per attack: an initial `WorldState`, a per-tick stream of full `WorldState` snapshots, and per-tick `Event` lists (event types listed in §6).
- **FR-S5.** The simulator is exposed both as a Python library (importable from the Barracks RL env) and as a CLI (`python -m sandbox_core.cli run`).
- **FR-S6.** The simulator computes a final `Score`: stars (0–3), destruction percent (discrete by non-wall building count), ticks elapsed, town-hall-destroyed flag.
- **FR-S7.** The simulator supports four termination conditions evaluated each tick (any-fires, see §5.9): timer at 1800 ticks; 100% destruction; agent emits `end_attack`; attacker has nothing left to do.
- **FR-S8.** The simulator validates every `BaseLayout` and `DeploymentPlan` it consumes; invalid inputs raise typed errors.
- **FR-S9.** The simulator's hot path emits zero log statements; the `Replay` is the sole sim log.
- **FR-S10.** The simulator entity-stats loader supports a manual-overrides layer (`data/manual_overrides.json`) merged on top of scraped wiki data at sim-startup time.
- **FR-S11.** The simulator content loader supports per-level entity stats from TH1 through TH6 (data file holds all levels), with the v1 sim selecting the TH-cap level for each entity per `BaseLayout.th_level` (always 6 in v1).

### 3.2 Sandbox-web (viewer + editor)

- **FR-W1.** Sandbox-web renders `Replay` JSON in two modes: top-down (procedural colored geometry, no assets required) and isometric (user-supplied sprites with a "fit-to-screen" fallback when sprites missing).
- **FR-W2.** The replay viewer supports timeline scrubbing, play/pause, variable playback speed (0.25×–8×), and ±1-tick stepping.
- **FR-W3.** The replay viewer overlays event markers on the timeline (deploy, damage, destroyed, spell_cast, town_hall_destroyed) and shows an entity inspector when a building or troop is clicked.
- **FR-W4.** The manual editor supports placing every building type from a categorized palette, drag-painting walls, and erasing entities — with live validation feedback.
- **FR-W5.** The manual editor enforces every constraint from §5.7 in real time and refuses to export an invalid base.
- **FR-W6.** The manual editor exports a validated `BaseLayout` JSON via the browser file-save API (user manually copies into `app/data/sample_bases/`).
- **FR-W7.** The manual editor autosaves to `localStorage` between mutations and offers "continue editing the last base" on next open.
- **FR-W8.** Sandbox-web never drives simulation live — it only consumes JSON artifacts produced by sandbox-core.
- **FR-W9.** TypeScript types for all schemas are auto-generated from Pydantic models via a `make types` task; the web project never declares its own duplicate of a sim schema.

### 3.3 Content & scraper

- **FR-C1.** The content layer ships four JSON files under `app/data/`: `buildings.json`, `troops.json`, `spells.json`, `th_caps.json`. Plus an optional `data/manual_overrides.json`.
- **FR-C2.** Content data is produced by a scraper script: `python -m sandbox_core.tools.scrape_wiki`. The script is deterministic given its HTML cache; reruns produce byte-identical output unless `--refresh` is passed.
- **FR-C3.** Wiki sources are pinned in the scraper's entity-list constant: `https://clashofclans.fandom.com/wiki/<EntityName>` for each TH6 entity, and `https://clashofclans.fandom.com/wiki/Troop_Movement_Speed` for tile-per-second movement speeds.
- **FR-C4.** The scraper writes pretty-printed JSON with sorted keys (so PR diffs are reviewable) and validates its own output against the Pydantic schemas before writing.
- **FR-C5.** The runtime loader merges scraped data with `manual_overrides.json` at sim startup; the merged result is the authoritative entity catalogue for the run.

---

## 4. Acceptance criteria

### Phase 0 acceptance
- **AC-S0.1.** A user can run the CLI on the tracer base and produce a `replay.json` that validates against `Replay`.
- **AC-S0.2.** The user can drag `out.json` into sandbox-web (top-down view) and watch a Barbarian walk to the Cannon and destroy the Town Hall.
- **AC-S0.3.** Pre-commit (lint + typecheck + fast tests) and CI (full suite) pass.
- **AC-S0.4.** One golden-replay fixture (`tracer_smoke.json`) is committed and validated by the golden-replay test.

### Phase 1 acceptance
- **AC-S1.1.** The full TH6 entity roster is present in `data/{buildings,troops,spells}.json` with stats scraped from the Fan Wiki at TH-cap-for-TH6 levels (and TH1–TH5 levels also present for forward use).
- **AC-S1.2.** All TH6 mechanics minus deferred targeting/pathing are simulated correctly per §5: hitbox geometry, splash damage, projectile travel, damage multipliers, Lightning Spell, termination, scoring.
- **AC-S1.3.** Six golden-replay scenarios pass (§11.2).
- **AC-S1.4.** Defense targeting respects target filters per data: Air Defense ignores ground troops; Cannon/Mortar attack ground only; Archer Tower / Wizard Tower attack ground+air. (Targeting is deferred but the *filter respect* must be live in v1 — the deferred scope is *which target gets picked* among legal ones, not *which targets are legal*.)
- **AC-S1.5.** The sandbox-web manual editor allows the user to author and export a TH6 base in under 10 minutes.
- **AC-S1.6.** Around 30 authored training bases + 5 authored eval bases exist in `app/data/sample_bases/`. Bases may be authored from scratch in the editor, ingested via the Cartographer and refined, or any mix.
- **AC-S1.7.** A trained agent's replay (produced by the Barracks track) loads and visualizes correctly in sandbox-web.

---

## 5. Architecture decisions

These are the decisions locked in the dedicated sandbox grilling. They override the architecture-grilling notes where in conflict; e.g., the corrected grid size (50×50 outer, 44×44 buildable) supersedes the "44×44" figure in `technical.md`. The Barracks observation tensor must be updated accordingly to `(C_obs, 50, 50)`.

### 5.1 Grid geometry & coordinates
- **Total grid: 50×50.** This is the simulator's full play area, including the deploy zone.
- **Inner buildable region: 44×44.** Rows 3–46, cols 3–46. Buildings and walls only placeable here.
- **Deploy ring: 3 tiles wide on each side.** Rows 0–2, rows 47–49, cols 0–2, cols 47–49. Troops only deployable here. Spells only castable in the inner buildable region (not the deploy ring).
- **Coordinate convention.** `(row, col)` with origin `(0, 0)` at the **top-left**; `row` increases downward, `col` increases rightward (matches numpy `array[r, c]` and standard image conventions). Float positions for troops use the same axes.
- **Tile centers** at half-integer coordinates: a tile `(r, c)` has center at `(r + 0.5, c + 0.5)` in float coords.
- **Building origin** = the **top-left tile of its footprint**. A 3×3 Cannon at origin `(10, 12)` occupies tiles `(10..12, 12..14)`.
- **All TH6 footprints are square** (1×1 walls, 2×2 (none at TH6), 3×3 most defenses + storages + Spell Factory + Lab + CC, 4×4 TH + Army Camp). Schema retains `[h, w]` for forward compatibility.

### 5.2 Building placement rules
The editor and the `BaseLayout` validator enforce identical rules; the simulator may trust a validated layout.

- **Footprint disjointness.** No two buildings or walls may share any tile. Strict.
- **No mandatory spacing.** Buildings and walls may sit flush against each other.
- **Inside buildable region.** Every footprint tile must lie in `r ∈ [3, 46], c ∈ [3, 46]`.
- **Snapping.** Footprint top-left snaps to integer tile coordinates.
- **TH-cap enforcement.** Per-entity caps loaded from `data/th_caps.json` (scraped from the Town Hall wiki page). The editor disables palette items at cap; the validator rejects layouts that exceed caps.
- **Required entities.** Exactly one Town Hall. No other hard requirements (a base with zero Army Camps is legal but degenerate).
- **Decorations / obstacles / gem boxes / trees.** Out of scope; not modelled.
- **CC contents.** `cc_contents` field is always empty in v1; validator rejects non-empty.

### 5.3 Walls
- **Storage.** Each wall is a separate `BuildingPlacement` entry with `building_type: "wall"` and a 1×1 footprint at its origin tile. No compressed-segment representation.
- **Cap.** 75 walls at TH6 (from `th_caps.json`).
- **Editor UX.** Drag-paint mode (`W` shortcut): the user holds mouse-down on a tile and drags; walls paint along the orthogonal line. Non-axial drags resolve to L-shapes. Painting over an existing wall is idempotent. Eraser tool (`E` shortcut) removes any building or wall.
- **Wall HP and damage rules:**
  - Walls take normal damage from troop attacks (1× by default, per §5.5 multipliers).
  - **Wall Breaker suicide damages walls** (full damage to target wall + splash to nearby walls per the WB's `splash_radius`).
  - **Lightning Spell does NOT damage walls.** (`SpellType.damages_walls: false`.)
  - **Wizard's regular ranged attack splash damages walls.** (Wizard is an attacker; full damage to walls in radius.)
  - **Defense splash (Mortar, Wizard Tower) does NOT damage walls.** Defense splash is troop-only.
  - These rules are encoded as `splash_damages_walls: bool` on each splash producer + `damages_walls: bool` on `SpellType`.

### 5.4 Hitbox model
The hitbox is the geometric region used for *targeting* (i.e., the region a troop must be in range of to attack the building). It is smaller than the footprint — a small "moat" of footprint tiles is walkable and unattackable around each non-wall building.

- **Schema field.** `BuildingType.hitbox_inset: float | null` (per entity). `null` resolves to the default rule at load time; the in-memory `BuildingType` always carries an explicit float so combat code never branches on entity name.
- **Default rule.** `hitbox_inset = max(footprint_size / 2 − 0.5, 0.5)`.
  - 1×1 (wall): inset 0.5 (the full tile is the hitbox).
  - 2×2: inset 0.5.
  - 3×3: inset 1.0.
  - 4×4: inset 1.5.
- **Override.** Army Camp (4×4) overrides to inset 1.0.
- **Hitbox shape is attacker-dependent.** For ground attackers, the hitbox is a **square** (footprint shrunk by `hitbox_inset` per side). For air attackers, the hitbox is a **circle** (radius = `hitbox_inset`, centered on footprint center). The "why" is part of the deferred targeting design.
- **Walls.** A wall's footprint = its hitbox = 1×1 (a wall fills the full tile). Troops cannot squeeze through a wall-and-building corner.
- **Implication.** Two adjacent non-wall buildings have hitboxes that don't touch — a 1-tile-wide walkable corridor exists between their hitbox edges. Pathfinding consumes this (deferred); building placement must not assume hitbox-adjacency means "no walk-through".

### 5.5 Damage application & multipliers
Damage application is the act of subtracting HP from a target on impact. Targeting (which target?) is deferred; damage application (how much, given a target?) is locked here.

- **Building category enum** (closed at v1): `town_hall`, `clan_castle`, `defense`, `wall`, `resource_collector`, `resource_storage`, `army`, `builder_hut`. Drives multiplier lookup, palette grouping, and (downstream) per-building reward weights.
- **Multiplier schema on TroopType:** `damage_multipliers: dict[category, float]` (default `{}`) plus `damage_multiplier_default: float = 1.0`.
- **Damage formula:** `damage_dealt = troop.base_damage_at_level × troop.damage_multipliers.get(target.category, troop.damage_multiplier_default)`.
- **Wall Breaker:** `base_damage` set to the wiki's wall-damage value; `damage_multipliers: {"wall": 1.0}`; `damage_multiplier_default: ~0.04` (i.e., ~4% to non-walls — refined from real-game values during scraper review).
- **Goblin:** `damage_multipliers: {"resource_collector": 2.0, "resource_storage": 2.0}`; `damage_multiplier_default: 1.0`.
- **All other TH6 troops:** empty multipliers dict, default 1.0.
- **Defenses do not have multipliers.** They apply flat `damage_per_shot` to troops.
- **No friendly-troop damage** from attacker splash (Wizard's splash does not hit friendly troops). Hard sim invariant, not a tunable.

### 5.6 Projectile mechanics
Damage propagation between attack-trigger and target HP change.

- **Model.** Distance-proportional travel time. Each ranged attacker has `projectile_speed_tiles_per_sec: float | null`. Travel time = `distance_tiles / speed × 10` ticks. `null` means instant hit (melee, suicide, Lightning).
- **Starter values** (hand-curated; refined during balance sessions):
  - Cannon ≈ 20 tiles/sec (near-instant).
  - Archer Tower ≈ 10.
  - Mortar ≈ 3 (slow arc — strategic mechanic).
  - Air Defense ≈ 10.
  - Wizard Tower ≈ 6.
  - Archer (troop) ≈ 10. Wizard (troop) ≈ 6.
  - Barbarian / Goblin / Giant / Wall Breaker → `null`.
- **Homing flag.** `BuildingType.projectile_homing: bool` and `TroopType.projectile_homing: bool`.
  - Single-target ranged attackers (Cannon, Archer Tower, Wizard Tower, Air Defense, Archer, Wizard): `homing: true`. The projectile tracks the target until impact. If the target dies mid-flight, the projectile despawns and does no damage.
  - Mortar: `homing: false`. The Mortar commits to an `impact_position` at fire time (target's hitbox center snapped to nearest tile center). On impact, splash applies in radius regardless of whether the original target survives. This is the real-Clash "dodge a Mortar" mechanic.
- **In-flight projectile representation.** A `Projectile` model in `WorldState` tracks `attacker_id`, `target_id`, `attacker_position`, `current_position`, `impact_position`, `damage`, `splash_radius_tiles`, `splash_damages_walls`, `ticks_to_impact`, `attack_kind`. Each tick advances `current_position` along the attack→impact line. On `ticks_to_impact == 0`, the hit resolves and a `damage` event emits.
- **Attack-cooldown semantics.** When an attacker acquires a target, it fires immediately (cooldown timer starts at zero). Subsequent attacks elapse `attack_cooldown_ticks`. If the target dies between trigger and impact (homing case), no damage is applied; cooldown still elapses normally.

### 5.7 Splash mechanics
- **Shape: circular.** Any entity whose hitbox intersects the splash circle takes damage.
- **Falloff: none.** Flat full damage within radius, zero outside. No linear/quadratic falloff in v1.
- **Splash center:**
  - Mortar (non-homing): `impact_position` committed at fire time.
  - Wizard / Wizard Tower / other homing splashers: target's hitbox center on impact tick.
  - Wall Breaker suicide: WB's float position the tick the suicide triggers.
- **Distance metric for splash:** Euclidean from splash center to (a) the closest point on each building's **square hitbox** (always-square for splash distance — independent of attacker type), or (b) each troop's float position. If distance ≤ `splash_radius`, damage applies (subject to filter).
- **Friendly-fire model.** Defense-source splash hits attacking troops only (no other defenses). Attacker-source splash (Wizard) hits buildings + walls (filter-permitting) + does NOT hit friendly troops.
- **Wizard Tower (defense) splash damages only troops.** Never damages other buildings or walls.

### 5.8 Lightning Spell
- **Cast mechanics.** Agent emits `kind: "spell", entity_type: "lightning", position: (r, c)` at decision-point tick `T`. On tick `T`, a `SpellCast` entity is created in `WorldState` with `cast_tick=T`, `center=(r, c)` (tile center), `bolts_remaining=N`, `next_bolt_tick=T+1`. Each bolt fires per `hit_interval_ticks`, applies `damage_per_hit` to every entity in radius, emits a `bolt_struck` event, and decrements `bolts_remaining`. When zero, the SpellCast despawns.
- **Per-level stats** in `spells.json`:
  - `radius_tiles: 2.0` (approximate; scraper authoritative).
  - `hit_interval_ticks: 1`.
  - `num_hits: 11` (constant across levels at TH6 max).
  - `damages_walls: false`.
  - `target_filter: "all_except_walls"` (ground troops, air troops, all buildings except walls).
  - `housing_space: 1`.
  - `levels[]`: per-level damage_per_hit values (level 1, 2, 3 at TH6-cap).
- **Friendly damage.** Lightning DOES damage friendly troops in radius (matches real game).
- **Spell capacity at TH6.** `th_caps.json` declares `spell_capacity_total: 2`. The action mask zeroes out spell casts when remaining capacity is 0.
- **Cast position legality.** Inner buildable region only (rows 3–46, cols 3–46); not in deploy ring.

### 5.9 Termination & scoring
- **Termination conditions** (any-fires):
  1. Tick ≥ 1800 (3-minute timer at 10 Hz).
  2. 100% destruction (every non-wall building destroyed).
  3. Agent emits `end_attack` scalar action.
  4. No further attack potential: all deployed troops dead AND troops_remaining_in_camps == 0 AND spells_remaining == 0 AND no in-flight projectiles.
- **Star thresholds** (matches real Clash, computed at terminal tick only):
  - 1 star if `destruction_pct ≥ 50`.
  - +1 star if `town_hall_destroyed`.
  - +1 star if `destruction_pct ≥ 100`.
- **Destruction percent.** Discrete per-building, walls excluded:
  `destruction_pct = (count of destroyed non-wall buildings / total non-wall buildings) × 100`.
  TH counts as one ordinary building. A building is destroyed when its HP ≤ 0 (latched). Partial HP loss does not count.
- **Town-hall-destroyed flag.** Set true the tick the TH building's HP reaches 0; latched.
- **`Score` schema** (computed each tick; only `stars` is non-zero on the terminal tick): `stars: int (0..3)`, `destruction_pct: float (0..100)`, `ticks_elapsed: int`, `town_hall_destroyed: bool`.

---

## 6. Data contracts

All Pydantic models live in `app/sandbox_core/schemas.py` per `technical.md` §4. TypeScript types are auto-generated from these. Every persisted JSON has a `schema_version: int = 1` field; migrations live in `schemas.py` per `technical.md` §4.4.

### 6.1 Static content schemas
Three multi-level types loaded once at sim startup and exposed as immutable singletons via `sandbox_core.content`:

- **BuildingType** — type-level fields (`category`, `footprint`, `hitbox_inset`, `target_filter`, `splash_radius_tiles`, `splash_damages_walls`, `min_range_tiles`, `projectile_speed_tiles_per_sec`, `projectile_homing`, `is_wall`, `damages_walls_on_suicide`) plus a `levels: list[BuildingLevelStats]` where each entry has `level`, `hp`, `damage_per_shot`, `range_tiles`, `attack_cooldown_ticks`, and `unlocked_at_th`.
- **TroopType** — type-level fields (`category`, `footprint`, `hitbox_radius_tiles`, `housing_space`, `speed_tiles_per_sec`, `target_filter`, `target_preference`, `splash_radius_tiles`, `splash_damages_walls`, `projectile_speed_tiles_per_sec`, `projectile_homing`, `damages_walls_on_suicide`, `damage_multipliers`, `damage_multiplier_default`) plus `levels: list[TroopLevelStats]` (`level`, `hp`, `base_damage`, `range_tiles`, `attack_cooldown_ticks`, `unlocked_at_th`). The `target_preference` field is schema-present but its value-meaning is part of the deferred grilling.
- **SpellType** — type-level fields (`category`, `radius_tiles`, `hit_interval_ticks`, `num_hits`, `damages_walls`, `target_filter`, `housing_space`) plus `levels: list[SpellLevelStats]` (`level`, `damage_per_hit`, `unlocked_at_th`).

### 6.2 TH-caps file
`data/th_caps.json` keyed by TH level, mapping each entity name to the cap level allowed at that TH (and special caps like `spell_capacity_total` and per-building count caps such as `cannon_count: 4`). The v1 sim selects rows from each entity using the TH-level-cap entries when instantiating a base.

### 6.3 BaseLayout, DeploymentPlan, Replay
- **BaseLayout** — `schema_version`, `metadata` (name, th_level, tags free-form, notes, author, created_at), `th_level: int`, `placements: list[BuildingPlacement]` (each = `{building_type: str, origin: [r, c], level: int | null}`), `cc_contents: list[str]` (always empty in v1).
- **DeploymentPlan** — `schema_version`, `metadata`, `actions: list[DeploymentAction]`. Each action: `{tick: int, kind: "deploy_troop" | "cast_spell", entity_type: str, position: [r, c]}`. No `wait` or `end_attack` kinds — those are env-only concerns.
- **Replay** — `schema_version`, `metadata` (sim_version, base_name, plan_name, run_id, episode_id, total_ticks, final_score, started_at, git_sha, config_hash), `initial_state: WorldState`, `frames: list[TickFrame]`.
- **TickFrame** — `tick: int`, `state: WorldState`, `events: list[Event]`.
- **WorldState** — buildings, troops, projectiles, spells (in-flight), score, tick.

### 6.4 Event types
Phase 0/1 events: `deploy`, `spell_cast`, `bolt_struck`, `attack_start`, `projectile_fired`, `damage`, `destroyed`, `end_attack`, `sim_terminated`.

Deferred to the targeting/pathing grilling (schema-present, unemitted in Phase 0/1): `target_acquired`, `target_lost`, `attack_end`.

Each event is `{type: str, tick: int, payload: dict}`.

### 6.5 Float precision in serialized replays
All `(rf, cf)` floats round to **3 decimal places** before serialization. `config_hash` is computed over the **rounded** values; the hash is therefore stable across float-noise.

### 6.6 Replay JSON encoding
- **Default mode: minified** (no whitespace, single line). Used by the sim, viewer, and RL env.
- **Pretty mode** with stable key ordering, used for committed golden-replay fixtures so `git diff` is reviewable.
- The reader handles both transparently.

### 6.7 `config_hash`
SHA-256 over the canonicalized JSON of the inputs that determine sim output: `base.json` + `plan.json` + `buildings.json` + `troops.json` + `spells.json` + `manual_overrides.json`. Two replays with identical `config_hash` *must* be bit-identical. The hash is the foundation of golden-replay tests and determinism regression detection.

### 6.8 `sim_version` vs `schema_version`
- `schema_version` — on-disk JSON contract. Frozen at v1.
- `sim_version` — `pyproject.toml` package version. Bumped on any change to simulator behavior. Recorded in `Replay.metadata.sim_version`. Golden-replay tests record the `sim_version` at fixture-creation time; running a different `sim_version` against the same `(base, plan)` may produce a different replay — the test framework either updates the golden via `--update-golden` or fails loudly.

---

## 7. Sandbox-core architecture

### 7.1 The `Sim` class
Public API per `technical.md` §5.1, refined here:

- `Sim(base: BaseLayout, deployment_plan: DeploymentPlan | None = None) -> Sim`
- `Sim.reset() -> WorldState` — returns to initial state, clears the replay buffer; used by the RL env between episodes.
- `Sim.step_tick() -> tuple[WorldState, list[Event]]` — advances one tick; raises `SimTerminatedError` if already terminal.
- `Sim.advance_to(target_tick: int) -> list[TickFrame]` — convenience for fast-forward; raises `ValueError` if `target_tick < current_tick`.
- `Sim.schedule_deployment(action: DeploymentAction) -> None` — used by the RL env (and by CLI internally to apply `DeploymentPlan` actions); raises `SimTerminatedError` after termination, `InvalidDeploymentError` on validation failure.
- `Sim.is_terminal() -> bool`.
- `Sim.score() -> Score`.
- `Sim.to_replay() -> Replay` — produces the full replay artifact; only valid after termination.

The `Sim` is reusable across episodes within one process via `reset()`. Vec-env workers each hold their own `Sim`.

### 7.2 Per-tick update order
Locked per `technical.md` §3 plus refinements from this PRD:

1. Resolve in-flight projectiles → impact events; if homing target died, despawn projectile silently.
2. Apply scheduled deployments queued for this tick (including spell casts, which spawn `SpellCast` entities).
3. Tick active spell casts (Lightning bolts).
4. Update troop targeting (re-pick on target death). **[Deferred — Phase 0 stub]**
5. Advance troop positions one substep along their cached path. **[Deferred — Phase 0 stub]**
6. Troops attack in range with cooldown ready; create projectiles (or apply melee damage instantly).
7. Update defense targeting. **[Deferred — Phase 0 stub]**
8. Defenses attack in range with cooldown ready; create projectiles.
9. Apply accumulated damage events; mark destroyed; emit `destroyed` events.
10. Update score (stars, % destruction).
11. Emit `sim_terminated` if termination condition fires.
12. Increment `tick`.

### 7.3 Module boundaries
- **`sim.py`** — owns `Sim`, the per-tick update orchestration, the world state. Thin glue.
- **`combat.py`** — pure functional damage application: `apply_damage(target, base_damage, attacker, multipliers) → damage_event`. No state.
- **`splash.py`** — pure functional splash resolution: `resolve_splash(world, center, radius, damage, filter, source_kind) → list[damage_event]`. No state.
- **`scoring.py`** — pure functional scoring: `compute_score(world) → Score` and `is_terminal(world) → bool`. No state.
- **`grid.py`** — tile + footprint helpers, perimeter/buildable region masks, hitbox geometry. Square inset and circular hitbox helpers both live here.
- **`pathfinding.py`** — **[Deferred]**. Stubs raise `NotImplementedError("path: pathfinding deferred — see app/docs/sandbox/")`.
- **`projectile.py`, `spell.py`, `building.py`, `troop.py`** — runtime entity types; mostly data carriers with minimal behavior on them (behavior lives in pure-functional helpers).
- **`replay.py`** — writer (incl. float rounding, hash, minified/pretty mode) and reader (incl. schema migration).
- **`content.py`** — loads the four data JSONs + `manual_overrides.json` at startup; merges; exposes immutable singletons.
- **`schemas.py`** — every Pydantic v2 model.
- **`cli.py`** — `run`, `validate`, `validate-plan`, `inspect-replay` subcommands.
- **`tools/scrape_wiki.py`** — separate dev-time tool, never imported by runtime code.

### 7.4 Tie-break canonical ordering
| Operation | Tie-break |
|---|---|
| Defense picks among multiple in-range troops (deferred mechanic, but ordering rule locked) | Lowest `troop.id` |
| Splash damage application order | Iterate by `target.id` ascending |
| Deployment order on the same tick | `DeploymentPlan.actions[]` order; for env-injected actions, FIFO insertion order |
| Multiple buildings destroyed in same tick | Events ordered by `building.id` ascending |
| Building ID assignment | Order in `BaseLayout.placements[]` → IDs `0..N-1` |
| Troop ID assignment | Monotonic counter starting at `len(buildings)`, incremented per `schedule_deployment` |

### 7.5 Sim API edge cases
- `step_tick()` after `is_terminal()` → `SimTerminatedError`.
- `schedule_deployment()` after termination → `SimTerminatedError`.
- `schedule_deployment()` with invalid action → `InvalidDeploymentError`.
- `advance_to(t)` with `t < current_tick` → `ValueError`.
- Loading a `Replay` that fails Pydantic validation → `ReplayValidationError`.

---

## 8. Sandbox-web specifics

### 8.1 Dual-view rendering
- **Top-down view (default).** Each tile is a 32×32 px axis-aligned square. Buildings render as colored rectangles with text labels (e.g., "C6" for a level-6 Cannon). Troops render as colored circles with single-letter labels. HP bars overlaid. No assets needed. Always works.
- **Isometric view.** 2:1 dimetric projection (each tile 64×32 px diamond). User-supplied sprites loaded from `app/sandbox_web/public/sprites/`. Missing sprites fall back to a magenta placeholder + entity name overlay.
- **Toggle.** `V` key cycles `top-down → iso → top-down`. Default = top-down. Iso requires at least one successfully-loaded sprite.
- **Persistence.** Selected view saved to `localStorage` per browser.

### 8.2 Iso projection spec (for asset generation)
- 2:1 dimetric, 64 px wide × 32 px tall per tile.
- Grid origin `(0, 0)` rendered at top of screen; row+ goes down-left, col+ goes down-right; visual "south" = `+row +col`.
- Pixel formula: `screen_x = (col − row) × 32 + canvas_center_x`; `screen_y = (col + row) × 16`.
- Sprite anchor: bottom-center pixel of sprite canvas pinned to the bottom corner of the building's footprint diamond on screen.
- Sprite canvas sizing: 1×1 → 64×64 px; 2×2 → 128×96; 3×3 → 192×144; 4×4 → 256×192. Troops: 48×64. Effects: 96×96. Terrain: 64×32 diamond.
- Format: PNG with alpha. Single-frame static (animations are Phase 2+). Light source from upper-left if shadows are baked.

### 8.3 Sprite directory layout
```
app/sandbox_web/public/sprites/
  buildings/    # one PNG per entity name (snake_case.png), no level suffixes in v1
  troops/
  spells/
  effects/      # explosion, bolt, splash
  terrain/      # grass, deploy_zone tile
```

The loader attempts to load every expected sprite at app start; missing sprites fall back per §8.1.

### 8.4 Renderer behavior
- **Render rate.** 60 fps Pixi ticker.
- **Interpolation.** Troop and projectile positions interpolated linearly between consecutive `TickFrame`s (6 render frames per tick at 60 fps / 10 Hz). Buildings static. HP bars update once per tick, no interp.
- **Camera.** Initial fit-to-grid; pan via click-drag; zoom 0.25×–4× via mouse wheel (centered on cursor); reset button.
- **HP bars.** Hidden at full HP, visible when damaged. 24×4 px for buildings, 16×3 px for troops, green→yellow→red.

### 8.5 Replay viewer
- **Loading paths.** Drag-drop `replay.json` onto the canvas; "Load replay…" file-picker button; URL parameter `?replay=<path>` for static-served replays.
- **Cross-version playback.** Loading a replay with `sim_version != current` shows a banner: `"Replay sim_version X.Y.Z loaded under runtime A.B.C — playback only"`. The viewer plays it as recorded; no re-simulation.
- **Playback controls (bottom toolbar).** Play/pause, scrub bar with current-tick marker, speed selector (0.25×, 0.5×, 1×, 2×, 4×, 8×), step ±1 tick buttons, tick counter `0123 / 1800`.
- **Event highlights on timeline.** Colored ticks below the scrubber (deploy=green, damage=yellow, destroyed=red, spell_cast=purple, town_hall_destroyed=gold). Hover-tooltip with event details.
- **Entity inspector.** Click a building or troop → side panel shows type, level, HP/maxHP, position, current target (when applicable), per-entity stats from the loaded content.

### 8.6 Editor
- **Layout.** Three-panel: palette (left), 50×50 grid (center, rendered in active view mode), validation + metadata (right).
- **Palette.** Entities grouped by category (Defenses, Resources, Army, Walls, Town Hall). Each shows count placed / TH6 cap. Disabled at cap.
- **Placement workflow.** Click palette item → "place" mode → hover ghost (green if legal, red if illegal) → click tile → place. `Esc` cancels.
- **Wall paint.** `W` shortcut → drag-paint orthogonal lines with L-shape on non-axial drags. Idempotent over existing walls.
- **Erase.** `E` shortcut → click any building/wall to remove. Right-click on a placed building shows context menu: erase / copy / inspect.
- **Validation panel.** Live-updating list of constraints: TH placed ✓, walls X/75, no overlap, all in buildable region, total building count. Failed entries are clickable and highlight conflicting tiles.
- **Metadata fields (right panel).** `name`, `tags` (free-form), `notes`, `author`, `created_at` auto-populated. Required for export.
- **Export.** "Export base.json" downloads the validated `BaseLayout` JSON via the browser file-save API. User manually copies into `app/data/sample_bases/`.
- **Import.** "Open base.json" loads an existing layout for editing.
- **Autosave.** `localStorage` per browser; "continue editing the last base?" prompt on next open.
- **Undo / redo.** `Ctrl+Z` / `Ctrl+Shift+Z`. 50-step history. History stored as full placement-list snapshots per step.
- **Quality-of-life (may defer to post-Phase-1 if needed).** Mass-clear, mirror horizontal/vertical, rotate 90°.

---

## 9. Wiki scraper

### 9.1 Sources (locked)
- Per-entity: `https://clashofclans.fandom.com/wiki/<EntityName>` (e.g., `Cannon`, `Town_Hall`, `Barbarian`, `Lightning_Spell`). The infobox provides static fields (footprint, target filter, housing space, etc.); the per-level table provides level-varying fields (HP, damage, range, cooldown).
- Movement speed: `https://clashofclans.fandom.com/wiki/Troop_Movement_Speed`. Tile-per-second floats; conversion to tiles/tick is `tiles_per_sec / 10`.

### 9.2 CLI surface
```
python -m sandbox_core.tools.scrape_wiki \
  --out app/data/ \
  [--refresh] [--only buildings|troops|spells|caps|all] [--cache-dir app/data/.wiki_cache]
```

### 9.3 Cache & idempotency
- HTML cache at `app/data/.wiki_cache/<entity>.html` (gitignored).
- First run downloads + caches; subsequent runs read cache; `--refresh` re-downloads.
- A `.metadata.json` per page records `{url, etag, last_modified, sha256, scraped_at}` for traceability.
- Output JSON is deterministic given the cache. Re-running with the same cache produces byte-identical output.

### 9.4 Output contract
- Four files: `data/buildings.json`, `data/troops.json`, `data/spells.json`, `data/th_caps.json`.
- Each output validates against its Pydantic schema before write; refuses to overwrite an existing file with output that fails validation.
- Pretty-printed, sorted keys, UTF-8.
- Optional manual overlay: `data/manual_overrides.json`. Authored by hand. Loader merge order at sim startup: `wiki scrape → manual_overrides → final BuildingType / TroopType / SpellType objects`. The merge happens once per sim startup; the scrape itself is a separate offline tool.

### 9.5 Stat-name normalization
Scraper has a `COLUMN_NORMALIZATIONS` map handling wiki header inconsistencies (e.g., `"Damage per Hit"`, `"Damage per Shot"`, `"Damage per Attack"` all → `damage_per_shot`). `Attack Speed` in seconds converts to `attack_cooldown_ticks` via `round(seconds × 10)`. `DPS` is dropped (derivable).

### 9.6 Defensive parsing
The parser logs warnings (not errors) when expected fields are missing from a wiki page; missing fields fall back to `null` in scrape output. The hand-curated `manual_overrides.json` is the gap-filling layer. The scraper-output validator catches missing-required cases.

### 9.7 Entity list
Hard-coded in the script:
- **Buildings:** Town Hall, Cannon, Archer Tower, Mortar, Air Defense, Wizard Tower, Clan Castle, Wall, Army Camp, Barracks, Laboratory, Spell Factory, Gold Mine, Elixir Collector, Gold Storage, Elixir Storage, Builder's Hut.
- **Troops:** Barbarian, Archer, Goblin, Giant, Wall Breaker, Wizard.
- **Spells:** Lightning Spell.

Adding an entity at TH7+ = appending to this list and re-scraping.

---

## 10. Sample-base authoring conventions

### 10.1 File layout
```
app/data/sample_bases/
  tracer.json                  # Phase 0 / MVP-Tiny
  base_01.json … base_30.json  # MVP-Real training set
  eval_01.json … eval_05.json  # frozen held-out
```
Names are stable; never renumbered post-commit.

### 10.2 BaseLayout metadata fields (required)
- `name: str`
- `th_level: int` (= 6 in v1)
- `tags: list[str]` (free-form; e.g., `["compartmentalized", "war-base"]`)
- `notes: str | null`
- `author: str`
- `created_at: str` (ISO 8601 UTC)

There is no `difficulty` field. Curriculum sequencing in barracks-land is configured by enumerating filenames per round, not by reading metadata.

### 10.3 Authoring guidelines
A short companion doc at `app/data/sample_bases/AUTHORING.md` describing variety guidance (avoid all-clustered-corner bases, aim for typical TH6 layouts spanning compound-TH / war-base / farming-base styles, eval bases authored first and never modified).

### 10.4 Eval-set discipline
The 5 eval bases are read-only by convention. No pre-commit hook enforces this in v1; if the convention is broken in practice, a hook can be added later.

### 10.5 Validator
The `BaseLayout` validator in `schemas.py` enforces the naming pattern when loading from `app/data/sample_bases/` (regex `(tracer|base_\d{2}|eval_\d{2})\.json`). Loading from elsewhere (e.g., editor exports during authoring) relaxes the rule.

---

## 11. Testing strategy

### 11.1 Test pyramid
- **Unit tests (`tests/unit/sandbox_core/`).** Pure-function tests for `combat.py`, `splash.py`, `scoring.py`, `grid.py`, `replay.py` (round-trip), `content.py` (load + merge), schema validators. Run in milliseconds; on every commit via pre-commit (see `technical.md` §10.1).
- **Property tests (`tests/unit/sandbox_core/test_invariants.py`).** Hypothesis-driven invariants from `technical.md` §9.2:
  - Total destruction percent monotonically non-decreasing across `step_tick()` sequences.
  - No troop occupies a non-buildable tile (deferred mechanic; placeholder test until pathfinding lands).
  - No two buildings overlap in footprint.
  - Score reported by `Sim` matches a from-scratch recompute over the current `WorldState`.
- **Golden-replay tests (`tests/golden/replays/`).** See §11.2.
- **Integration tests (`tests/integration/`).** Full episode through Barracks env (deferred to barracks); replay round-trip (read-after-write equivalence).
- **Smoke training test.** Owned by barracks; outside the Sandbox PRD.

### 11.2 Golden-replay coverage
Frozen `(base.json, plan.json) → expected_replay.json` fixtures committed under `tests/golden/replays/`:

- **Phase 0:**
  - `tracer_smoke.json` — tracer base + single Barbarian deploy. Walks to TH, destroys it.
- **Phase 1:**
  - `mortar_splash.json` — base with one Mortar; cluster of Barbarians; Mortar splash kills 3+.
  - `wall_breaker_breach.json` — walls around a Cannon; WB breaches; Goblin walks through opening to attack a resource.
  - `wizard_splash_walls.json` — Wizard attacking a building behind a wall; walls in splash radius take damage.
  - `lightning_destroys_mortar.json` — low-HP Mortar; Lightning cast; Mortar destroyed.
  - `full_th6_attack.json` — full TH6 base, full troop roster + 1 Lightning, scripted attack reaching ≥50% destruction.

Targeting/pathing-related goldens (e.g., archer attack-position rule) get added in the deferred grilling.

### 11.3 Golden update workflow
- `pytest tests/golden/replays/` runs each scenario, regenerates the replay in memory, diffs against committed.
- On mismatch: test fails with a structured tile-by-tile diff (first 50 differing fields).
- `pytest --update-golden tests/golden/replays/` overwrites committed goldens. The diff is part of the PR. A pre-commit warning (not block) flags golden updates whose commit message lacks a `[golden-update]` tag.

### 11.4 Determinism regression test
`tests/integration/test_replay_determinism.py`: runs the same `(base, plan)` twice, asserts byte-identical replays. Catches non-determinism introduced by accidental dict-iteration-order dependencies, RNG slips, etc.

### 11.5 Schema migration tests
For each schema, `tests/golden/migrations/<schema>_v1.json` exists; CI loads through the migration chain (currently a no-op at v1) and asserts the result validates against the latest schema. Future v2 migrations get tests added at write time.

### 11.6 Modules called out for isolated testing
The deep modules — `combat.py`, `splash.py`, `scoring.py`, `grid.py` — get the most unit-test surface. Their interfaces are pure-functional and stable; they encapsulate the trickiest logic.

The renderer's iso-projection helpers also get pure-function unit tests (Vitest or Jest on the TS side): `gridToScreen(r, c)`, `screenToGrid(x, y)`.

---

## 12. Performance budgets & determinism

### 12.1 Performance (single-core, pure Python)
- Sandbox-core, MVP-Tiny attack: **≥100 episodes/sec**.
- Sandbox-core, full TH6 attack: **≥50 episodes/sec**.
- Sim startup time (loader + content merge + base validation): **≤100 ms**.
- Replay file size, full TH6 attack: **≤3 MB** pretty / **≤1.5 MB** minified.
- Replay in-memory during sim: **≤50 MB** peak per worker.
- Web frontend: **60 fps** interpolated playback on commodity hardware.

If profiling shows the inner loop blocks training throughput, escalation order: (1) pure-Python micro-optimizations (avoid dict lookups in tick loop, pre-resolve stats), (2) `numba.jit` on `step_tick` inner pieces, (3) `numpy`-vectorize splash/distance checks, (4) Cython or Rust port (Phase 2.5+ only).

### 12.2 Determinism
- No RNG anywhere in the simulator. Tie-breaks via canonical ordering (§7.4).
- `Replay.metadata.config_hash` is the determinism oracle: identical `config_hash` ⇒ bit-identical replays.
- Determinism regression test in CI (§11.4).
- Float-rounding to 3 decimals before serialization removes float-noise from the determinism surface.

### 12.3 Schema versioning
- `schema_version: 1` is frozen across v1.
- Additive-only changes (new optional fields, new optional enum values) carry forward without bump.
- Breaking changes bump the version and ship a migration in `schemas.py`.
- Migration tests in CI (§11.5).

---

## 13. Deferred to follow-up grilling

Out of scope **for this PRD only**, in scope **for Phase 1 overall** via a follow-up grilling session. The user will author an MD doc describing the rules; that doc plus its grilling will produce the design for the implementing engineer.

### 13.1 Pathfinding
- Pathfinding algorithm choice (A* with diagonals at √2 cost is the working assumption per `technical.md` §5.2, but the per-troop quirks may require refinement).
- Diagonal-corner blocking when walls fence diagonally adjacent tiles (real-game allows or blocks this — TBD).
- Path-cache invalidation triggers (target death, wall break, target re-acquisition).
- Per-troop movement quirks (e.g., the "perpendicular tile" attack-position rule for ranged troops, which the user flagged for the deferred grilling).

### 13.2 Troop targeting & defense targeting
- Target acquisition logic per troop type (Goblin → resources, Giant → defenses, Wall Breaker → walls, Barbarian/Archer/Wizard → nearest valid).
- Defense targeting selection rules among multiple in-range troops.
- Re-targeting cadence (every tick? on target death only? on event?).
- The `target_preference` and `target_filter` schema fields stay schema-present in v1 with documented values; the deferred grilling fills in the consuming behavior.
- The hitbox shape switch (square for ground attackers, circle for air attackers) — geometric semantics defined here; their use at attack time is part of the deferred targeting rules.

### 13.3 Phase 0 placeholder behavior
For Phase 0 specifically (the tracer bullet), pathfinding/targeting use naive placeholders sufficient to ship the tracer scenario:
- Single-target straight-line walk toward the nearest non-wall building.
- Melee attack on hitbox-adjacency.
- Defenses: nearest-troop-in-range with no preference.

These placeholders are documented as TODOs and replaced wholesale once the deferred grilling produces the real spec.

---

## 14. Out of scope (v1)

**Project-wide out-of-scope** (per `app/docs/prd.md` §9): multiplayer, war, leagues, Builder Base, non-TH6 levels, Supercell-IP assets (sprites must come from user folder), mobile app, networked play.

**Sandbox-specific out-of-scope (v1):**
- Heroes (King at TH7, Queen at TH9). Schema-empty fields stay reserved.
- Air units and active anti-air mechanics. Air Defense exists with HP only; no air troops trigger it.
- Filled Clan Castle with defending troops. CC is building-only.
- Stochastic mechanics or seeded RNG inside the sim.
- Live in-browser interactive attacks (replay viewer only; manual attacks via Python CLI).
- Decorations / obstacles / gem boxes / trees.
- Hero abilities (active cooldown skills).
- Multi-frame sprite animations (single-frame static in v1).
- Hero healing / persistent state across attacks.
- Per-entity sprite level variants (one sprite per type regardless of level in v1).
- Procedural base generation (deferred to Phase 2.8 escalation only if MVP-Real overfits).
- Mutation pipeline (rotate, mirror, jitter, wall-edits) — deferred to Phase 2.4.
- Sandbox-side reward computation. Reward lives in `barracks/reward.py`; the Sandbox is reward-blind.
- Live IPC. All inter-subsystem communication via on-disk JSON.

---

## 15. Risks & mitigations

- **R-S1. Wiki HTML structure changes mid-Phase-1.** *Mitigation:* the scraper's HTML cache is committed (or at least its content hashes are tracked); a cache-rebuild reveals the change; defensive parser falls back on known-good cache when the new fetch fails to validate.
- **R-S2. Manual base authoring takes longer than anticipated.** *Mitigation:* the editor's mirror/rotate/clear quality-of-life features (deferrable) substantially speed authoring. The 30-base target is a goal, not a gate — fewer bases just means a smaller training distribution for the MVP-Real run, with the 5 eval bases remaining the immutable measurement ruler.
- **R-S3. Pathfinding/targeting deferred grilling produces a spec that requires schema changes.** *Mitigation:* the schema fields consumed by targeting (`target_filter`, `target_preference`, `hitbox_inset`, `damage_multipliers`, `damages_walls_on_suicide`) are all *present* in v1 with documented defaults. The deferred grilling adds *behavior*, not new fields. If new fields are required, additive-only changes don't bump the schema version.
- **R-S4. Sandbox-web iso renderer reveals an asset-pipeline problem (sprites don't align).** *Mitigation:* the top-down view is the primary workhorse for debugging the sim; iso is visual polish. If sprite alignment proves intractable, top-down ships and iso slips to Phase 2 without blocking the milestone.
- **R-S5. Determinism breaks silently.** *Mitigation:* the determinism-regression test (§11.4) plus golden-replay tests (§11.2) catch any byte-level divergence on every CI run.
- **R-S6. Replay file sizes balloon.** *Mitigation:* float-rounding to 3 decimals + minified default mode keep typical full-TH6 replays under 1.5 MB. If TH7+ content blows this budget, the schema's optional `state_delta` field (per `technical.md` §4.5) lets us switch to deltas.
- **R-S7. Sim throughput falls below 50 ep/sec on full TH6.** *Mitigation:* the optimization escalation ladder in §12.1.

---

## 16. Cross-references

- `app/docs/prd.md` — whole-project PRD (this PRD elaborates §5.1).
- `app/docs/technical.md` — cross-cutting technical architecture.
- `app/docs/roadmap.md` — phasing context (this PRD covers Phases 0 + 1 of the Sandbox).
- `app/docs/ubiquitous-language.md` — terminology.
- `app/docs/agents/sessions/<sandbox-grilling>.txt` — session transcript with rationale for every decision in §5.
- `app/docs/barracks/design.md` — adjacent subsystem; consumes `BaseLayout` and `Replay` from this Sandbox.

The follow-up grilling on pathfinding and targeting will produce its own session artifact and a `app/docs/sandbox/design.md` (or extension to this PRD) covering §13.
