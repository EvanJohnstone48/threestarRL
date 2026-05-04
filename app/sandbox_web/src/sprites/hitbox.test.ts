import { describe, it, expect } from "vitest";
import { hitboxInsetTiles, hitboxRect } from "./hitbox";

describe("hitboxInsetTiles", () => {
  it("matches PRD §5.4 default rule", () => {
    expect(hitboxInsetTiles("cannon", 3)).toBe(1.0);
    expect(hitboxInsetTiles("town_hall", 4)).toBe(1.5);
    expect(hitboxInsetTiles("clan_castle", 3)).toBe(1.0);
    expect(hitboxInsetTiles("builders_hut", 2)).toBe(0.5);
  });

  it("applies army_camp override (1.0 instead of default 1.5)", () => {
    expect(hitboxInsetTiles("army_camp", 4)).toBe(1.0);
  });

  it("returns 0 for walls (footprint = hitbox)", () => {
    expect(hitboxInsetTiles("wall", 1)).toBe(0);
  });
});

describe("hitboxRect", () => {
  it("centers a 1×1 hitbox inside a 3×3 cannon", () => {
    expect(hitboxRect("cannon", [10, 10], [3, 3])).toEqual({
      rowMin: 11,
      rowMax: 12,
      colMin: 11,
      colMax: 12,
    });
  });

  it("centers a 2×2 hitbox inside a 4×4 army camp", () => {
    expect(hitboxRect("army_camp", [10, 10], [4, 4])).toEqual({
      rowMin: 11,
      rowMax: 13,
      colMin: 11,
      colMax: 13,
    });
  });

  it("returns full 1×1 footprint for walls", () => {
    expect(hitboxRect("wall", [5, 5], [1, 1])).toEqual({
      rowMin: 5,
      rowMax: 6,
      colMin: 5,
      colMax: 6,
    });
  });
});
