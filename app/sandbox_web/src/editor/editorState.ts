import type { BuildingPlacement } from "@/generated_types";
import { footprintFor } from "@/render/footprints";
import { BUILDABLE_MIN, BUILDABLE_MAX_EXCLUSIVE } from "@/render/projection";
import { TH6_CAPS } from "./th6Caps";

export type PlaceResult = "placed" | "illegal" | "cap_exceeded";
export type GhostLegality = "legal" | "overlap" | "out_of_bounds" | "cap_exceeded";

export interface EditorState {
  mode: "idle" | "placing";
  selectedType: string | null;
  placements: BuildingPlacement[];
}

export function createEditorState(): EditorState {
  return { mode: "idle", selectedType: null, placements: [] };
}

export function enterPlaceMode(state: EditorState, type: string): EditorState {
  return { ...state, mode: "placing", selectedType: type };
}

export function exitPlaceMode(state: EditorState): EditorState {
  return { ...state, mode: "idle", selectedType: null };
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
