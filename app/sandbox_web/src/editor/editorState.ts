import type { BuildingPlacement } from "@/generated_types";
import { footprintFor } from "@/render/footprints";
import { BUILDABLE_MIN, BUILDABLE_MAX_EXCLUSIVE, GRID_SIZE } from "@/render/projection";
import { TH6_CAPS } from "./th6Caps";

export type PlaceResult = "placed" | "illegal" | "cap_exceeded";
export type GhostLegality = "legal" | "overlap" | "out_of_bounds" | "cap_exceeded";
export type PaintResult = "painted" | "capped" | "noop";
export type EditorMode = "idle" | "placing" | "painting" | "erasing";

export interface EditorState {
  mode: EditorMode;
  selectedType: string | null;
  placements: BuildingPlacement[];
  paintStart: [number, number] | null;
}

export function createEditorState(): EditorState {
  return { mode: "idle", selectedType: null, placements: [], paintStart: null };
}

export function enterPlaceMode(state: EditorState, type: string): EditorState {
  return { ...state, mode: "placing", selectedType: type, paintStart: null };
}

export function exitPlaceMode(state: EditorState): EditorState {
  return exitCurrentMode(state);
}

export function exitCurrentMode(state: EditorState): EditorState {
  return { ...state, mode: "idle", selectedType: null, paintStart: null };
}

export function enterPaintMode(state: EditorState): EditorState {
  return { ...state, mode: "painting", selectedType: null, paintStart: null };
}

export function enterEraseMode(state: EditorState): EditorState {
  return { ...state, mode: "erasing", selectedType: null, paintStart: null };
}

export function startPaintDrag(state: EditorState, tile: [number, number]): EditorState {
  if (state.mode !== "painting") return state;
  return { ...state, paintStart: tile };
}

export function commitWallPaint(
  state: EditorState,
  endTile: [number, number],
): [EditorState, PaintResult] {
  if (state.mode !== "painting" || state.paintStart === null) {
    return [state, "noop"];
  }

  const tiles = resolveOrthoLine(state.paintStart, endTile);

  const existingWallKeys = new Set<string>(
    state.placements
      .filter((p) => p.building_type === "wall")
      .map((p) => `${p.origin[0]},${p.origin[1]}`),
  );

  const newTiles = tiles.filter(([r, c]) => !existingWallKeys.has(`${r},${c}`));

  const currentWallCount = existingWallKeys.size;
  const remaining = 75 - currentWallCount;

  const cleared = { ...state, paintStart: null };

  if (newTiles.length === 0) return [cleared, "noop"];
  if (remaining <= 0) return [cleared, "capped"];

  const tilesToAdd = newTiles.slice(0, remaining);
  const capped = tilesToAdd.length < newTiles.length;

  const newPlacements = [
    ...state.placements,
    ...tilesToAdd.map(([r, c]) => ({
      building_type: "wall",
      origin: [r, c] as [number, number],
      level: 1,
    })),
  ];

  return [{ ...cleared, placements: newPlacements }, capped ? "capped" : "painted"];
}

export function eraseAtTile(state: EditorState, tile: [number, number]): EditorState {
  const [tr, tc] = tile;
  for (let i = 0; i < state.placements.length; i++) {
    const p = state.placements[i];
    const [rows, cols] = footprintFor(p.building_type);
    if (tr >= p.origin[0] && tr < p.origin[0] + rows && tc >= p.origin[1] && tc < p.origin[1] + cols) {
      return removeBuilding(state, i);
    }
  }
  return state;
}

// Resolves the orthogonal path between two tiles.
// Axial: straight horizontal or vertical line.
// Non-axial: L-shape, horizontal-first when |dc| >= |dr|, vertical-first otherwise.
export function resolveOrthoLine(
  from: [number, number],
  to: [number, number],
): [number, number][] {
  const [r1, c1] = from;
  const [r2, c2] = to;
  const dr = Math.abs(r2 - r1);
  const dc = Math.abs(c2 - c1);

  if (dr === 0 && dc === 0) return [[r1, c1]];
  if (dr === 0) return _lineH(r1, c1, c2);
  if (dc === 0) return _lineV(r1, r2, c1);

  if (dc >= dr) {
    // horizontal leg then vertical leg
    const leg1 = _lineH(r1, c1, c2);
    const leg2 = _lineV(r1, r2, c2);
    return [...leg1, ...leg2.slice(1)];
  } else {
    // vertical leg then horizontal leg
    const leg1 = _lineV(r1, r2, c1);
    const leg2 = _lineH(r2, c1, c2);
    return [...leg1, ...leg2.slice(1)];
  }
}

