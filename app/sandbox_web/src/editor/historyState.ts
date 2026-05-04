import type { BuildingPlacement } from "@/generated_types";

export interface HistoryState {
  past: BuildingPlacement[][];
  present: BuildingPlacement[];
  future: BuildingPlacement[][];
}

const MAX_HISTORY = 50;

export function createHistoryState(initial: BuildingPlacement[] = []): HistoryState {
  return { past: [], present: initial, future: [] };
}

export function pushHistory(state: HistoryState, next: BuildingPlacement[]): HistoryState {
  const past = [...state.past, state.present].slice(-MAX_HISTORY);
  return { past, present: next, future: [] };
}

export function undo(state: HistoryState): HistoryState {
  if (state.past.length === 0) return state;
  const past = state.past.slice(0, -1);
  const present = state.past[state.past.length - 1];
  const future = [state.present, ...state.future];
  return { past, present, future };
}

export function redo(state: HistoryState): HistoryState {
  if (state.future.length === 0) return state;
  const [present, ...future] = state.future;
  const past = [...state.past, state.present];
  return { past, present, future };
}

export function canUndo(state: HistoryState): boolean {
  return state.past.length > 0;
}

export function canRedo(state: HistoryState): boolean {
  return state.future.length > 0;
}
