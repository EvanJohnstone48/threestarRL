# 009 — Lightning Spell

**GitHub Issue:** #9

## Parent PRD

`app/docs/sandbox/prd.md` (§5.8 Lightning Spell)

## What to build

Full Lightning Spell behavior end-to-end.

- `SpellType` schema loaded from `spells.json` with all per-level entries TH1–TH6 (TH6-cap = level 3).
- Cast mechanics per §5.8: agent action (or scripted `DeploymentAction { kind: "cast_spell" }`) at decision-point tick `T` creates a `SpellCast` entity in `WorldState` with `cast_tick=T`, `center=(r, c)` (tile center), `bolts_remaining=N`, `next_bolt_tick=T+1`.
- Each subsequent tick where `current_tick == next_bolt_tick`: one bolt fires; applies `damage_per_hit` to every entity in radius filtered by `target_filter: "all_except_walls"`; emits `bolt_struck` event; decrements `bolts_remaining`; sets `next_bolt_tick += hit_interval_ticks`.
- When `bolts_remaining == 0`: SpellCast despawns; `spell_complete` (or terminal `bolt_struck` with terminal flag) event emitted.
- Friendly damage allowed: friendly troops in the radius are damaged. (Matches real game.)
- Cast position legality: inner buildable region only (rows 3–46, cols 3–46); deploy ring rejected by `DeploymentPlan` validator and runtime `schedule_deployment`.
- Spell capacity: `th_caps.json` declares `spell_capacity_total: 2` at TH6; runtime checks the cumulative `housing_space` of all queued + applied casts; over-cap raises `InvalidDeploymentError`.
- Walls NEVER damaged: filter strictly excludes walls.
- Authors `lightning_destroys_mortar.json` golden: a low-HP Mortar; cast Lightning over it; bolts strike; Mortar HP → 0 → destroyed; nearby wall in radius takes zero damage (verifying filter).

## Acceptance criteria

- [ ] `SpellType` for Lightning loaded with all per-level entries (TH1–TH6 with `unlocked_at_th: 5` for level 1 etc.).
- [ ] Cast at deploy-ring tile rejected by validator with clear error.
- [ ] Cast at inner-buildable tile creates a `SpellCast` entity; `spell_cast` event emitted.
- [ ] Bolts emit `bolt_struck` events at `hit_interval_ticks` cadence; one per bolt.
- [ ] Damage applies to ground troops, air troops (none at TH6 — verify filter accepts but no targets), and all non-wall buildings in radius.
- [ ] Walls in radius take zero damage from Lightning (verified by unit test).
- [ ] Friendly troops in radius take damage (verified by unit test).
- [ ] Spell capacity respected: 3rd cast in same episode (capacity = 2) raises `InvalidDeploymentError`.
- [ ] Golden replay `lightning_destroys_mortar.json` committed and passes.

## Blocked by

- Blocked by `issues/open/005-defenses-projectile-mechanics-and-splash.md`
- Blocked by `issues/open/006-troops-full-roster-and-damage-multipliers.md`

## User stories addressed

- FR-S2 (Lightning Spell).
- AC-S1.2, AC-S1.3 (one of six goldens).
