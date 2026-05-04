import { describe, it, expect } from "vitest";
import {
  createEditorState,
  enterPlaceMode,
  exitPlaceMode,
  placeBuildingAt,
  removeBuilding,
  getGhostLegality,
  resolveOrthoLine,
  enterPaintMode,
  enterEraseMode,
  exitCurrentMode,
  startPaintDrag,
  commitWallPaint,
  eraseAtTile,
  clearAll,
  mirrorHorizontal,
  mirrorVertical,
  rotate90CW,
} from "./editorState";

describe("editorState — initial state", () => {
  it("starts in idle mode with no placements", () => {
    const state = createEditorState();
    expect(state.mode).toBe("idle");
    expect(state.placements).toHaveLength(0);
    expect(state.selectedType).toBeNull();
  });
});

describe("editorState — enterPlaceMode / exitPlaceMode", () => {
  it("enters place mode and records the selected type", () => {
    const s1 = createEditorState();
    const s2 = enterPlaceMode(s1, "cannon");
    expect(s2.mode).toBe("placing");
    expect(s2.selectedType).toBe("cannon");
  });

  it("exitPlaceMode returns to idle and clears selectedType", () => {
    const s1 = enterPlaceMode(createEditorState(), "cannon");
    const s2 = exitPlaceMode(s1);
    expect(s2.mode).toBe("idle");
    expect(s2.selectedType).toBeNull();
  });
});

describe("editorState — placeBuildingAt", () => {
  it("places a building when mode is placing and position is legal", () => {
    const s1 = enterPlaceMode(createEditorState(), "cannon");
    const [s2, result] = placeBuildingAt(s1, [10, 10]);
    expect(result).toBe("placed");
    expect(s2.placements).toHaveLength(1);
    expect(s2.placements[0].building_type).toBe("cannon");
    expect(s2.placements[0].origin).toEqual([10, 10]);
  });

  it("returns illegal when position is outside buildable region", () => {
    const s1 = enterPlaceMode(createEditorState(), "cannon");
    const [s2, result] = placeBuildingAt(s1, [0, 0]);
    expect(result).toBe("illegal");
    expect(s2.placements).toHaveLength(0);
  });

  it("returns illegal when placement would overlap an existing building", () => {
    const s1 = enterPlaceMode(createEditorState(), "cannon");
    const [s2] = placeBuildingAt(s1, [10, 10]);
    const s3 = enterPlaceMode(s2, "cannon");
    const [s4, result] = placeBuildingAt(s3, [10, 10]);
    expect(result).toBe("illegal");
    expect(s4.placements).toHaveLength(1);
  });

  it("returns cap_exceeded when TH6 cap is reached", () => {
    // mortar cap is 1
    let state = enterPlaceMode(createEditorState(), "mortar");
    [state] = placeBuildingAt(state, [10, 10]);
    state = enterPlaceMode(state, "mortar");
    const [finalState, result] = placeBuildingAt(state, [20, 20]);
    expect(result).toBe("cap_exceeded");
    expect(finalState.placements).toHaveLength(1);
  });

  it("returns illegal when not in place mode", () => {
    const s1 = createEditorState();
    const [s2, result] = placeBuildingAt(s1, [10, 10]);
    expect(result).toBe("illegal");
    expect(s2.placements).toHaveLength(0);
  });
});

describe("editorState — removeBuilding", () => {
  it("removes a building by index", () => {
    let state = enterPlaceMode(createEditorState(), "cannon");
    [state] = placeBuildingAt(state, [10, 10]);
    const s2 = removeBuilding(state, 0);
    expect(s2.placements).toHaveLength(0);
  });

  it("is a no-op for an invalid index", () => {
    let state = enterPlaceMode(createEditorState(), "cannon");
    [state] = placeBuildingAt(state, [10, 10]);
    const s2 = removeBuilding(state, 99);
    expect(s2.placements).toHaveLength(1);
  });
});

