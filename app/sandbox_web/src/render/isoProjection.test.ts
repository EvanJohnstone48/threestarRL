import { describe, expect, it } from "vitest";
import { gridToIsoScreen, isoScreenToGrid } from "./isoProjection";
import { BUILDABLE_MIN, BUILDABLE_MAX_EXCLUSIVE, GRID_SIZE } from "./projection";

describe("gridToIsoScreen", () => {
  it("origin corner (0,0) lands at canvas center", () => {
    const cx = 800;
    const pt = gridToIsoScreen(0, 0, cx, 0);
    expect(pt.x).toBe(cx);
    expect(pt.y).toBe(0);
  });

  it("matches PRD §8.2 formula exactly", () => {
    const cx = 400;
    // screen_x = (5−3)×32 + 400 = 464; screen_y = (5+3)×16 = 128
    const pt = gridToIsoScreen(3, 5, cx, 0);
    expect(pt.x).toBe(464);
    expect(pt.y).toBe(128);
  });

  it("south corner of full 50×50 grid", () => {
    const pt = gridToIsoScreen(GRID_SIZE, GRID_SIZE, 0, 0);
    // (50−50)×32 = 0; (50+50)×16 = 1600
    expect(pt.x).toBe(0);
    expect(pt.y).toBe(1600);
  });

  it("east corner of full grid", () => {
    const pt = gridToIsoScreen(0, GRID_SIZE, 0, 0);
    // (50−0)×32 = 1600; (50+0)×16 = 800
    expect(pt.x).toBe(1600);
    expect(pt.y).toBe(800);
  });

  it("deploy ring — inner boundary north corner", () => {
    const pt = gridToIsoScreen(BUILDABLE_MIN, BUILDABLE_MIN, 0, 0);
    // (3−3)×32 = 0; (3+3)×16 = 96
    expect(pt.x).toBe(0);
    expect(pt.y).toBe(96);
  });

  it("deploy ring — inner boundary east corner", () => {
    const pt = gridToIsoScreen(BUILDABLE_MIN, BUILDABLE_MAX_EXCLUSIVE, 0, 0);
    // (47−3)×32 = 1408; (47+3)×16 = 800
    expect(pt.x).toBe(1408);
    expect(pt.y).toBe(800);
  });
});

describe("isoScreenToGrid", () => {
  it("is the exact inverse of gridToIsoScreen for integer coords", () => {
    const cx = 500;
    const cy = 100;
    const cases: [number, number][] = [
      [0, 0],
      [25, 25],
      [3, 47],
      [49, 3],
      [GRID_SIZE, GRID_SIZE],
    ];
    for (const [r, c] of cases) {
      const pt = gridToIsoScreen(r, c, cx, cy);
      const back = isoScreenToGrid(pt.x, pt.y, cx, cy);
      expect(back.row).toBeCloseTo(r, 10);
      expect(back.col).toBeCloseTo(c, 10);
    }
  });

  it("deploy ring corner roundtrip", () => {
    const cx = 800;
    const cy = 0;
    const pt = gridToIsoScreen(BUILDABLE_MIN, BUILDABLE_MAX_EXCLUSIVE, cx, cy);
    const back = isoScreenToGrid(pt.x, pt.y, cx, cy);
    expect(back.row).toBeCloseTo(BUILDABLE_MIN, 10);
    expect(back.col).toBeCloseTo(BUILDABLE_MAX_EXCLUSIVE, 10);
  });
});
