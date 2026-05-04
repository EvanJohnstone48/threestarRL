import { describe, it, expect } from "vitest";
import { validateLayout } from "./validator";
import type { BuildingPlacement } from "@/generated_types";

function bp(building_type: string, origin: [number, number]): BuildingPlacement {
  return { building_type, origin, level: 1 };
}

describe("validateLayout — TH constraint", () => {
  it("fails when no TH placed", () => {
    const results = validateLayout([]);
    const th = results.find((r) => r.label.startsWith("TH placed"));
    expect(th?.passing).toBe(false);
  });

  it("passes when exactly one TH placed", () => {
    const results = validateLayout([bp("town_hall", [10, 10])]);
    const th = results.find((r) => r.label.startsWith("TH placed"));
    expect(th?.passing).toBe(true);
  });
});

describe("validateLayout — walls constraint", () => {
  it("passes with 0 walls", () => {
    const results = validateLayout([]);
    const walls = results.find((r) => r.label.startsWith("Walls"));
    expect(walls?.passing).toBe(true);
  });

  it("passes with exactly 75 walls", () => {
    const placements: BuildingPlacement[] = Array.from({ length: 75 }, (_, i) =>
      bp("wall", [3, 3 + i]),
    );
    const results = validateLayout(placements);
    const walls = results.find((r) => r.label.startsWith("Walls"));
    expect(walls?.passing).toBe(true);
  });

  it("fails with 76 walls", () => {
    const placements: BuildingPlacement[] = Array.from({ length: 76 }, (_, i) =>
      bp("wall", [3, 3 + i]),
    );
    const results = validateLayout(placements);
    const walls = results.find((r) => r.label.startsWith("Walls"));
    expect(walls?.passing).toBe(false);
  });
});

describe("validateLayout — overlap constraint", () => {
  it("passes with non-overlapping buildings", () => {
    const results = validateLayout([bp("town_hall", [10, 10]), bp("cannon", [20, 20])]);
    const overlap = results.find((r) => r.label.includes("overlap"));
    expect(overlap?.passing).toBe(true);
  });

  it("fails when two buildings overlap", () => {
    // Both cannons at same origin → overlap
    const results = validateLayout([bp("cannon", [10, 10]), bp("cannon", [10, 10])]);
    const overlap = results.find((r) => r.label.includes("overlap"));
    expect(overlap?.passing).toBe(false);
  });

  it("fails when TH (4x4) and cannon (3x3) origins touch but footprints overlap", () => {
    // TH at [10,10] occupies rows 10-13, cols 10-13
    // Cannon at [12,12] occupies rows 12-14, cols 12-14 → overlaps
    const results = validateLayout([bp("town_hall", [10, 10]), bp("cannon", [12, 12])]);
    const overlap = results.find((r) => r.label.includes("overlap"));
    expect(overlap?.passing).toBe(false);
  });
});

describe("validateLayout — buildable region constraint", () => {
  it("passes for buildings inside buildable region", () => {
    const results = validateLayout([bp("cannon", [10, 10])]);
    const region = results.find((r) => r.label.includes("buildable"));
    expect(region?.passing).toBe(true);
  });

  it("fails when building origin is inside deploy ring", () => {
    // origin [0,0] is in the deploy ring (< BUILDABLE_MIN=3)
    const results = validateLayout([bp("cannon", [0, 0])]);
    const region = results.find((r) => r.label.includes("buildable"));
    expect(region?.passing).toBe(false);
  });

  it("fails when building footprint extends outside buildable region", () => {
    // cannon (3×3) at [45,45] extends to [47,47] — BUILDABLE_MAX_EXCLUSIVE is 47 → out of bounds
    const results = validateLayout([bp("cannon", [45, 45])]);
    const region = results.find((r) => r.label.includes("buildable"));
    expect(region?.passing).toBe(false);
  });
});

describe("validateLayout — conflictingIndices", () => {
  it("overlap failure reports both conflicting indices", () => {
    const results = validateLayout([bp("cannon", [10, 10]), bp("cannon", [10, 10])]);
    const overlap = results.find((r) => r.label.includes("overlap"));
    expect(overlap?.conflictingIndices).toEqual(expect.arrayContaining([0, 1]));
  });

  it("out-of-bounds failure reports the offending index", () => {
    const results = validateLayout([bp("cannon", [0, 0])]);
    const region = results.find((r) => r.label.includes("buildable"));
    expect(region?.conflictingIndices).toContain(0);
  });
});
