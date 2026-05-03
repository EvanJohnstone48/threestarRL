# The Sandbox — PRD (placeholder)

**Status: stub.** This per-subsystem PRD will be authored in a dedicated grilling session before Phase 1 sandbox-content work begins. The overall project PRD already commits to:

- v1 functional requirements: see `app/docs/prd.md` §5.1.
- Architecture: see `app/docs/technical.md` §3 and §5.
- Phase plan: see `app/docs/roadmap.md` Phases 0 and 1.

## Scope of the future grilling

The dedicated Sandbox grilling session will resolve:

- Exact balance numbers per entity (HP, damage, range, speed, cooldown) for v1 — drafts approximating source-game values.
- Splash damage falloff curve (linear, step, quadratic).
- Wall Breaker AI rules (target selection, suicide trigger range, splash on detonation).
- Mortar firing arc and minimum range mechanics.
- Manual editor UX details (palette ordering, validation feedback, keyboard shortcuts).
- Replay viewer scrubbing UX (timeline detail level, event highlights, entity inspector behavior).
- Sample base authoring conventions (file naming, difficulty labeling, metadata fields).
- Performance targets per scenario.

## Decisions inherited from architecture grilling

These are committed and not up for renegotiation in the Sandbox grilling:

- 10 Hz tick rate.
- Deterministic, no RNG.
- 44×44 grid with first-class footprints and tile-walls + `is_wall` flag.
- Continuous troop position on discrete grid.
- Hybrid replay format (full state per tick + events).
- Data-driven core (no hardcoded entity stats).
- Full TH6 entity roster.
- Clan Castle as building-only (no defending troops in v1).
