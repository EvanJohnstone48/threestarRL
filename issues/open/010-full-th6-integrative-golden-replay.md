# 010 — Full TH6 integrative golden replay

**GitHub Issue:** #10

## Parent PRD

`app/docs/sandbox/prd.md` (§11.2 golden coverage; AC-S1.3 final scenario)

## What to build

The capstone integrative golden replay exercising every Phase 1 mechanic in concert.

- Hand-author `full_th6_attack.json` base in `tests/golden/replays/bases/`: a complete TH6 base with 1 TH, 4 Cannons, 3 Archer Towers, 2 Mortars, 2 Air Defenses, 2 Wizard Towers, 1 Clan Castle (empty), 75 walls in a sensible layout, and the full non-defense set (Army Camps, Barracks, Lab, Spell Factory, Mines, Collectors, Storages, Builder's Huts).
- Hand-author `full_th6_plan.json` plan: deploys all six troop types over time, casts at least one Lightning, runs to natural termination via condition 4 (no troops left) or 100% destruction.
- Plan must reach **≥50% destruction** (≥1 star) reliably under the placeholder pathing.
- Golden replay `full_th6_attack.json` recorded and committed.
- Determinism check inside the test: the test runs the sim twice and asserts byte-identical replay output (this is in addition to the broader determinism regression test in issue 011 — this asserts the integrative scenario specifically).

## Acceptance criteria

- [ ] `full_th6_attack.json` base committed; validates against `BaseLayout`.
- [ ] `full_th6_plan.json` plan committed; validates against `DeploymentPlan`; passes the (base, plan) compatibility validator.
- [ ] Golden replay `full_th6_attack.json` committed; golden-replay test passes byte-identical.
- [ ] Final score in the recorded replay shows `destruction_pct ≥ 50` and at least 1 star.
- [ ] Determinism subassertion in the test: rerunning produces byte-identical replay (`config_hash` matches).
- [ ] All four termination conditions exercised at least once across the golden corpus (timer, 100%, end_attack, nothing-left) — document which scenario covers which condition.
- [ ] Register the `full_th6_attack` scenario in the `SCENARIOS` list at `tests/integration/test_replay_determinism.py` (single-line append; framework already in place from issue 011).

## Blocked by

- Blocked by `issues/open/005-defenses-projectile-mechanics-and-splash.md`
- Blocked by `issues/open/006-troops-full-roster-and-damage-multipliers.md`
- Blocked by `issues/open/007-walls-and-wall-breaker-suicide.md`
- Blocked by `issues/open/008-wizard-splash-damages-walls.md`
- Blocked by `issues/open/009-lightning-spell.md`

## User stories addressed

- AC-S1.3 (full set of six goldens — this is #6).
- AC-S1.4 (defense filters live in integrative scenario).