describe("editorState — getGhostLegality", () => {
  it("returns legal for a valid empty position in place mode", () => {
    const s1 = enterPlaceMode(createEditorState(), "cannon");
    expect(getGhostLegality(s1, [10, 10])).toBe("legal");
  });

  it("returns out_of_bounds for a position in the deploy ring", () => {
    const s1 = enterPlaceMode(createEditorState(), "cannon");
    expect(getGhostLegality(s1, [0, 0])).toBe("out_of_bounds");
  });

  it("returns overlap when another building is already there", () => {
    let state = enterPlaceMode(createEditorState(), "cannon");
    [state] = placeBuildingAt(state, [10, 10]);
    state = enterPlaceMode(state, "cannon");
    expect(getGhostLegality(state, [10, 10])).toBe("overlap");
  });

  it("returns cap_exceeded when cap is reached", () => {
    let state = enterPlaceMode(createEditorState(), "mortar");
    [state] = placeBuildingAt(state, [10, 10]);
    state = enterPlaceMode(state, "mortar");
    expect(getGhostLegality(state, [20, 20])).toBe("cap_exceeded");
  });
});

// ---------------------------------------------------------------------------
// resolveOrthoLine
// ---------------------------------------------------------------------------

describe("resolveOrthoLine — axial lines", () => {
  it("returns a single tile when from === to", () => {
    expect(resolveOrthoLine([5, 5], [5, 5])).toEqual([[5, 5]]);
  });

  it("returns horizontal line left-to-right", () => {
    expect(resolveOrthoLine([5, 3], [5, 6])).toEqual([
      [5, 3],
      [5, 4],
      [5, 5],
      [5, 6],
    ]);
  });

  it("returns horizontal line right-to-left", () => {
    const tiles = resolveOrthoLine([5, 6], [5, 3]);
    expect(tiles).toHaveLength(4);
    expect(tiles[0]).toEqual([5, 6]);
    expect(tiles[tiles.length - 1]).toEqual([5, 3]);
  });

  it("returns vertical line top-to-bottom", () => {
    expect(resolveOrthoLine([3, 5], [6, 5])).toEqual([
      [3, 5],
      [4, 5],
      [5, 5],
      [6, 5],
    ]);
  });

  it("returns vertical line bottom-to-top", () => {
    const tiles = resolveOrthoLine([6, 5], [3, 5]);
    expect(tiles).toHaveLength(4);
    expect(tiles[0]).toEqual([6, 5]);
    expect(tiles[tiles.length - 1]).toEqual([3, 5]);
  });
});

describe("resolveOrthoLine — L-shape resolution", () => {
  it("goes horizontal-first when |dc| >= |dr|", () => {
    // from (5,5) to (8,10): dc=5, dr=3 → horizontal first
    const tiles = resolveOrthoLine([5, 5], [8, 10]);
    expect(tiles[0]).toEqual([5, 5]);
    expect(tiles[tiles.length - 1]).toEqual([8, 10]);
    // Corner should be (5,10)
    const cornerIdx = tiles.findIndex(([r, c]) => r === 5 && c === 10);
    expect(cornerIdx).toBeGreaterThan(0);
    // No duplicates at corner
    const cornerCount = tiles.filter(([r, c]) => r === 5 && c === 10).length;
    expect(cornerCount).toBe(1);
    // Total: 6 (horiz) + 3 (vert after corner) = 9
    expect(tiles).toHaveLength(9);
  });

  it("goes vertical-first when |dr| > |dc|", () => {
    // from (5,5) to (10,8): dr=5, dc=3 → vertical first
    const tiles = resolveOrthoLine([5, 5], [10, 8]);
    expect(tiles[0]).toEqual([5, 5]);
    expect(tiles[tiles.length - 1]).toEqual([10, 8]);
    // Corner should be (10,5)
    const cornerIdx = tiles.findIndex(([r, c]) => r === 10 && c === 5);
    expect(cornerIdx).toBeGreaterThan(0);
    expect(tiles).toHaveLength(9);
  });
});

// ---------------------------------------------------------------------------
// Paint mode state machine
// ---------------------------------------------------------------------------

describe("editorState — enterPaintMode / enterEraseMode / exitCurrentMode", () => {
  it("enterPaintMode sets mode to painting", () => {
    const s = enterPaintMode(createEditorState());
    expect(s.mode).toBe("painting");
    expect(s.selectedType).toBeNull();
  });

  it("enterEraseMode sets mode to erasing", () => {
    const s = enterEraseMode(createEditorState());
    expect(s.mode).toBe("erasing");
  });

  it("entering paint mode exits place mode", () => {
    const s1 = enterPlaceMode(createEditorState(), "cannon");
    const s2 = enterPaintMode(s1);
    expect(s2.mode).toBe("painting");
    expect(s2.selectedType).toBeNull();
  });

  it("exitCurrentMode returns to idle from any mode", () => {
    expect(exitCurrentMode(enterPaintMode(createEditorState())).mode).toBe("idle");
    expect(exitCurrentMode(enterEraseMode(createEditorState())).mode).toBe("idle");
    expect(exitCurrentMode(enterPlaceMode(createEditorState(), "cannon")).mode).toBe("idle");
  });
});

