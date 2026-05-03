# threestarRL

A research project: build a Clash of Clans-style attack simulator (**The Sandbox**) and use it as a reinforcement learning environment (**The Barracks**) to study whether an agent can learn base-attacking strategy. A computer vision pipeline (**The Cartographer**) eventually allows the agent to attack bases captured from real screenshots.

For the full spec, read in this order:

1. [`app/docs/idea.md`](app/docs/idea.md) — original project pitch
2. [`app/docs/prd.md`](app/docs/prd.md) — full project PRD (vision, milestones, FRs)
3. [`app/docs/technical.md`](app/docs/technical.md) — implementation architecture
4. [`app/docs/barracks/design.md`](app/docs/barracks/design.md) — RL design specifics (obs/action/reward)
5. [`app/docs/roadmap.md`](app/docs/roadmap.md) — phased plan (Phase 0–4)
6. [`app/docs/ubiquitous-language.md`](app/docs/ubiquitous-language.md) — the project glossary
7. [`app/docs/agents/agent.md`](app/docs/agents/agent.md) — the agentic-issue operating process

## Status

The project is in **Phase 0 — Foundation**. Repo scaffolding is in place; the tracer-bullet implementation has not yet started.

## Quick start

### Python (sandbox-core, barracks, cartographer)

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras --dev       # install everything
uv run pytest -m "not slow"      # fast unit tests
uv run ruff check .              # lint
uv run ruff format .             # format
uv run pyright                   # type check
uv run pre-commit install        # install commit hooks
```

### Web frontend (sandbox-web)

Requires Node 20+.

```bash
cd app/sandbox_web
pnpm install                     # or npm install
pnpm dev                         # vite dev server
pnpm build                       # production build
pnpm lint && pnpm typecheck      # checks
```

## Repo layout

See [`app/docs/technical.md` §2](app/docs/technical.md) for the canonical layout. High-level:

```
app/
  docs/                    # PRDs, design docs, roadmap, glossary, per-subsystem
  sandbox_core/            # Python — pure simulator
  sandbox_web/             # TypeScript — Vite+React+Pixi viewer/editor
  barracks/                # Python — RL env + training
  cartographer/            # Python — CV pipeline (v2 stub)
  data/                    # Game content + sample bases + reward weights
  experiments/runs/        # Per-run training artifacts (gitignored)
tests/                     # Unit + integration + golden replay
ralph/                     # Issue execution loop
issues/
  open/                    # Active issues fed to the ralph loop
  done/                    # Completed issues, moved by the ralph loop
```

## Issues and the ralph loop

The agentic operating process (see [`app/docs/agents/agent.md`](app/docs/agents/agent.md)) is built on small, vertical-slice issues that the ralph loop executes one at a time.

**Single issue queue.** All issues live in the root `issues/` directory:

- `issues/open/` — active issues that ralph picks up.
- `issues/done/` — completed issues, moved here by ralph after the work commits.

When you start working on a phase, drop the issue files for that phase into `issues/open/` (regardless of which subsystem they belong to — sandbox, barracks, and cartographer issues all share this one queue). The ralph loop globs `issues/open/*.md` and works one at a time.

## Development workflow

1. Pick a phase from [`app/docs/roadmap.md`](app/docs/roadmap.md).
2. Decompose the phase's high-level issue clusters into individual issue files (or use the `prd-to-issues` skill).
3. Place issue files in `issues/open/`.
4. Run `ralph/once.sh` for a single iteration or `ralph/afk.sh <N>` for N iterations.
5. The ralph loop picks an issue, executes it via TDD (`/tdd` skill), runs feedback loops (`pytest`, `pyright`, `ruff`), commits, and moves the issue to `issues/done/`.

## Determinism guarantee

The simulator is **deterministic with no RNG** in v1. The same `(base.json, plan.json)` always produces a bit-identical `replay.json`. Golden replay tests in `tests/golden/replays/` enforce this against regressions.

If you need to update a golden replay (e.g., after an intentional balance change), regenerate via `pytest --update-golden` and review the diff in your PR.

## License

MIT.
