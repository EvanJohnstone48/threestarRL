import { describe, expect, it } from "vitest";
import {
  BUILDABLE_MAX_EXCLUSIVE,
  BUILDABLE_MIN,
  GRID_SIZE,
  TILE_SIZE,
  gridToScreen,
  isInDeployRing,
  screenToGrid,
} from "./projection";

describe("gridToScreen / screenToGrid", () => {
  it("origin tile maps to (0, 0)", () => {
    expect(gridToScreen(0, 0)).toEqual({ x: 0, y: 0 });
  });

  it("col controls x, row controls y", () => {
    expect(gridToScreen(0, 5)).toEqual({ x: 5 * TILE_SIZE, y: 0 });
    expect(gridToScreen(5, 0)).toEqual({ x: 0, y: 5 * TILE_SIZE });
  });

  it("max-extent tile maps to bottom-right of grid", () => {
    const { x, y } = gridToScreen(GRID_SIZE - 1, GRID_SIZE - 1);
    expect(x).toBe((GRID_SIZE - 1) * TILE_SIZE);
    expect(y).toBe((GRID_SIZE - 1) * TILE_SIZE);
  });

  it("respects custom tileSize", () => {
    expect(gridToScreen(2, 3, 10)).toEqual({ x: 30, y: 20 });
  });

  it("screenToGrid inverts gridToScreen for integer tiles", () => {
    for (const [r, c] of [
      [0, 0],
      [3, 5],
      [25, 25],
      [49, 49],
    ] as const) {
      const { x, y } = gridToScreen(r, c);
      expect(screenToGrid(x, y)).toEqual({ row: r, col: c });
    }
  });
});

describe("isInDeployRing", () => {
  it("treats rows 0..2 and 47..49 as deploy ring", () => {
    expect(isInDeployRing(0, 25)).toBe(true);
    expect(isInDeployRing(2, 25)).toBe(true);
    expect(isInDeployRing(47, 25)).toBe(true);
    expect(isInDeployRing(49, 25)).toBe(true);
  });

  it("treats cols 0..2 and 47..49 as deploy ring", () => {
    expect(isInDeployRing(25, 0)).toBe(true);
    expect(isInDeployRing(25, 2)).toBe(true);
    expect(isInDeployRing(25, 47)).toBe(true);
    expect(isInDeployRing(25, 49)).toBe(true);
  });

  it("treats inner buildable cells as not in deploy ring", () => {
    expect(isInDeployRing(BUILDABLE_MIN, BUILDABLE_MIN)).toBe(false);
    expect(isInDeployRing(25, 25)).toBe(false);
    expect(isInDeployRing(BUILDABLE_MAX_EXCLUSIVE - 1, BUILDABLE_MAX_EXCLUSIVE - 1)).toBe(false);
  });

  it("treats out-of-bounds cells as not in ring (caller's job to bounds-check)", () => {
    expect(isInDeployRing(-1, 5)).toBe(false);
    expect(isInDeployRing(50, 5)).toBe(false);
  });
});
