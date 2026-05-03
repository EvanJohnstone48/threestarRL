# Golden replays

Frozen `(base.json, plan.json) → expected_replay.json` fixtures.

The architectural keystone for a deterministic simulator: any change that unintentionally alters simulation output breaks the corresponding golden test. Intentional changes regenerate via `pytest --update-golden` and the diff is part of the PR.

See `app/docs/technical.md` §9.3 for the strategy.

## Planned scenarios (Phase 1)

- `vanilla_movement.json` — one Barbarian walking and attacking.
- `mortar_splash.json` — Mortar splash damage hits multiple troops.
- `wb_breach.json` — Wall Breaker pathing and wall destruction.
- `wizard_splash.json` — Wizard's splash damage on a tight troop cluster.
- `lightning_spell.json` — Lightning destroys a low-HP defense.
- `full_th6_attack.json` — full TH6 roster end-to-end attack.
