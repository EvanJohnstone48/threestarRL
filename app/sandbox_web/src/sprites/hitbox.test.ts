import { describe, it, expect } from "vitest";
import { hitboxInsetTiles, hitboxRect } from "./hitbox";

describe("hitboxInsetTiles", () => {
  it("uses the 0.5 default for everything without an override", () => {
    expect(hitboxInsetTiles("cannon", 3)).toBe(0.5);
    expect(hitboxInsetTiles("town_hall", 4)).toBe(0.5);
    expect(hitboxInsetTiles("clan_castle", 3)).toBe(0.5);
    expect(hitboxInsetTiles("builders_hut", 2)).toBe(0.5);
  });

  it("applies army_camp override (1.0)", () => {
    expect(hitboxInsetTiles("army_camp", 4)).toBe(1.0);
  });

  it("applies wall override (0.0 — full-tile hitbox)", () => {
    expect(hitboxInsetTiles("wall", 1)).toBe(0);
  });
});

describe("hitboxRect", () => {
  it("centers a 2×2 hitbox inside a 3×3 cannon (inset 0.5)", () => {
    expect(hitboxRect("cannon", [10, 10], [3, 3])).toEqual({
      rowMin: 10.5,
      rowMax: 12.5,
      colMin: 10.5,
      colMax: 12.5,
    });
  });

  it("centers a 3×3 hitbox inside a 4×4 town hall (inset 0.5)", () => {
    expect(hitboxRect("town_hall", [10, 10], [4, 4])).toEqual({
      rowMin: 10.5,
      rowMax: 13.5,
      colMin: 10.5,
      colMax: 13.5,
    });
  });

  it("centers a 2×2 hitbox inside a 4×4 army camp (inset 1.0 override)", () => {
    expect(hitboxRect("army_camp", [10, 10], [4, 4])).toEqual({
      rowMin: 11,
      rowMax: 13,
      colMin: 11,
      colMax: 13,
    });
  });

  it("returns the full 1×1 footprint for walls (inset 0)", () => {
    expect(hitboxRect("wall", [5, 5], [1, 1])).toEqual({
      rowMin: 5,
      rowMax: 6,
      colMin: 5,
      colMax: 6,
    });
  });
});
