# Experiments

Per-run training artifacts and the configs that produced them.

## Layout

```
experiments/
  configs/
    mvp_tiny.json        # training config for MVP-Tiny
    mvp_real.json        # training config for MVP-Real
    ...
  runs/<run_id>/         # one self-contained directory per training run (gitignored)
    config.json          # resolved config snapshot at run start
    run_metadata.json    # git_sha, seed, library versions, start time, etc.
    checkpoints/         # SB3 model checkpoints
    eval_results/        # per-eval-call metrics JSON
    replays/             # best/worst eval rollout replays
    tensorboard/         # SB3 tensorboard logs
  notes/                 # writeups (mvp_real_results.md, cartographer_results.md, etc.)
  sweeps/                # hyperparameter sweep results (Phase 2.6)
```

## Conventions

- Every run gets a unique `run_id` (timestamp + short hash).
- `runs/<run_id>/` is **immutable post-run**. Never edit a run's artifacts after the run completes.
- Training launches with: `uv run python -m barracks.train --config configs/<config>.json`.
- Reproducing a run: `uv run python -m barracks.train --config runs/<run_id>/config.json --seed-from runs/<run_id>/run_metadata.json`.
- Training refuses to start with a dirty git tree unless `--allow-dirty` is passed.

## What's gitignored

`runs/*` is gitignored (only `.gitkeep` is tracked). Training artifacts are local-only — push notable results to `notes/` as markdown writeups instead of committing run dirs.
