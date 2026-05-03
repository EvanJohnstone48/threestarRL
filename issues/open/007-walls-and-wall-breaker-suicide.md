# 007 — Walls + Wall Breaker suicide mechanics

**GitHub Issue:** #7

## Parent PRD

`app/docs/sandbox/prd.md` (§5.3 walls, §5.5 damage multipliers, §11.2 golden coverage)

## What to build

Full wall behavior at the simulator level + the Wall Breaker suicide-and-splash mechanic.

- Walls treated as 1×1 first-class blockers in `Grid` (already partially in 001's placeholder); `is_wall: true` flag drives behavior.
- Wall HP scaling per level loaded from `buildings.json`.
- WB suicide trigger: in placeholder pathing, the WB walks straight at the nearest wall and on hitbox-adjacency triggers its suicide. (Real targeting/pathing for WB is part of the deferred grilling.)
- WB suicide event applies:
  - Full `base_damage × wall_multiplier (=1.0)` to the target wall.
  - Splash damage with `splash_damages_walls: true` on adjacent walls in radius.
  - WB despawned from `WorldState` (HP → 0).
- `damages_walls_on_suicide: bool` field on `TroopType` drives this; set `true` only for Wall Breaker.
- Wall destruction emits `destroyed` event; tile becomes walkable (the placeholder pathing must respect this — re-acquire path on next-target lookup).
- Authors `wall_breaker_breach.json` golden: small base with walls fencing a Cannon; deploy WB; watch wall destruction; deploy a follow-up Goblin that walks through the breach (placeholder pathing should naturally find the now-walkable tile).

## Acceptance criteria

- [ ] Wall HP scales correctly by level per scraped data; verified by unit test loading walls at level 1, 3, 6.
- [ ] WB on hitbox-adjacency to wall: emits suicide-damage event, applies wall_damage to target wall + splash to adjacent walls.
- [ ] Walls in WB splash radius take splash damage; non-wall buildings in the radius take their multiplier-adjusted damage (per `damage_multipliers`).
- [ ] WB has zero HP after suicide and is despawned.
- [ ] `splash_damages_walls: true` correctly produces damage events on walls; `splash_damages_walls: false` (e.g., Mortar) leaves walls unaffected — assertable in a single unit test exercising both source kinds against the same wall layout.
- [ ] Wall destruction makes the tile walkable: the placeholder pathfinder's next-target lookup successfully routes through a destroyed wall position (verified in golden replay).
- [ ] Golden replay `wall_breaker_breach.json` committed and passes: wall destroyed, breach visible, follow-up Goblin pathing through.
- [ ] Note in `pathfinding.py`: "wall-destruction-driven re-pathing is placeholder; full mechanic in deferred grilling".

## Blocked by

- Blocked by `issues/open/005-defenses-projectile-mechanics-and-splash.md`
- Blocked by `issues/open/006-troops-full-roster-and-damage-multipliers.md`

## User stories addressed

- FR-S2 (Wall + Wall Breaker behavior).
- AC-S1.2, AC-S1.3 (one of six goldens).
