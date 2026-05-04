# Golden replays

Frozen `(base.json, plan.json) → expected_replay.json` fixtures.

The architectural keystone for a deterministic simulator: any change that unintentionally alters simulation output breaks the corresponding golden test. Intentional changes regenerate via `pytest --update-golden` and the diff is part of the PR.

See `app/docs/technical.md` §9.3 for the strategy.

## Phase 1 scenarios

- `tracer_smoke.json` — tracer base + single Barbarian deploy.
- `mortar_splash.json` — Mortar splash kills 3+ clustered Barbarians in one impact.
- `wall_breaker_breach.json` — WB breaches a wall fence, follow-up Goblin destroys the TH.
- `wizard_splash_walls.json` — Wizard's splash damages adjacent walls while attacking a building.
- `lightning_destroys_mortar.json` — two Lightning casts destroy a low-HP Mortar.
- `full_th6_attack.json` — capstone integrative: full TH6 roster + all six troop types + Lightning.

## Termination-condition coverage

PRD §5.9 lists four termination conditions; the golden corpus covers them as follows:

| Condition       | Covered by                                                          |
| --------------- | ------------------------------------------------------------------- |
| timer (1800 t)  | _gap_ — no current scenario runs the full 1800 ticks                |
| 100% destruction | `wall_breaker_breach`, `wizard_splash_walls`, `full_th6_attack`    |
| `end_attack`    | _gap_ — env-only concern; not expressible in `DeploymentPlan`       |
| nothing-left    | `tracer_smoke`, `mortar_splash`, `lightning_destroys_mortar`        |

`end_attack` is an agent action (Barracks env), not a `DeploymentPlan` action — the
PRD §6 explicitly excludes it from plan schemas — so it cannot be triggered from a
hand-authored plan and is not exercised by the golden corpus.

The timer gap can be filled by a future scenario whose plan extends past tick 1800
without reaching 100% destruction.
