import type { BuildingPlacement } from "@/generated_types";
import { footprintFor } from "@/render/footprints";
import { BUILDABLE_MIN, BUILDABLE_MAX_EXCLUSIVE } from "@/render/projection";

export interface ConstraintResult {
  label: string;
  passing: boolean;
  conflictingIndices: number[];
}

export function validateLayout(placements: BuildingPlacement[]): ConstraintResult[] {
  return [
    checkTH(placements),
    checkWalls(placements),
    checkOverlap(placements),
    checkBuildableRegion(placements),
  ];
}

function checkTH(placements: BuildingPlacement[]): ConstraintResult {
  const indices = placements
    .map((p, i) => (p.building_type === "town_hall" ? i : -1))
    .filter((i) => i !== -1);
  return {
    label: `TH placed (${indices.length}/1 required)`,
    passing: indices.length === 1,
    conflictingIndices: indices.length !== 1 ? indices : [],
  };
}

function checkWalls(placements: BuildingPlacement[]): ConstraintResult {
  const wallIndices = placements
    .map((p, i) => (p.building_type === "wall" ? i : -1))
    .filter((i) => i !== -1);
  const count = wallIndices.length;
  const passing = count <= 75;
  return {
    label: `Walls ${count}/75`,
    passing,
    conflictingIndices: passing ? [] : wallIndices.slice(75),
  };
}

function tileSet(placements: BuildingPlacement[]): Map<string, number> {
  const map = new Map<string, number>();
  for (let i = 0; i < placements.length; i++) {
    const { building_type, origin } = placements[i];
    const [rows, cols] = footprintFor(building_type);
    for (let r = origin[0]; r < origin[0] + rows; r++) {
      for (let c = origin[1]; c < origin[1] + cols; c++) {
        const key = `${r},${c}`;
        if (!map.has(key)) map.set(key, i);
      }
    }
  }
  return map;
}

function checkOverlap(placements: BuildingPlacement[]): ConstraintResult {
  const seen = new Map<string, number>();
  const conflicting = new Set<number>();
  for (let i = 0; i < placements.length; i++) {
    const { building_type, origin } = placements[i];
    const [rows, cols] = footprintFor(building_type);
    for (let r = origin[0]; r < origin[0] + rows; r++) {
      for (let c = origin[1]; c < origin[1] + cols; c++) {
        const key = `${r},${c}`;
        const prev = seen.get(key);
        if (prev !== undefined) {
          conflicting.add(prev);
          conflicting.add(i);
        } else {
          seen.set(key, i);
        }
      }
    }
  }
  return {
    label: "No footprint overlap",
    passing: conflicting.size === 0,
    conflictingIndices: Array.from(conflicting),
  };
}

function checkBuildableRegion(placements: BuildingPlacement[]): ConstraintResult {
  const conflicting: number[] = [];
  for (let i = 0; i < placements.length; i++) {
    const { building_type, origin } = placements[i];
    const [rows, cols] = footprintFor(building_type);
    const rowEnd = origin[0] + rows;
    const colEnd = origin[1] + cols;
    if (
      origin[0] < BUILDABLE_MIN ||
      origin[1] < BUILDABLE_MIN ||
      rowEnd > BUILDABLE_MAX_EXCLUSIVE ||
      colEnd > BUILDABLE_MAX_EXCLUSIVE
    ) {
      conflicting.push(i);
    }
  }
  return {
    label: "All footprints inside buildable region",
    passing: conflicting.length === 0,
    conflictingIndices: conflicting,
  };
}
