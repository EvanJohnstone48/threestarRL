import type { TickFrame } from "@/generated_types";

export type SelectedEntity =
  | { kind: "building"; id: number }
  | { kind: "troop"; id: number }
  | null;

export interface InspectorData {
  kind: "building" | "troop";
  id: number;
  entityType: string;
  level: number;
  hp: number;
  maxHp: number;
  position: [number, number];
  destroyed: boolean;
}

// Derive inspector display data for the selected entity from the current frame.
// Returns null if nothing is selected or the entity is missing from the frame.
export function getInspectorData(
  selection: SelectedEntity,
  frame: TickFrame | null,
): InspectorData | null {
  if (!selection || !frame) return null;
  if (selection.kind === "building") {
    const b = frame.state.buildings.find((b) => b.id === selection.id);
    if (!b) return null;
    return {
      kind: "building",
      id: b.id,
      entityType: b.building_type,
      level: b.level,
      hp: b.hp,
      maxHp: b.max_hp,
      position: b.origin,
      destroyed: b.destroyed,
    };
  } else {
    const t = frame.state.troops.find((t) => t.id === selection.id);
    if (!t) return null;
    return {
      kind: "troop",
      id: t.id,
      entityType: t.troop_type,
      level: t.level,
      hp: t.hp,
      maxHp: t.max_hp,
      position: t.position,
      destroyed: t.destroyed,
    };
  }
}
