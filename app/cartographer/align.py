"""Stage 4: snap Roboflow detections to integer grid tiles."""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from cartographer.detect import Detection
from cartographer.grid import ISO_ANGLE_1, ISO_ANGLE_2

_logger = logging.getLogger("cartographer")

_BUILDINGS_PATH = Path(__file__).parent.parent / "data" / "buildings.json"
_GRID_SIZE = 44
_CENTROID_TARGET = 22

# Traps that exist as Roboflow classes but are absent from buildings.json.
_TRAP_FOOTPRINTS: dict[str, tuple[int, int]] = {
    "bomb": (1, 1),
    "giant_bomb": (2, 2),
    "spring_trap": (1, 1),
    "air_bomb": (1, 1),
}


class OverlapError(ValueError):
    """Raised when two placed footprints share a tile."""


class BoundaryError(ValueError):
    """Raised when centering clips the 44x44 grid."""


class ReverseProjectionError(ValueError):
    """Raised when the reverse-projected anchor exceeds 0.5 tile from observed."""


def _load_footprints() -> dict[str, tuple[int, int]]:
    data = json.loads(_BUILDINGS_PATH.read_text(encoding="utf-8"))
    fp: dict[str, tuple[int, int]] = {
        e["name"]: (e["footprint"][0], e["footprint"][1])
        for e in data["entries"]
        if "name" in e
    }
    fp.update(_TRAP_FOOTPRINTS)
    return fp


_FOOTPRINTS: dict[str, tuple[int, int]] = _load_footprints()


@dataclass(frozen=True)
class AlignedPlacement:
    class_name: str
    origin: tuple[int, int]
    footprint: tuple[int, int]
    confidence: float


def _basis_matrix(pitch: float) -> np.ndarray:
    """2x2 matrix where result @ [col, row]^T = pixel offset from grid origin."""
    v1 = np.array([math.cos(ISO_ANGLE_1), math.sin(ISO_ANGLE_1)]) * pitch
    v2 = np.array([math.cos(ISO_ANGLE_2), math.sin(ISO_ANGLE_2)]) * pitch
    return np.column_stack([v1, v2])


def run(
    detections: list[Detection],
    pitch: float,
    origin: tuple[float, float],
    offsets: dict[str, tuple[float, float]] | None = None,
) -> list[AlignedPlacement]:
    """Snap each detection to an integer grid tile origin.

    Args:
        detections: Accepted detections from the detect stage.
        pitch: Tile pitch in pixels from the grid stage.
        origin: Grid origin pixel (ox, oy) from the grid stage.
        offsets: Per-class footprint-center calibration offsets from calibration.load_offsets().
                 Pass None or {} to use zero offsets for all classes.

    Raises:
        OverlapError: Two placed footprints share a tile.
        BoundaryError: Centering the hull centroid at (22, 22) clips the grid.
        ReverseProjectionError: Reverse-projected anchor exceeds 0.5 tile.
    """
    if not detections:
        return []

    if offsets is None:
        offsets = {}

    mat = _basis_matrix(pitch)
    mat_inv: np.ndarray = np.linalg.inv(mat)
    ox, oy = origin

    warned_this_run: set[str] = set()
    placements: list[AlignedPlacement] = []

    for det in detections:
        x1, _y1, x2, y2 = det.bbox_xyxy
        # Start from the detector box's bottom-center, then apply calibration so
        # the anchor represents the center of the building's footprint.
        anchor_x = (x1 + x2) / 2.0
        anchor_y = float(y2)

        # Apply per-class calibration offset (warns once per class per ingest)
        if offsets and det.class_name not in offsets and det.class_name not in warned_this_run:
            _logger.warning(
                "cartographer.align: no calibration offset for class %s, using (0, 0)",
                det.class_name,
            )
            warned_this_run.add(det.class_name)
        dx, dy = offsets.get(det.class_name, (0.0, 0.0))
        anchor_x += dx
        anchor_y += dy

        # Convert footprint-center pixel to fractional tile coords (col, row).
        delta = np.array([anchor_x - ox, anchor_y - oy], dtype=float)
        cr = mat_inv @ delta
        col_frac, row_frac = float(cr[0]), float(cr[1])

        # Footprint dimensions are in tile counts. The calibrated center is at
        # origin + footprint / 2. For 2x2 and 4x4 this is the shared inner tile
        # border; for 3x3 this is the center of the middle tile.
        fp = _FOOTPRINTS.get(det.class_name, (3, 3))
        cols, rows = fp

        col0_frac = col_frac - cols / 2.0
        row0_frac = row_frac - rows / 2.0

        col0 = round(col0_frac)
        row0 = round(row0_frac)

        # Reverse-project to validate (predicted center should be within 0.5 tile)
        pred_cr = np.array([col0 + cols / 2.0, row0 + rows / 2.0], dtype=float)
        pred_delta = mat @ pred_cr
        pred_anchor_x = ox + float(pred_delta[0])
        pred_anchor_y = oy + float(pred_delta[1])
        dist = math.hypot(pred_anchor_x - anchor_x, pred_anchor_y - anchor_y)
        if dist > 0.5 * pitch:
            raise ReverseProjectionError(
                f"{det.class_name}: reverse-projection error {dist:.2f}px "
                f"> 0.5 * pitch ({0.5 * pitch:.2f}px); "
                f"anchor={anchor_x:.1f},{anchor_y:.1f} "
                f"predicted={pred_anchor_x:.1f},{pred_anchor_y:.1f}"
            )

        placements.append(
            AlignedPlacement(
                class_name=det.class_name,
                origin=(col0, row0),
                footprint=fp,
                confidence=det.confidence,
            )
        )

    # Detect overlapping footprints
    occupied: dict[tuple[int, int], str] = {}
    for p in placements:
        c0, r0 = p.origin
        cols, rows = p.footprint
        for dc in range(cols):
            for dr in range(rows):
                tile = (c0 + dc, r0 + dr)
                if tile in occupied:
                    raise OverlapError(
                        f"Tile {tile} is occupied by both {occupied[tile]} and {p.class_name}"
                    )
                occupied[tile] = p.class_name

    # Center convex-hull centroid at (CENTROID_TARGET, CENTROID_TARGET)
    origins = np.array([p.origin for p in placements], dtype=float)
    centroid = origins.mean(axis=0)
    shift_col = round(_CENTROID_TARGET - centroid[0])
    shift_row = round(_CENTROID_TARGET - centroid[1])

    centered: list[AlignedPlacement] = []
    for p in placements:
        c0, r0 = p.origin
        cols, rows = p.footprint
        new_c0 = c0 + shift_col
        new_r0 = r0 + shift_row
        if (
            new_c0 < 0
            or new_r0 < 0
            or new_c0 + cols > _GRID_SIZE
            or new_r0 + rows > _GRID_SIZE
        ):
            raise BoundaryError(
                f"{p.class_name}: origin ({new_c0}, {new_r0}) footprint {cols}x{rows} "
                f"clips the {_GRID_SIZE}x{_GRID_SIZE} grid after centering"
            )
        centered.append(
            AlignedPlacement(
                class_name=p.class_name,
                origin=(new_c0, new_r0),
                footprint=p.footprint,
                confidence=p.confidence,
            )
        )

    return centered
