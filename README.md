# threestarRL

A research project: build a Clash of Clans-style attack simulator (**The Sandbox**) and use it as a reinforcement learning environment (**The Barracks**) to study whether an agent can learn base-attacking strategy. A computer vision pipeline (**The Cartographer**) eventually allows the agent to attack bases captured from real screenshots.

For the full spec, read in this order:

1. [`app/docs/idea.md`](app/docs/idea.md) — original project idea
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
issues/                    # Active issues fed to the ralph loop (see "Issues" below)
```
