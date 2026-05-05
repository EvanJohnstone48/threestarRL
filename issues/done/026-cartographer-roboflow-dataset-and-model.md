# 026 — Roboflow dataset capture, label, and train v1 model

**GitHub Issue:** #26

## Parent PRD

`app/docs/cartographer/prd.md` (§4.4, §4.8, §4.11, §4.14)

## What to build

**HITL.** Out-of-repo work in the Roboflow UI. Produces a trained object-detection model the rest of the pipeline can call.

Capture ≥50 TH6 home-village screenshots from the project owner's device under the input scope contracted in PRD §4.11 (scout view, full base in frame, default zoom range, no custom scenery, default device aspect ratio).

Create the Roboflow project. Label each screenshot with the type-only taxonomy from PRD §4.4 — every class label must literally equal a key in `app/data/buildings.json` (lowercase, snake_case). The 16 classes are: `cannon`, `archer_tower`, `mortar`, `air_defense`, `wizard_tower`, `town_hall`, `clan_castle`, `army_camp`, `barracks`, `lab`, `spell_factory`, `gold_mine`, `elixir_collector`, `gold_storage`, `elixir_storage`, `builders_hut`. Walls are intentionally excluded from the taxonomy per PRD §4.5.

Hit ≥20 instances per defense class (`cannon`, `archer_tower`, `mortar`, `air_defense`, `wizard_tower`) per PRD §4.14.

Train a Roboflow object-detection model. Pin `project_name` and `dataset_version` (and any other Roboflow-side config required by the hosted Inference SDK) in `app/data/cartographer_config.json`. Leave `confidence_threshold` at `0.5`. Document `ROBOFLOW_API_KEY` env-var usage in `app/cartographer/README.md` (or contributor docs) so that issue 027 can call hosted inference.

## Acceptance criteria

- [ ] ≥50 TH6 screenshots captured and stored (path documented).
- [ ] All screenshots labelled in Roboflow.
- [ ] Every class label matches a key in `buildings.json` exactly (no `Wall` class).
- [ ] ≥20 instances per defense class.
- [ ] Roboflow model trained and an inference endpoint is reachable with the project's API key.
- [ ] `cartographer_config.json` updated with real `project_name` and `dataset_version`.
- [ ] `ROBOFLOW_API_KEY` setup documented.

## Blocked by

- Blocked by `issues/open/025-cartographer-package-skeleton-cli-tracer.md` (so the class enum the model targets is committed first).

## User stories addressed

Parent PRD user stories: 11, 12, 14.
