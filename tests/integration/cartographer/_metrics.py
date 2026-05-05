"""Metrics for comparing a cartographer-produced BaseLayout to ground truth.

Operates on `BuildingPlacement` lists where `origin` is `(col, row)`. All
comparison helpers expect the inputs to already be re-centered so the mean of
non-wall origins lands at `(22, 22)` — matching the cartographer pipeline's
frame-commit convention in `cartographer/align.py`. Use `recenter()` to
normalize before comparing.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from sandbox_core.schemas import BuildingPlacement

_CENTROID_TARGET: tuple[int, int] = (22, 22)


def recenter(placements: Sequence[BuildingPlacement]) -> list[BuildingPlacement]:
    """Translate `placements` so the mean of non-wall origins is at (22, 22).

    Matches `cartographer.align.run`'s integer-shift centering, so re-centred
    pred and GT can be compared directly.
    """
    non_walls = [p for p in placements if p.building_type != "wall"]
    if not non_walls:
        return list(placements)
    cx = sum(p.origin[0] for p in non_walls) / len(non_walls)
    cy = sum(p.origin[1] for p in non_walls) / len(non_walls)
    dx = round(_CENTROID_TARGET[0] - cx)
    dy = round(_CENTROID_TARGET[1] - cy)
    if dx == 0 and dy == 0:
        return list(placements)
    return [
        BuildingPlacement(
            building_type=p.building_type,
            origin=(p.origin[0] + dx, p.origin[1] + dy),
            level=p.level,
        )
        for p in placements
    ]


def class_f1(
    pred: Sequence[BuildingPlacement],
    gt: Sequence[BuildingPlacement],
    *,
    tile_tolerance: int = 1,
) -> dict[str, float]:
    """Per-non-wall-class F1.

    A predicted `(class, origin)` is a true positive iff there is an unused
    same-class GT origin within Chebyshev distance `<= tile_tolerance`. Each
    GT origin matches at most one pred. Walls are excluded — measure those
    via `wall_precision_recall`.
    """
    pred_by_class: dict[str, list[tuple[int, int]]] = defaultdict(list)
    gt_by_class: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for p in pred:
        if p.building_type == "wall":
            continue
        pred_by_class[p.building_type].append(p.origin)
    for p in gt:
        if p.building_type == "wall":
            continue
        gt_by_class[p.building_type].append(p.origin)

    f1s: dict[str, float] = {}
    for cls in set(pred_by_class) | set(gt_by_class):
        preds = pred_by_class[cls]
        gts = gt_by_class[cls]
        used = [False] * len(gts)
        tp = 0
        for px, py in preds:
            for i, (gx, gy) in enumerate(gts):
                if used[i]:
                    continue
                if max(abs(px - gx), abs(py - gy)) <= tile_tolerance:
                    used[i] = True
                    tp += 1
                    break
        fp = len(preds) - tp
        fn = len(gts) - tp
        precision = tp / (tp + fp) if (tp + fp) else 1.0
        recall = tp / (tp + fn) if (tp + fn) else 1.0
        f1s[cls] = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )
    return f1s


def max_origin_drift(
    pred: Sequence[BuildingPlacement],
    gt: Sequence[BuildingPlacement],
) -> float:
    """Max Chebyshev distance from each non-wall pred to nearest same-class GT.

    Returns -1.0 if any predicted class is absent from GT (a categorical miss
    that the drift metric cannot represent — surface as a hard failure in the
    test).
    """
    gt_by_class: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for p in gt:
        if p.building_type == "wall":
            continue
        gt_by_class[p.building_type].append(p.origin)
    max_d = 0.0
    for p in pred:
        if p.building_type == "wall":
            continue
        gts = gt_by_class.get(p.building_type, [])
        if not gts:
            return -1.0
        d = float(min(max(abs(p.origin[0] - gx), abs(p.origin[1] - gy)) for gx, gy in gts))
        if d > max_d:
            max_d = d
    return max_d


def wall_precision_recall(
    pred: Sequence[BuildingPlacement],
    gt: Sequence[BuildingPlacement],
) -> tuple[float, float]:
    """(precision, recall) on the set of wall tile origins."""
    pred_walls = {p.origin for p in pred if p.building_type == "wall"}
    gt_walls = {p.origin for p in gt if p.building_type == "wall"}
    if not pred_walls and not gt_walls:
        return (1.0, 1.0)
    tp = len(pred_walls & gt_walls)
    precision = tp / len(pred_walls) if pred_walls else 1.0
    recall = tp / len(gt_walls) if gt_walls else 1.0
    return precision, recall