describe("editorState — startPaintDrag / commitWallPaint", () => {
  it("startPaintDrag records the paint start tile", () => {
    const s = startPaintDrag(enterPaintMode(createEditorState()), [10, 10]);
    expect(s.paintStart).toEqual([10, 10]);
  });

  it("commitWallPaint paints walls along a horizontal line", () => {
    let state = enterPaintMode(createEditorState());
    state = startPaintDrag(state, [10, 10]);
    const [next, result] = commitWallPaint(state, [10, 13]);
    expect(result).toBe("painted");
    const walls = next.placements.filter((p) => p.building_type === "wall");
    expect(walls).toHaveLength(4);
    expect(walls.map((w) => w.origin)).toContainEqual([10, 10]);
    expect(walls.map((w) => w.origin)).toContainEqual([10, 13]);
  });

  it("commitWallPaint paints walls along a vertical line", () => {
    let state = enterPaintMode(createEditorState());
    state = startPaintDrag(state, [10, 10]);
    const [next, result] = commitWallPaint(state, [13, 10]);
    expect(result).toBe("painted");
    const walls = next.placements.filter((p) => p.building_type === "wall");
    expect(walls).toHaveLength(4);
  });

  it("painting over an existing wall is idempotent", () => {
    let state = enterPaintMode(createEditorState());
    state = startPaintDrag(state, [10, 10]);
    [state] = commitWallPaint(state, [10, 13]);
    // Paint the same line again
    state = startPaintDrag(state, [10, 10]);
    const [next, result] = commitWallPaint(state, [10, 13]);
    expect(result).toBe("noop");
    const walls = next.placements.filter((p) => p.building_type === "wall");
    expect(walls).toHaveLength(4); // no duplicates
  });

  it("stops at 75-wall cap and returns capped", () => {
    // Place 74 walls first
    let state = enterPaintMode(createEditorState());
    for (let row = 3; row < 3 + 74; row++) {
      state = startPaintDrag(state, [row, 3]);
      [state] = commitWallPaint(state, [row, 3]);
    }
    expect(state.placements.filter((p) => p.building_type === "wall")).toHaveLength(74);
    // Try to paint 5 more — only 1 should go in
    state = startPaintDrag(state, [3, 10]);
    const [next, result] = commitWallPaint(state, [3, 14]); // 5 tiles
    expect(result).toBe("capped");
    const wallCount = next.placements.filter((p) => p.building_type === "wall").length;
    expect(wallCount).toBe(75);
  });

  it("commitWallPaint is noop when not in paint mode", () => {
    const state = createEditorState();
    const [next, result] = commitWallPaint(state, [10, 10]);
    expect(result).toBe("noop");
    expect(next).toBe(state);
  });
});

// ---------------------------------------------------------------------------
// eraseAtTile
// ---------------------------------------------------------------------------

