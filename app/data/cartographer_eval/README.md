# Cartographer eval set

Hand-labelled ground-truth fixtures for the v2 Cartographer empirical bar (issue #31, AC-C1/C3/C4/C5/C7).

## Layout

Each fixture is a paired `<name>.jpg` + `<name>.json` in this directory:

```
cartographer_eval/
├── th6_eval_01.jpg       # source screenshot
├── th6_eval_01.json      # hand-labelled BaseLayout (buildings + walls)
├── th6_eval_02.jpg
├── th6_eval_02.json
└── ...
```

The JSON is produced by the sandbox-web editor (`uv run npm --prefix app/sandbox_web run dev` → load the screenshot via "Load screenshot…" → place buildings and paint walls → "Export base.json"). Save the exported file back into this folder under the same basename as the screenshot.

## Scope

5 hand-labelled bases. AC-C5 (wall precision/recall) is measured against the wall placements in the same 5 layouts — there is no separate wall-only subset.
