"""CLI: python -m cartographer ingest --in <screenshot> [--out <path>]"""

from __future__ import annotations

import argparse
from pathlib import Path

from cartographer import pipeline


def main() -> None:
    parser = argparse.ArgumentParser(prog="cartographer")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_parser = sub.add_parser("ingest", help="Ingest a screenshot into a BaseLayout JSON.")
    ingest_parser.add_argument("--in", dest="input", required=True, type=Path, metavar="PATH")
    ingest_parser.add_argument("--out", dest="output", type=Path, default=None, metavar="PATH")

    args = parser.parse_args()

    if args.command == "ingest":
        pipeline.run(args.input, args.output)
