# threestarRL

threestarRL is a research project about whether an agent can learn to attack
Clash of Clans-style bases inside a custom simulator.

The project has three main pieces:

- **The Sandbox**: a deterministic attack simulator and replay viewer.
- **The Barracks**: a reinforcement learning environment built on top of the simulator.
- **The Cartographer**: a future computer vision pipeline that turns base screenshots into structured layouts.

This project does not interact with the live game, automate gameplay, or run a bot
against real accounts. The goal is to build a controlled simulator with similar
strategic structure, then study what an RL agent can learn from it.

## Inspiration

I have played Clash of Clans for most of my life. I started my first base in
grade one, and years later, after reaching Town Hall 15 and playing less often,
I saw my brother playing and remembered an old question I had as a kid:

What if a bot could actually learn how to attack?

The interesting part is that Clash attacks are not pure chaos. A base is mostly
static once the attack starts. Buildings, walls, defenses, ranges, troop stats,
and target preferences all create a rules-driven system. Troops move through
pathfinding. Defenses select targets. Attacks succeed or fail through decisions
about timing, placement, funneling, and priority.

threestarRL is an attempt to build that simulator and
see whether modern reinforcement learning can discover a useful attack strategy
inside it. Excited to see where it goes :)

## Current Status

The project is in **Phase 0 - Foundation**.

The current goal is a tracer bullet: deploy one troop on a tiny base, simulate
the attack, write a replay, and render that replay in the browser. This keeps
the first milestone small while still touching the real architecture end to end.

## Documentation

Read these in order:

1. [`app/docs/idea.md`](app/docs/idea.md) - original project idea
2. [`app/docs/prd.md`](app/docs/prd.md) - project PRD
3. [`app/docs/technical.md`](app/docs/technical.md) - implementation architecture
4. [`app/docs/roadmap.md`](app/docs/roadmap.md) - phased build plan
5. [`app/docs/ubiquitous-language.md`](app/docs/ubiquitous-language.md) - project glossary
6. [`app/docs/barracks/design.md`](app/docs/barracks/design.md) - RL observation/action/reward design
7. [`app/docs/agents/agent.md`](app/docs/agents/agent.md) - agentic issue workflow

## Quick Start

### Python

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras --dev
uv run pytest -m "not slow"
uv run ruff check .
uv run ruff format .
uv run pyright
uv run pre-commit install
```

### Web Frontend

Requires Node 20+.

```bash
cd app/sandbox_web
npm install
npm run dev
npm run build
npm run lint
npm run typecheck
```

On Windows PowerShell, use `npm.cmd` if `npm` is blocked by execution policy:

```powershell
npm.cmd install
npm.cmd run dev
```

### Generated TypeScript types

Sandbox-web reads the sim's data contracts from
`app/sandbox_web/src/generated_types.ts`, which is auto-generated from the
Pydantic schemas in `app/sandbox_core/schemas.py`. Regenerate after editing the
schemas:

```bash
uv run generate-types
# or, equivalently:
uv run python -m sandbox_core.tools.generate_types
```

Pre-commit and CI fail if the committed file drifts from the schemas. The same
check runs locally as a unit test (`tests/unit/sandbox_core/test_generate_types.py`).

## Repo Layout

```text
app/
  docs/                    # PRDs, roadmap, glossary, design docs
  sandbox_core/            # Python simulator core
  sandbox_web/             # Vite + React + Pixi replay viewer/editor
  barracks/                # RL environment and training code
  cartographer/            # CV pipeline stub
  data/                    # game data, sample bases, reward weights
  experiments/runs/        # training artifacts, gitignored
tests/                     # unit, integration, and golden replay tests
ralph/                     # issue execution loop scripts and prompts
issues/                    # active issues for the agentic workflow
```

## Research Question

Can an RL agent learn useful attack strategy, including deployment timing,
troop placement, pathing awareness, spell usage, and target prioritization,
inside a custom base-attack simulator?
