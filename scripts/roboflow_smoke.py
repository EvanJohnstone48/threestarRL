"""One-shot smoke test for the Roboflow inference key.

Verifies that `ROBOFLOW_API_KEY` can reach the underlying detection model
(`home-village-building-detector/3`) — the same model the cartographer's
`detect` stage will call. The Roboflow workflow wrapper
(`detect-count-and-visualize`) only adds annotated-image / count outputs that
the cartographer already produces itself in `diagnostic.py`, so the model
endpoint is the right surface to gate on.

Run:
    python scripts/roboflow_smoke.py
"""

from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

import requests

MODEL = "home-village-building-detector/3"
ENDPOINT = f"https://detect.roboflow.com/{MODEL}"
IMAGE = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "cartographer"
    / "resources"
    / "roboflow_example_fullimage.png"
)


def _load_api_key() -> str:
    key = os.environ.get("ROBOFLOW_API_KEY")
    if key:
        return key
    env_file = Path(__file__).resolve().parents[1] / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("ROBOFLOW_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("ROBOFLOW_API_KEY not set and not found in .env")


def main() -> int:
    api_key = _load_api_key()
    if not IMAGE.exists():
        sys.exit(f"missing test image: {IMAGE}")

    b64 = base64.b64encode(IMAGE.read_bytes()).decode("ascii")
    print(f"POST {ENDPOINT}")
    print(f"image: {IMAGE.name} ({IMAGE.stat().st_size} bytes)")
    resp = requests.post(
        ENDPOINT,
        params={"api_key": api_key},
        data=b64,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=60,
    )
    if resp.status_code != 200:
        print(f"HTTP {resp.status_code}: {resp.text[:500]}")
        return 1

    data = resp.json()
    preds = data.get("predictions") or []
    img_meta = data.get("image") or {}
    print(f"HTTP 200  image={img_meta.get('width')}x{img_meta.get('height')}")
    print(f"predictions: {len(preds)}")

    classes: dict[str, int] = {}
    confs: list[float] = []
    for p in preds:
        cls = p.get("class") or "?"
        classes[cls] = classes.get(cls, 0) + 1
        c = p.get("confidence")
        if isinstance(c, (int, float)):
            confs.append(float(c))
    for cls, n in sorted(classes.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {cls}: {n}")
    if confs:
        print(
            f"confidence: min={min(confs):.3f} mean={sum(confs)/len(confs):.3f} max={max(confs):.3f}"
        )
    print("OK — API key is valid and model is reachable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
