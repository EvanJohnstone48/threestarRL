"""CLI entrypoint for sandbox-core.

Subcommands:
  run            Simulate (base, plan) -> Replay JSON.
  validate       Validate a BaseLayout JSON file.
  validate-plan  Validate a DeploymentPlan JSON file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import sandbox_core
from sandbox_core.content import DEFAULT_DATA_DIR, load_catalogue
from sandbox_core.replay import compute_config_hash, write_replay
from sandbox_core.schemas import BaseLayout, DeploymentPlan
from sandbox_core.sim import Sim


def _cmd_run(args: argparse.Namespace) -> int:
    base_path = Path(args.base)
    plan_path = Path(args.plan)
    out_path = Path(args.out)
    data_dir = Path(args.data_dir) if args.data_dir else DEFAULT_DATA_DIR

    base_raw = json.loads(base_path.read_text(encoding="utf-8"))
    plan_raw = json.loads(plan_path.read_text(encoding="utf-8"))
    base = BaseLayout.model_validate(base_raw)
    plan = DeploymentPlan.model_validate(plan_raw)

    catalogue = load_catalogue(data_dir)

    config_hash = compute_config_hash(
        base_raw,
        plan_raw,
        json.loads((data_dir / "buildings.json").read_text(encoding="utf-8")),
        json.loads((data_dir / "troops.json").read_text(encoding="utf-8")),
    )

    sim = Sim(
        base,
        plan,
        catalogue_buildings=catalogue.buildings,
        catalogue_troops=catalogue.troops,
        catalogue_spells=dict(catalogue.spells),
        sim_version=sandbox_core.__version__,
        config_hash=config_hash,
    )
    sim.run_until_termination(max_ticks=args.max_ticks)

    replay = sim.to_replay(
        base_name=base.metadata.name,
        plan_name=plan.metadata.name,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_replay(replay, out_path, pretty=bool(args.pretty))

    print(
        f"wrote {out_path} (ticks={replay.metadata.total_ticks}, "
        f"stars={replay.metadata.final_score.stars}, "
        f"destruction={replay.metadata.final_score.destruction_pct:.1f}%)"
    )
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    raw = json.loads(Path(args.path).read_text(encoding="utf-8"))
    BaseLayout.model_validate(raw)
    print(f"OK {args.path}")
    return 0


def _cmd_validate_plan(args: argparse.Namespace) -> int:
    raw = json.loads(Path(args.path).read_text(encoding="utf-8"))
    DeploymentPlan.model_validate(raw)
    print(f"OK {args.path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m sandbox_core.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Simulate (base, plan) -> replay JSON")
    p_run.add_argument("--base", required=True, help="path to BaseLayout JSON")
    p_run.add_argument("--plan", required=True, help="path to DeploymentPlan JSON")
    p_run.add_argument("--out", required=True, help="path to write Replay JSON")
    p_run.add_argument("--data-dir", default=None, help="override app/data/ dir")
    p_run.add_argument("--max-ticks", type=int, default=1800)
    p_run.add_argument("--pretty", action="store_true", help="pretty-print replay JSON")
    p_run.set_defaults(func=_cmd_run)

    p_val = sub.add_parser("validate", help="Validate a BaseLayout JSON")
    p_val.add_argument("path")
    p_val.set_defaults(func=_cmd_validate)

    p_valp = sub.add_parser("validate-plan", help="Validate a DeploymentPlan JSON")
    p_valp.add_argument("path")
    p_valp.set_defaults(func=_cmd_validate_plan)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
