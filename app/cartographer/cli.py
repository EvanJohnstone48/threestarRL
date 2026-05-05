"""CLI: python -m cartographer ingest --in <screenshot> [--out <path>]
              python -m cartographer calibrate --in <path>...
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import threading
import webbrowser
from pathlib import Path

from cartographer import pipeline


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _run_calibrate(screenshot_paths: list[Path]) -> None:
    import uvicorn

    from cartographer import detect, preprocess
    from cartographer.server import ScreenshotEntry, create_app

    config_path = Path(__file__).parent.parent / "data" / "cartographer_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    api_key = os.environ.get("ROBOFLOW_API_KEY", "")

    entries: list[ScreenshotEntry] = []
    for p in screenshot_paths:
        image = preprocess.load(p)
        accepted, _ = detect.run(
            image,
            project_name=config["project_name"],
            dataset_version=config["dataset_version"],
            confidence_threshold=config["confidence_threshold"],
            api_key=api_key,
        )
        entries.append(ScreenshotEntry(filename=p.name, image_path=p, detections=accepted))

    shutdown_event = threading.Event()
    app = create_app(entries, config, shutdown_event=shutdown_event)

    port = _free_port()
    url = f"http://localhost:{port}/?tab=cartographer&mode=calibrate"

    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait briefly for the server to start before opening the browser.
    import time
    time.sleep(0.5)
    webbrowser.open(url)

    shutdown_event.wait()
    server.should_exit = True
    thread.join(timeout=5)


def main() -> None:
    parser = argparse.ArgumentParser(prog="cartographer")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_parser = sub.add_parser("ingest", help="Ingest a screenshot into a BaseLayout JSON.")
    ingest_parser.add_argument("--in", dest="input", required=True, type=Path, metavar="PATH")
    ingest_parser.add_argument("--out", dest="output", type=Path, default=None, metavar="PATH")

    calibrate_parser = sub.add_parser(
        "calibrate",
        help="Run the HITL calibration workflow against one or more screenshots.",
    )
    calibrate_parser.add_argument(
        "--in", dest="inputs", required=True, nargs="+", type=Path, metavar="PATH"
    )

    args = parser.parse_args()

    if args.command == "ingest":
        pipeline.run(args.input, args.output)
    elif args.command == "calibrate":
        _run_calibrate(args.inputs)
