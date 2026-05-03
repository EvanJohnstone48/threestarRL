# 001 — Sandbox-core tracer

**GitHub Issue:** #1

## Parent PRD

`app/docs/sandbox/prd.md` (Phase 0 — Tracer bullet)

## What to build

The Phase 0 tracer bullet for sandbox-core. A thin end-to-end pure-Python slice from input to Replay JSON, sufficient to demo "Barbarian walks to Cannon and destroys the TH" via CLI.

Includes:

- All Pydantic v2 schemas for v1 data contracts per PRD §6: `BaseLayout`, `BuildingPlacement`, `DeploymentPlan`, `DeploymentAction`, `WorldState`, `TickFrame`, `Replay`, `Score`, `Event`, `BuildingType`, `TroopType`, `SpellType`. All persisted JSONs carry `schema_version: 1`.
- `Grid` module with footprint occupancy, the 50×50 outer / 44×44 buildable / 3-tile deploy-ring region masks per §5.1.
- `Sim` class per §7.1 with the per-tick update order from §7.2. **Pathfinding and targeting are stubbed per §13.3**: troops walk in a straight line toward the nearest non-wall building, attack on hitbox-adjacency (melee); defenses pick the nearest in-range troop with no preference.
- `combat.py`, `splash.py`, `scoring.py` as deep modules per §7.3 (pure-functional, isolated unit tests).
- `content.py` loader reading hand-written 2-entity `buildings.json` (Town Hall + Cannon) and `troops.json` (Barbarian + Giant). The wiki scraper is issue 004 — this issue ships hand-written placeholder data only.
- `tracer.json` base + `single_barb.json` plan (committed under `app/data/sample_bases/` and `app/data/sample_plans/`).
- CLI `python -m sandbox_core.cli run --base ... --plan ... --out ...` plus `validate` and `validate-plan` subcommands per §7.
- `replay.py` writer with 3-decimal float rounding (§6.5), `config_hash` (§6.7), minified default output, pretty mode for goldens (§6.6).
- Golden replay `tracer_smoke.json` committed under `tests/golden/replays/` and asserted by a golden-replay test.
- Determinism property test placeholder (full version is issue 011).

## Acceptance criteria

- [ ] All Pydantic schemas in `app/sandbox_core/schemas.py` typecheck under `pyright` strict.
- [ ] `python -m sandbox_core.cli run --base tracer.json --plan single_barb.json --out out.json` succeeds.
- [ ] `out.json` validates against `Replay`.
- [ ] Replay round-trip test passes (write → read → assert structural equality).
- [ ] Golden replay `tracer_smoke.json` committed; golden-replay test passes byte-identical to fresh sim output.
- [ ] `Sim.step_tick()` after termination raises `SimTerminatedError`; `Sim.advance_to(t < current)` raises `ValueError`; `Sim.schedule_deployment(...)` after termination raises `SimTerminatedError`; invalid deploy raises `InvalidDeploymentError`.
- [ ] Pre-commit hooks (ruff + ruff-format + pyright + `pytest -m "not slow"`) all pass.
- [ ] CI green on the full suite.
- [ ] Per-tick update order in `sim.py` matches §7.2; placeholder steps clearly marked with `# Placeholder per PRD §13.3 — replace once pathfinding/targeting grilling lands`.

## Blocked by

None — can start immediately.

## User stories addressed

- FR-S1 (10 Hz, no RNG, deterministic).
- FR-S3 (data-driven; no hardcoded stats — even with 2-entity hand-written data, stats live in JSON).
- FR-S4 (`Replay` artifact per attack with full state per tick + events).
- FR-S5 (Python library + CLI).
- FR-S6 (`Score` computation).
- FR-S7 (termination conditions).
- FR-S8 (validators reject bad inputs).
- FR-S9 (no log emissions in hot path).
- AC-S0.1, AC-S0.3, AC-S0.4.
