"""Integration tests for the cartographer pipeline on hand-labelled fixtures.

Each fixture is a paired `<name>.jpg` + `<name>.json` in
`app/data/cartographer_eval/`. The `.json` is the ground-truth `BaseLayout`
exported from the sandbox-web editor; `pipeline.run()` is invoked against the
screenshot and the produced layout is compared to ground truth.

Both pred and GT are re-centered (mean of non-wall origins → `(22, 22)`)
before comparison, matching the cartographer pipeline's frame-commit
convention in `cartographer/align.py`. This isolates pipeline accuracy from
labelling-frame choices.

These tests are gated on `@pytest.mark.slow` and
`@pytest.mark.requires_roboflow_api_key`, so they skip cleanly in pre-commit
and when `ROBOFLOW_API_KEY` is unset (see `conftest.py`). When run, each
fixture costs one Roboflow inference call.

Note on AC-C3: the parent issue text reads "≥90% F1 on building class, ≥95%
IoU on bounding box". Bbox IoU cannot be measured here because the
hand-labelled GT is tile-origin based, not bbox-based — annotating bboxes is
out of scope for issue #31. Per-class F1 is enforced in
`test_ac_c3_class_f1`; bbox-IoU coverage would need a separate annotation
pass. AC-C4 already covers positional precision via tile-distance drift, so
the gap is small in practice.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sandbox_core.schemas import BaseLayout

from cartographer import pipeline

from ._metrics import class_f1, max_origin_drift, recenter, wall_precision_recall

_REPO_ROOT = Path(__file__).resolve().parents[3]
_EVAL_DIR = _REPO_ROOT / "app" / "data" / "cartographer_eval"

_FIXTURE_NAMES: tuple[str, ...] = (
    "th6_eval_01",
    "th6_eval_02",
    "th6_eval_03",
    "th6_eval_04",
    "th6_eval_05",
)

_AC_C3_MIN_F1 = 0.90
_AC_C4_MAX_DRIFT_TILES = 0.5
_AC_C5_MIN_WALL_PRECISION = 0.95
_AC_C5_MIN_WALL_RECALL = 0.90

pytestmark = [pytest.mark.slow, pytest.mark.requires_roboflow_api_key]


@pytest.fixture(scope="module", params=_FIXTURE_NAMES)
def ingested(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[str, BaseLayout, BaseLayout, Path]:
    """Run `pipeline.run()` once per fixture name and return (name, pred, gt, path).

    Module-scoped + parametrized: pytest creates one fixture instance per
    param (5 total), each shared across tests in this module. Net cost: 5
    Roboflow calls per full run.
    """
    name: str = request.param
    screenshot = _EVAL_DIR / f"{name}.jpg"
    gt_path = _EVAL_DIR / f"{name}.json"
    if not screenshot.exists():
        pytest.fail(f"missing eval screenshot: {screenshot}")
    if not gt_path.exists():
        pytest.fail(f"missing GT layout: {gt_path}")

    out_dir = tmp_path_factory.mktemp(f"cartographer_eval_{name}")
    out_path = out_dir / f"{name}.json"
    layout = pipeline.run(screenshot, out_path=out_path)

    gt = BaseLayout.model_validate_json(gt_path.read_text(encoding="utf-8"))
    return name, layout, gt, out_path


def test_ac_c1_pydantic_round_trip(
    ingested: tuple[str, BaseLayout, BaseLayout, Path],
) -> None:
    """AC-C1: every successful ingestion produces a `BaseLayout` that loads cleanly."""
    name, layout, _, out_path = ingested
    written = BaseLayout.model_validate_json(out_path.read_text(encoding="utf-8"))
    assert written.schema_version == layout.schema_version, name
    assert written.placements == layout.placements, name
    assert written.traps == layout.traps, name


def test_ac_c3_class_f1(
    ingested: tuple[str, BaseLayout, BaseLayout, Path],
) -> None:
    """AC-C3 (per-class F1 ≥ 0.9) on building placements after centroid alignment."""
    name, layout, gt, _ = ingested
    pred = recenter(layout.placements)
    truth = recenter(gt.placements)
    f1s = class_f1(pred, truth, tile_tolerance=1)
    failing = {cls: round(f, 3) for cls, f in f1s.items() if f < _AC_C3_MIN_F1}
    assert not failing, (
        f"{name}: classes below F1 {_AC_C3_MIN_F1}: {failing}; full table: "
        f"{ {cls: round(f, 3) for cls, f in f1s.items()} }"
    )


def test_ac_c4_grid_alignment(
    ingested: tuple[str, BaseLayout, BaseLayout, Path],
) -> None:
    """AC-C4: each pred placement within ±0.5 tile of nearest same-class GT.

    With integer tile origins after centring, the practical bar is exact match.
    """
    name, layout, gt, _ = ingested
    pred = recenter(layout.placements)
    truth = recenter(gt.placements)
    drift = max_origin_drift(pred, truth)
    assert drift >= 0.0, f"{name}: pred contains a class absent from GT (drift sentinel -1)"
    assert drift <= _AC_C4_MAX_DRIFT_TILES, (
        f"{name}: max placement drift {drift} tiles > {_AC_C4_MAX_DRIFT_TILES}"
    )


def test_ac_c5_walls(
    ingested: tuple[str, BaseLayout, BaseLayout, Path],
) -> None:
    """AC-C5: wall precision ≥ 0.95, recall ≥ 0.90 on tile-set match."""
    name, layout, gt, _ = ingested
    pred = recenter(layout.placements)
    truth = recenter(gt.placements)
    precision, recall = wall_precision_recall(pred, truth)
    assert precision >= _AC_C5_MIN_WALL_PRECISION, (
        f"{name}: wall precision {precision:.3f} < {_AC_C5_MIN_WALL_PRECISION}"
    )
    assert recall >= _AC_C5_MIN_WALL_RECALL, (
        f"{name}: wall recall {recall:.3f} < {_AC_C5_MIN_WALL_RECALL}"
    )


def test_ac_c7_provenance_round_trip(
    ingested: tuple[str, BaseLayout, BaseLayout, Path],
) -> None:
    """AC-C7: provenance is fully populated and round-trips through Pydantic."""
    name, layout, _, out_path = ingested
    p = layout.provenance
    assert p is not None, name
    assert p.source_screenshot, name
    assert p.ingest_timestamp_utc, name
    assert p.dataset_version, name
    assert p.confidence_threshold > 0.0, name
    assert p.derived_pitch_px > 0.0, name
    assert p.derived_origin_px is not None, name
    assert p.per_placement_confidence, name

    written = BaseLayout.model_validate_json(out_path.read_text(encoding="utf-8"))
    assert written.provenance == layout.provenance, name
