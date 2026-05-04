# 008 — Wizard splash damages walls

**GitHub Issue:** #8

## Parent PRD

`app/docs/sandbox/prd.md` (§5.3 walls, §5.7 splash, §11.2 golden coverage)

## What to build

Verifies and demonstrates the asymmetric `splash_damages_walls` flag — Wizard's splash damages walls, but defense splash (Mortar, Wizard Tower) does not.

- Wizard configured in `troops.json` with `splash_damages_walls: true` (overlay via `manual_overrides.json` if not in scraped output).
- Mortar and Wizard Tower configured with `splash_damages_walls: false` per §5.3.
- When Wizard fires on a target whose splash radius covers walls, those walls take splash damage equal to `base_damage × multiplier` per `damage_multipliers`.
- Authors `wizard_splash_walls.json` golden: a Wizard attacks a building behind a row of walls; walls in the splash radius progressively take damage as the Wizard fires.

## Acceptance criteria

- [ ] Wizard's `splash_damages_walls: true` in the merged content; Mortar and Wizard Tower `false`.
- [ ] When Wizard fires on a target whose splash radius covers walls: those walls take damage; emits `damage` events for each affected wall.
- [ ] Comparison unit test: same splash geometry resolved with Wizard source (walls damaged) vs Mortar source (walls untouched).
- [ ] Golden replay `wizard_splash_walls.json` committed and passes.

## Blocked by

- Blocked by `issues/open/006-troops-full-roster-and-damage-multipliers.md`

## User stories addressed

- FR-S2 (Wizard mechanics).
- AC-S1.2, AC-S1.3 (one of six goldens).
