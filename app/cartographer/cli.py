"""CLI: python -m cartographer ingest --in <screenshot> [--out <path>]
              python -m cartographer calibrate [--in <path>...]
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import threading
import webbrowser
from pathlib import Path
from urllib.parse import urlencode

from cartographer import pipeline

_DEFAULT_FRONTEND_URL = "http://localhost:5173/"
_DEFAULT_CALIBRATION_DIR = Path(__file__).parent.parent / "data" / "base_screenshots"
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _frontend_url(mode: str, api_port: int) -> str:
    base = os.environ.get("SANDBOX_WEB_URL", _DEFAULT_FRONTEND_URL).rstrip("/") + "/"
    query = urlencode(
        {
            "tab": "cartographer",
            "mode": mode,
            "api": f"http://127.0.0.1:{api_port}",
        }
    )
    return f"{base}?{query}"


def _expand_calibration_inputs(inputs: list[Path] | None) -> list[Path]:
    paths = inputs or [_DEFAULT_CALIBRATION_DIR]
    expanded: list[Path] = []
    for path in paths:
        if path.is_dir():
            expanded.extend(
                p for p in sorted(path.iterdir()) if p.is_file() and p.suffix.lower() in _IMAGE_EXTENSIONS
            )
        else:
            expanded.append(path)
    return expanded


def _run_calibrate(screenshot_paths: list[Path]) -> None:
    import uvicorn

    from cartographer import detect, preprocess
    from cartographer.server import ScreenshotEntry, create_app

    config_path = Path(__file__).parent.parent / "data" / "cartographer_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    api_key = os.environ.get("ROBOFLOW_API_KEY", "")

    expanded_paths = _expand_calibration_inputs(screenshot_paths)
    if not expanded_paths:
        raise SystemExit("No calibration screenshots found.")

    entries: list[ScreenshotEntry] = []
    for p in expanded_paths:
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
    url = _frontend_url("calibrate", port)

    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait briefly for the server to start before opening the browser.
    import time
    time.sleep(0.5)
    print(f"Cartographer API server running on http://127.0.0.1:{port}")
    print(f"Loaded {len(entries)} calibration screenshot(s).")
    print(f"Opening calibration UI: {url}")
    print("Waiting for Save & exit in the browser...")
    webbrowser.open(url)

    shutdown_event.wait()
    server.should_exit = True
    thread.join(timeout=5)


def _run_review(screenshot_path: Path, out_path: Path | None) -> None:
    import uvicorn
    from sandbox_core.schemas import (
        BaseLayout,
        BaseLayoutMetadata,
        BuildingPlacement,
        CartographerProvenance,
        TrapPlacement,
    )

    from cartographer import pipeline
    from cartographer.detect import TRAP_CLASSES
    from cartographer.server import create_review_app

    image, _accepted, _sub_threshold, pitch, origin, placements, _diag_path, cfg = (
        pipeline.run_to_align(screenshot_path, out_path)
    )

    if out_path is None:
        out_path = (
            Path(__file__).parent.parent
            / "data"
            / "scraped_bases"
            / (screenshot_path.stem + ".json")
        )

    # Build candidate BaseLayout from aligned placements
    building_placements: list[BuildingPlacement] = []
    trap_placements: list[TrapPlacement] = []
    for p in placements:
        if p.class_name in TRAP_CLASSES:
            trap_placements.append(TrapPlacement(trap_type=p.class_name, origin=p.origin))
        else:
            building_placements.append(BuildingPlacement(building_type=p.class_name, origin=p.origin))

    per_conf = {f"{p.class_name}_{i}": p.confidence for i, p in enumerate(placements)}
    candidate_layout = BaseLayout(
        metadata=BaseLayoutMetadata(name=screenshot_path.stem, th_level=6),
        th_level=6,
        placements=building_placements,
        traps=trap_placements,
        provenance=CartographerProvenance(
            source_screenshot=str(screenshot_path),
            ingest_timestamp_utc=__import__("datetime").datetime.now(
                __import__("datetime").UTC
            ).isoformat(),
            dataset_version=str(cfg["dataset_version"]),
            confidence_threshold=float(cfg["confidence_threshold"]),
            derived_pitch_px=pitch,
            derived_origin_px=(origin[0], origin[1]),
            per_placement_confidence=per_conf,
        ),
    )

    shutdown_event = threading.Event()
    app = create_review_app(
        screenshot_path=screenshot_path,
        candidate_layout=candidate_layout,
        derived_pitch_px=pitch,
        derived_origin_px=origin,
        image=image,
        out_path=out_path,
        config=cfg,
        shutdown_event=shutdown_event,
    )

    port = _free_port()
    url = _frontend_url("review", port)

    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    import time
    time.sleep(0.5)
    print(f"Cartographer API server running on http://127.0.0.1:{port}")
    print(f"Opening review UI: {url}")
    print("Waiting for Save corrected layout in the browser...")
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
    ingest_parser.add_argument(
        "--review",
        action="store_true",
        default=False,
        help="Open the review UI before writing the final JSON.",
    )

    calibrate_parser = sub.add_parser(
        "calibrate",
        help="Run the HITL calibration workflow against one or more screenshots.",
    )
    calibrate_parser.add_argument(
        "--in",
        dest="inputs",
        required=False,
        nargs="+",
        type=Path,
        metavar="PATH",
        help="Screenshot file(s) or folder(s). Defaults to app/data/base_screenshots.",
    )

    args = parser.parse_args()

    if args.command == "ingest":
        if args.review:
            _run_review(args.input, args.output)
        else:
            pipeline.run(args.input, args.output)
    elif args.command == "calibrate":
        _run_calibrate(args.inputs)
