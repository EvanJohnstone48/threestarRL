import { describe, it, expect } from "vitest";
import { createEditorState, enterPlaceMode, exitPlaceMode, placeBuildingAt, removeBuilding, getGhostLegality } from "./editorState";

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