describe("editorState — eraseAtTile", () => {
  it("erases a 1×1 wall at the given tile", () => {
    let state = enterPaintMode(createEditorState());
    state = startPaintDrag(state, [10, 10]);
    [state] = commitWallPaint(state, [10, 10]);
    expect(state.placements).toHaveLength(1);
    const next = eraseAtTile(state, [10, 10]);
    expect(next.placements).toHaveLength(0);
  });

  it("erases a multi-tile building when any tile in its footprint is clicked", () => {
    // cannon is 3×3 — click an interior tile
    let state = enterPlaceMode(createEditorState(), "cannon");
    [state] = placeBuildingAt(state, [10, 10]);
    // Click on tile [11, 11] which is inside the 3×3 footprint
    const next = eraseAtTile(state, [11, 11]);
    expect(next.placements).toHaveLength(0);
  });

  it("is a no-op when no placement exists at the tile", () => {
    let state = enterPlaceMode(createEditorState(), "cannon");
    [state] = placeBuildingAt(state, [10, 10]);
    const next = eraseAtTile(state, [20, 20]);
    expect(next.placements).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// Mass actions
// ---------------------------------------------------------------------------

describe("clearAll", () => {
  it("empties placements and preserves mode", () => {
    let state = enterPlaceMode(createEditorState(), "cannon");
    [state] = placeBuildingAt(state, [10, 10]);
    const next = clearAll(state);
    expect(next.placements).toHaveLength(0);
    expect(next.mode).toBe("placing");
  });

  it("is a no-op on an already-empty state (returns empty placements)", () => {
    const state = createEditorState();
    const next = clearAll(state);
    expect(next.placements).toHaveLength(0);
  });
});

describe("mirrorHorizontal", () => {
  it("reflects a 1×1 wall across the vertical center axis", () => {
    // wall at col 10 → col 50-10-1 = 39
    const result = mirrorHorizontal([{ building_type: "wall", origin: [10, 10], level: 1 }]);
    expect(result[0].origin).toEqual([10, 39]);
  });

  it("reflects a 3×3 cannon correctly", () => {
    // cannon at col 10, width 3 → col 50-10-3 = 37
    const result = mirrorHorizontal([{ building_type: "cannon", origin: [10, 10], level: 1 }]);
    expect(result[0].origin).toEqual([10, 37]);
  });

  it("rows are unchanged", () => {
    const result = mirrorHorizontal([{ building_type: "cannon", origin: [15, 20], level: 1 }]);
    expect(result[0].origin[0]).toBe(15);
  });

  it("double mirror returns to original position", () => {
    const original = [{ building_type: "cannon", origin: [10, 10], level: 1 }];
    expect(mirrorHorizontal(mirrorHorizontal(original))[0].origin).toEqual([10, 10]);
  });

  it("two buildings swap positions correctly", () => {
    const p1 = { building_type: "wall", origin: [5, 10] as [number, number], level: 1 };
    const p2 = { building_type: "wall", origin: [5, 39] as [number, number], level: 1 };
    const result = mirrorHorizontal([p1, p2]);
    expect(result[0].origin).toEqual([5, 39]);
    expect(result[1].origin).toEqual([5, 10]);
  });
});

describe("mirrorVertical", () => {
  it("reflects a 1×1 wall across the horizontal center axis", () => {
    // wall at row 10 → row 50-10-1 = 39
    const result = mirrorVertical([{ building_type: "wall", origin: [10, 10], level: 1 }]);
    expect(result[0].origin).toEqual([39, 10]);
  });

  it("reflects a 3×3 cannon correctly", () => {
    // cannon at row 10, height 3 → row 50-10-3 = 37
    const result = mirrorVertical([{ building_type: "cannon", origin: [10, 10], level: 1 }]);
    expect(result[0].origin).toEqual([37, 10]);
  });

  it("cols are unchanged", () => {
    const result = mirrorVertical([{ building_type: "cannon", origin: [15, 20], level: 1 }]);
    expect(result[0].origin[1]).toBe(20);
  });

  it("double mirror returns to original position", () => {
    const original = [{ building_type: "cannon", origin: [10, 10], level: 1 }];
    expect(mirrorVertical(mirrorVertical(original))[0].origin).toEqual([10, 10]);
  });
});

describe("rotate90CW", () => {
  it("rotates a 1×1 wall 90° clockwise", () => {
    // tile (r,c) → (c, 49-r) for 1×1. wall at (10,20) → (20, 39)
    const result = rotate90CW([{ building_type: "wall", origin: [10, 20], level: 1 }]);
    expect(result[0].origin).toEqual([20, 39]);
  });

  it("rotates a 3×3 cannon 90° clockwise", () => {
    // cannon at (10,10), n=3: new_r=10, new_c=50-10-3=37
    const result = rotate90CW([{ building_type: "cannon", origin: [10, 10], level: 1 }]);
    expect(result[0].origin).toEqual([10, 37]);
  });

  it("four rotations return to original position", () => {
    const original = [{ building_type: "cannon", origin: [5, 20], level: 1 }];
    const r1 = rotate90CW(original);
    const r2 = rotate90CW(r1);
    const r3 = rotate90CW(r2);
    const r4 = rotate90CW(r3);
    expect(r4[0].origin).toEqual([5, 20]);
  });

  it("rotated placements stay within buildable region (BUILDABLE_MIN=3, BUILDABLE_MAX=47)", () => {
    // Place a cannon at a corner of the buildable region
    const placements = [{ building_type: "cannon", origin: [3, 3], level: 1 }];
    const result = rotate90CW(placements);
    const [r, c] = result[0].origin;
    expect(r).toBeGreaterThanOrEqual(3);
    expect(c).toBeGreaterThanOrEqual(3);
    expect(r + 3).toBeLessThanOrEqual(47);
    expect(c + 3).toBeLessThanOrEqual(47);
  });
});
