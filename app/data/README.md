# Data

This directory holds all game content, sample bases, and tunable configuration for threestarRL. Everything here is loaded by `sandbox_core` and `barracks` at startup; nothing in code hardcodes entity stats.

## Files

| Path | Purpose | Authored in phase |
| --- | --- | --- |
| `buildings.json` | All TH6 building stats (HP, footprint, damage, range, cooldown, splash, target filter, projectile arc, ...) | Phase 0.1 (skeleton: 2 entries) → Phase 1.1.1–1.1.4 (full TH6) |
| `troops.json` | All TH6 troop stats (HP, damage, range, speed, target preference, splash, housing space) | Phase 0.1 (skeleton: 2 entries) → Phase 1.1.2 (full TH6) |
| `spells.json` | Lightning Spell stats | Phase 1.1.3 |
| `th6_rules.json` | Caps: max walls, max cannons, troop capacity, spell capacity | Phase 1.1.4 |
| `reward_weights.json` | Tunable reward coefficients (created at scaffold time with defaults; tuned in dedicated sessions during MVP-Tiny eval) | Scaffold |
| `cartographer_config.json` | (v2) Roboflow project name, dataset version, inference endpoint, confidence threshold | Phase 3 |
| `sample_bases/tracer.json` | MVP-Tiny tracer base (TH + 1 Cannon + walls) | Phase 0.1 |
| `sample_bases/base_*.json` | MVP-Real training set (~30 hand-built TH6 bases) | Phase 1.1.5 |
| `sample_bases/eval_*.json` | Frozen 5-base held-out eval set | Phase 1.1.5 |
| `scraped_bases/*.json` | (v2) Cartographer outputs (gitignored) | Phase 3 |
| `mutations.py` | Base mutation pipeline (rotate, mirror, jitter, wall edits) | Phase 2.4 |
| `generator.py` | (Deferred) Procedural base generator with TH6 caps | Phase 2.8 if MVP-Real overfits |

## Schema versioning

Every JSON file in this directory has a `schema_version` integer field. Migrations live in `sandbox_core/schemas.py` and are applied transparently at load time.

## Source of truth

All Pydantic models are defined in `sandbox_core/schemas.py`. JSON files here must validate against those models — any change to the schema requires either a content edit here or a migration there.
