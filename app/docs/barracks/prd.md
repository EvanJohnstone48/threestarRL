# The Barracks — PRD (placeholder)

**Status: stub.** This per-subsystem PRD will be authored in a dedicated grilling session before Phase 1.2 RL work begins. The overall project PRD already commits to:

- v1 functional requirements: see `app/docs/prd.md` §5.2.
- Architecture: see `app/docs/technical.md` §6.
- RL design specifics: see `app/docs/barracks/design.md`.
- Phase plan: see `app/docs/roadmap.md` Phases 1 and 2.

## Scope of the future grilling

The dedicated Barracks grilling session will resolve:

- Action space shape variants — single flattened `Discrete` vs explicit `head_select` vs hierarchical heads.
- Wait-bucket granularity — keep 50/100/200 ticks or add 25-tick fine-grain.
- Observation channel ordering and consolidation — collapse per-building-type channels into a categorical encoding?
- Frame stacking vs LSTM vs single-frame (final call deferred to MVP-Tiny empirical results).
- Curriculum specifics — round thresholds, base difficulty labeling, promotion criteria.
- Reward weight tuning protocol — A/B run count, eval metric used during tuning, allowed parameter ranges.
- Hyperparameter sweep budget — Bayesian optimization vs grid search; sweep ranges per HP.
- Augmentation at observation level — random rotation/mirror at training time as an additional invariance.
- Custom CNN feature extractor depth and width tuning.

## Decisions inherited from architecture grilling

These are committed and not up for renegotiation in the Barracks grilling:

- Decision-point action model (not per-tick).
- Single flattened `Discrete(C_act * 44 * 44 + n_scalar)` action space with masking.
- Rich semantic grid observation (Path 2 — pre-decoded channels).
- Layered shaped reward dominated by sparse star bonuses.
- SB3 + sb3-contrib MaskablePPO.
- 16-worker SubprocVecEnv.
- Tiered training distribution (1 base → 30 + mutations → procedural if needed).
- Frozen 5-base eval set, never re-tuned.
