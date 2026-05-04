# 005 — Defenses: projectile mechanics + splash

**GitHub Issue:** #5

## Parent PRD

`app/docs/sandbox/prd.md` (§5.6 projectiles, §5.7 splash)

## What to build

Full defense behavior for all five TH6 defenses: Cannon, Archer Tower, Mortar, Air Defense, Wizard Tower. Includes the projectile model and the splash impact system.

- `Projectile` entity in `WorldState` per §5.6 (attacker_id, target_id, attacker_position, current_position, impact_position, damage, splash_radius_tiles, splash_damages_walls, ticks_to_impact, attack_kind).
- Projectile travel model: `travel_ticks = distance_tiles / projectile_speed_tiles_per_sec × 10`. Per-tick advance along the attacker→impact line.
- `projectile_homing` flag drives behavior:
  - **Homing (Cannon, Archer Tower, Air Defense, Wizard Tower):** projectile tracks the target until impact; if target dies mid-flight, projectile despawns silently, no damage.
  - **Non-homing (Mortar):** `impact_position` committed at fire time (target's hitbox center snapped to nearest tile center); on impact, splash applies in radius regardless of original-target survival.
- `splash.py` deep module with pure-functional API: `resolve_splash(world, center, radius, damage, filter, source_kind) → list[damage_event]`. Flat circular, target-hitbox-edge distance per §5.7 (always-square hitbox for splash distance), `splash_damages_walls` filter, friendly-fire model.
- First attack on target acquisition fires immediately (cooldown timer starts at zero); subsequent attacks elapse `attack_cooldown_ticks`.
- Targeting is still placeholder (§13.3): defenses pick nearest in-range troop with no preference. Real targeting is the deferred grilling.
- `target_filter` (`ground` / `air` / `both`) is enforced even though targeting is placeholder — Air Defense ignores ground troops; Mortar/Cannon attack ground only; Archer Tower/Wizard Tower attack ground+air. (At TH6 only ground troops exist, so AD is effectively inert; the filter still matters in tests.)
- Authors `mortar_splash.json` golden replay: a base with one Mortar, deploy 5 Barbarians clustered, Mortar splash kills 3+.

## Acceptance criteria

- [ ] All five defenses load from `buildings.json` and instantiate in `Sim`.
- [ ] `Projectile` entities appear in `WorldState` during in-flight ticks; `projectile_fired` events emitted on creation, `damage` events on impact.
- [ ] Mortar's projectile commits to `impact_position` at fire time; if cluster of troops moves out before impact, splash hits the empty location (no damage to absent troops).
- [ ] Cannon/AT/AD/WT projectiles despawn silently when target dies mid-flight; no damage applied.
- [ ] Splash damage applies to all entities in radius per the filter; one `damage` event emitted per affected target.
- [ ] Wizard Tower splash damages only troops, never other buildings (AC-S1.4 partial — ground filter respected even with placeholder targeting).
- [ ] `splash.py` unit tests: empty radius, single target, multiple targets, wall filter on/off, friendly-fire exclusion (placeholder no-op for v1 since no friendly attacker splash from defenses), distance-to-hitbox-edge for varied footprints.
- [ ] Golden replay `mortar_splash.json` committed and passes — Mortar splash kills 3+ clustered Barbarians in single impact.
- [ ] AC-S1.4 covered for the defense side: target filters respected at attack time.
- [ ] Register the `mortar_splash` scenario in the `SCENARIOS` list at `tests/integration/test_replay_determinism.py` (single-line append; framework already in place from issue 011).

## Blocked by

- Blocked by `issues/open/004-wiki-scraper-and-overrides-loader.md`

## User stories addressed

- FR-S2 (defense roster).
- FR-S3 (data-driven projectile speeds + homing flags).
- AC-S1.1, AC-S1.2 (defense mechanics live), AC-S1.3 (one of six goldens), AC-S1.4 (defense filters).
