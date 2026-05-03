# The Cartographer — PRD (placeholder)

**Status: stub. Cartographer is deferred to v2.** This per-subsystem PRD will be authored in a dedicated grilling session before Phase 3 work begins. The overall project PRD already commits to:

- v1 + v2 functional requirements: see `app/docs/prd.md` §5.3.
- Architecture: see `app/docs/technical.md` §7.
- Phase plan: see `app/docs/roadmap.md` Phase 3.

## Scope of the future grilling

The dedicated Cartographer grilling session will resolve:

- Roboflow class taxonomy — exactly which entity classes the model detects and how merged classes (e.g., "Cannon-level-1" vs "Cannon-level-6") are handled.
- Perspective correction technique — homography-based vs ML-based vs hybrid.
- Confidence threshold tuning per class.
- Hosted vs local inference choice.
- Synthetic-vs-real training data split inside Roboflow.
- How sandbox-web's renderer is reused (or not) to produce synthetic training screenshots.
- Detection-to-grid alignment math (bbox center to tile origin, footprint inference from bbox dimensions).
- Failure modes and graceful degradation (e.g., when detection confidence is below threshold).
- Whether to support multi-screenshot ingestion for one base (capturing the full layout from multiple zoom levels).

## Decisions inherited from architecture grilling

These are committed and not up for renegotiation in the Cartographer grilling:

- Roboflow-based pipeline (not from-scratch CNN).
- Output contract: `BaseLayout` JSON conforming to the v1-frozen schema. No Cartographer-specific layout type.
- Pipeline shape: preprocess → Roboflow detect → grid alignment → footprint reconstruction → schema emission.
- API key via `ROBOFLOW_API_KEY` env var, never committed.
- Project + dataset version pinned in `app/data/cartographer_config.json`.
- v1 commitment is package stub only; no v1 implementation work.

## Why deferred

Decoupling Cartographer from v1 is deliberate. Building a CV pipeline while also debugging RL training on a custom simulator is two unconstrained subprojects in parallel — one is enough. v2 begins after MVP-Real has confirmed the agent learns at all on synthetic bases, at which point the synthetic-to-real transfer experiment is the headline result.
