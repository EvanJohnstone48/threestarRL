# 006 — Troops: full roster + damage multipliers

**GitHub Issue:** #6

## Parent PRD

`app/docs/sandbox/prd.md` (§5.5 damage application, §6.1 schemas)

## What to build

Full TH6 troop roster loaded from `troops.json` with all per-level stats (TH1–TH6) and the damage-multiplier system fully wired.

- All six TH6 troops: Barbarian, Archer, Goblin, Giant, Wall Breaker, Wizard. Per-level stats consumed.
- `BuildingType.category` enum populated for every TH6 building per §5.5: `town_hall`, `clan_castle`, `defense`, `wall`, `resource_collector`, `resource_storage`, `army`, `builder_hut`. Closed enum at v1.
- `combat.py` deep module pure-functional API: `apply_damage(target, base_damage, attacker, multipliers) → damage_event`. Formula: `damage_dealt = troop.base_damage_at_level × troop.damage_multipliers.get(target.category, troop.damage_multiplier_default)`.
- Multiplier configuration in `troops.json` (and overrides for WB in `manual_overrides.json` if not in scraped output):
  - **Goblin:** `damage_multipliers: {"resource_collector": 2.0, "resource_storage": 2.0}`, `damage_multiplier_default: 1.0`.
  - **Wall Breaker:** `damage_multipliers: {"wall": 1.0}`, `damage_multiplier_default: ~0.04`. `base_damage` is the wiki's wall-damage value.
  - **All others:** `damage_multipliers: {}`, `damage_multiplier_default: 1.0`.
- Targeting and pathing remain placeholder (§13.3); this issue does NOT touch them. WB suicide is its own issue (007).

## Acceptance criteria

- [ ] All six troops load from `troops.json` with per-level stats for TH1–TH6.
- [ ] `category` field present and validated for every `BuildingType`. Validator rejects unknown categories.
- [ ] `combat.py` unit tests cover:
  - Multiplier lookup with explicit category match.
  - Multiplier lookup falling back to `damage_multiplier_default`.
  - Goblin attacking a Gold Storage → 2× base_damage (assertable).
  - Goblin attacking a Cannon → 1× base_damage (default).
  - Wall Breaker `base_damage` × 1.0 vs wall (full damage).
  - Wall Breaker `base_damage` × 0.04 vs Cannon (default).
  - Default-default multiplier troop (e.g. Barbarian) vs every category yields 1×.
- [ ] In a placeholder-pathing scenario, Goblin attacking a Gold Storage deals exactly 2× the base damage value per attack tick (verified in a fast unit test).
- [ ] WB suicide on a wall vs WB suicide on a defense yields ~25× damage ratio (matches base × multiplier formula). (Full WB suicide mechanic is issue 007; this issue verifies the multiplier math standalone.)

## Blocked by

- Blocked by `issues/open/004-wiki-scraper-and-overrides-loader.md`

## User stories addressed

- FR-S2 (troop roster).
- FR-S3 (data-driven multipliers).
- AC-S1.1.
