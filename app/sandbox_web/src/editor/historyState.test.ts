import { describe, it, expect } from "vitest";
import {
  createHistoryState,
  pushHistory,
  undo,
  redo,
  canUndo,
  canRedo,
} from "./historyState";
import type { BuildingPlacement } from "@/generated_types";

function bp(col: number): BuildingPlacement {
  return { building_type: "cannon", origin: [10, col], level: 1 };
}

describe("historyState — initial state", () => {
  it("starts with empty past and future", () => {
    const h = createHistoryState([]);
    expect(h.past).toHaveLength(0);
    expect(h.future).toHaveLength(0);
    expect(h.present).toEqual([]);
  });

  it("canUndo is false; canRedo is false", () => {
    const h = createHistoryState([]);
    expect(canUndo(h)).toBe(false);
    expect(canRedo(h)).toBe(false);
  });
});

describe("historyState — pushHistory", () => {
  it("moves present to past and sets new present", () => {
    const h0 = createHistoryState([]);
    const h1 = pushHistory(h0, [bp(10)]);
    expect(h1.present).toEqual([bp(10)]);
    expect(h1.past).toHaveLength(1);
    expect(h1.past[0]).toEqual([]);
    expect(h1.future).toHaveLength(0);
  });

  it("clears future on new push", () => {
    const h0 = createHistoryState([]);
    const h1 = pushHistory(h0, [bp(10)]);
    const h2 = undo(h1);
    const h3 = pushHistory(h2, [bp(20)]);
    expect(h3.future).toHaveLength(0);
  });

  it("caps history at 50 steps", () => {
    let h = createHistoryState([]);
    for (let i = 0; i < 55; i++) {
      h = pushHistory(h, [bp(i)]);
    }
    expect(h.past).toHaveLength(50);
  });
});

describe("historyState — undo", () => {
  it("restores the previous present", () => {
    const h0 = createHistoryState([]);
    const h1 = pushHistory(h0, [bp(10)]);
    const h2 = undo(h1);
    expect(h2.present).toEqual([]);
    expect(h2.past).toHaveLength(0);
    expect(h2.future).toHaveLength(1);
    expect(h2.future[0]).toEqual([bp(10)]);
  });

  it("is a no-op when nothing to undo", () => {
    const h = createHistoryState([bp(10)]);
    const h2 = undo(h);
    expect(h2).toBe(h);
  });

  it("canUndo becomes false after undoing to initial state", () => {
    const h0 = createHistoryState([]);
    const h1 = pushHistory(h0, [bp(10)]);
    const h2 = undo(h1);
    expect(canUndo(h2)).toBe(false);
  });
});

describe("historyState — redo", () => {
  it("re-applies the undone change", () => {
    const h0 = createHistoryState([]);
    const h1 = pushHistory(h0, [bp(10)]);
    const h2 = undo(h1);
    const h3 = redo(h2);
    expect(h3.present).toEqual([bp(10)]);
    expect(h3.future).toHaveLength(0);
    expect(h3.past).toHaveLength(1);
  });

  it("is a no-op when nothing to redo", () => {
    const h = createHistoryState([bp(10)]);
    const h2 = redo(h);
    expect(h2).toBe(h);
  });

  it("canRedo becomes false after redoing", () => {
    const h0 = createHistoryState([]);
    const h1 = pushHistory(h0, [bp(10)]);
    const h2 = undo(h1);
    const h3 = redo(h2);
    expect(canRedo(h3)).toBe(false);
  });
});

describe("historyState — multi-step undo/redo", () => {
  it("supports chained undo and redo", () => {
    const h0 = createHistoryState([]);
    const h1 = pushHistory(h0, [bp(10)]);
    const h2 = pushHistory(h1, [bp(20)]);
    const h3 = pushHistory(h2, [bp(30)]);

    const u1 = undo(h3);
    expect(u1.present).toEqual([bp(20)]);
    const u2 = undo(u1);
    expect(u2.present).toEqual([bp(10)]);
    const u3 = undo(u2);
    expect(u3.present).toEqual([]);

    const r1 = redo(u3);
    expect(r1.present).toEqual([bp(10)]);
    const r2 = redo(r1);
    expect(r2.present).toEqual([bp(20)]);
  });
});