function _lineH(row: number, c1: number, c2: number): [number, number][] {
  const tiles: [number, number][] = [];
  const step = c2 >= c1 ? 1 : -1;
  for (let c = c1; step > 0 ? c <= c2 : c >= c2; c += step) {
    tiles.push([row, c]);
  }
  return tiles;
}

function _lineV(r1: number, r2: number, col: number): [number, number][] {
  const tiles: [number, number][] = [];
  const step = r2 >= r1 ? 1 : -1;
  for (let r = r1; step > 0 ? r <= r2 : r >= r2; r += step) {
    tiles.push([r, col]);
  }
  return tiles;
}

export function placeBuildingAt(
  state: EditorState,
  origin: [number, number],
): [EditorState, PlaceResult] {
  if (state.mode !== "placing" || state.selectedType === null) {
    return [state, "illegal"];
  }
  const type = state.selectedType;
  const legality = _checkLegality(type, origin, state.placements);
  if (legality === "legal") {
    const placement: BuildingPlacement = { building_type: type, origin, level: 1 };
    return [{ ...state, placements: [...state.placements, placement] }, "placed"];
  }
  if (legality === "cap_exceeded") return [state, "cap_exceeded"];
  return [state, "illegal"];
}

export function removeBuilding(state: EditorState, index: number): EditorState {
  if (index < 0 || index >= state.placements.length) return state;
  const placements = state.placements.filter((_, i) => i !== index);
  return { ...state, placements };
}

export function getGhostLegality(state: EditorState, origin: [number, number]): GhostLegality {
  if (state.mode !== "placing" || state.selectedType === null) return "legal";
  return _checkLegality(state.selectedType, origin, state.placements);
}

// ---------------------------------------------------------------------------
// Mass actions
// ---------------------------------------------------------------------------

export function clearAll(state: EditorState): EditorState {
  return { ...state, placements: [] };
}

export function mirrorHorizontal(placements: BuildingPlacement[]): BuildingPlacement[] {
  return placements.map((p) => {
    const [, cols] = footprintFor(p.building_type);
    return { ...p, origin: [p.origin[0], GRID_SIZE - p.origin[1] - cols] as [number, number] };
  });
}

export function mirrorVertical(placements: BuildingPlacement[]): BuildingPlacement[] {
  return placements.map((p) => {
    const [rows] = footprintFor(p.building_type);
    return { ...p, origin: [GRID_SIZE - p.origin[0] - rows, p.origin[1]] as [number, number] };
  });
}

// Rotates 90° clockwise around grid center (GRID_SIZE/2 - 0.5, GRID_SIZE/2 - 0.5).
// All TH6 footprints are square so the footprint dimensions are unchanged.
export function rotate90CW(placements: BuildingPlacement[]): BuildingPlacement[] {
  return placements.map((p) => {
    const [rows] = footprintFor(p.building_type); // square footprint: rows === cols
    const [r, c] = p.origin;
    return { ...p, origin: [c, GRID_SIZE - r - rows] as [number, number] };
  });
}

function _checkLegality(
  type: string,
  origin: [number, number],
  placements: BuildingPlacement[],
): GhostLegality {
  const [rows, cols] = footprintFor(type);

  // Bounds check
  if (
    origin[0] < BUILDABLE_MIN ||
    origin[1] < BUILDABLE_MIN ||
    origin[0] + rows > BUILDABLE_MAX_EXCLUSIVE ||
    origin[1] + cols > BUILDABLE_MAX_EXCLUSIVE
  ) {
    return "out_of_bounds";
  }

  // Cap check
  const cap = TH6_CAPS[type] ?? 0;
  const placed = placements.filter((p) => p.building_type === type).length;
  if (placed >= cap) return "cap_exceeded";

  // Overlap check
  const occupied = new Set<string>();
  for (const p of placements) {
    const [pr, pc] = footprintFor(p.building_type);
    for (let r = p.origin[0]; r < p.origin[0] + pr; r++) {
      for (let c = p.origin[1]; c < p.origin[1] + pc; c++) {
        occupied.add(`${r},${c}`);
      }
    }
  }
  for (let r = origin[0]; r < origin[0] + rows; r++) {
    for (let c = origin[1]; c < origin[1] + cols; c++) {
      if (occupied.has(`${r},${c}`)) return "overlap";
    }
  }

  return "legal";
}
