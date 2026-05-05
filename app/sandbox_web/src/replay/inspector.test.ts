import { describe, expect, it } from "vitest";
import { getInspectorData, type SelectedEntity } from "./inspector";
import type { TickFrame } from "@/generated_types";

function makeFrame(overrides: Partial<TickFrame["state"]> = {}): TickFrame {
  return {
    tick: 0,
    state: {
      tick: 0,
      buildings: [],
      troops: [],
      traps: [],
      projectiles: [],
      spells: [],
      score: { stars: 0, destruction_pct: 0, ticks_elapsed: 0, town_hall_destroyed: false },
      ...overrides,
    },
    events: [],
  };
}

const BUILDING = {
  id: 1,
  building_type: "cannon",
  origin: [10, 15] as [number, number],
  level: 5,
  hp: 200,
  max_hp: 290,
  destroyed: false,
};

const TROOP = {
  id: 42,
  troop_type: "barbarian",
  level: 6,
  position: [25.5, 30.2] as [number, number],
  hp: 45,
  max_hp: 300,
  destroyed: false,
};

describe("getInspectorData — null cases", () => {
  it("returns null when selection is null", () => {
    const frame = makeFrame();
    expect(getInspectorData(null, frame)).toBeNull();
  });

  it("returns null when frame is null", () => {
    const sel: SelectedEntity = { kind: "building", id: 1 };
    expect(getInspectorData(sel, null)).toBeNull();
  });

  it("returns null when building id is not in frame", () => {
    const frame = makeFrame({ buildings: [BUILDING] });
    const sel: SelectedEntity = { kind: "building", id: 999 };
    expect(getInspectorData(sel, frame)).toBeNull();
  });

  it("returns null when troop id is not in frame", () => {
    const frame = makeFrame({ troops: [TROOP] });
    const sel: SelectedEntity = { kind: "troop", id: 999 };
    expect(getInspectorData(sel, frame)).toBeNull();
  });
});

describe("getInspectorData — building", () => {
  const frame = makeFrame({ buildings: [BUILDING] });
  const sel: SelectedEntity = { kind: "building", id: 1 };
  const data = getInspectorData(sel, frame)!;

  it("returns kind=building", () => expect(data.kind).toBe("building"));
  it("returns correct id", () => expect(data.id).toBe(1));
  it("returns correct entityType", () => expect(data.entityType).toBe("cannon"));
  it("returns correct level", () => expect(data.level).toBe(5));
  it("returns correct hp and maxHp", () => {
    expect(data.hp).toBe(200);
    expect(data.maxHp).toBe(290);
  });
  it("returns correct position (origin)", () => {
    expect(data.position).toEqual([10, 15]);
  });
  it("returns destroyed=false when alive", () => expect(data.destroyed).toBe(false));
});

describe("getInspectorData — troop", () => {
  const frame = makeFrame({ troops: [TROOP] });
  const sel: SelectedEntity = { kind: "troop", id: 42 };
  const data = getInspectorData(sel, frame)!;

  it("returns kind=troop", () => expect(data.kind).toBe("troop"));
  it("returns correct id", () => expect(data.id).toBe(42));
  it("returns correct entityType", () => expect(data.entityType).toBe("barbarian"));
  it("returns correct level", () => expect(data.level).toBe(6));
  it("returns correct hp and maxHp", () => {
    expect(data.hp).toBe(45);
    expect(data.maxHp).toBe(300);
  });
  it("returns correct position", () => {
    expect(data.position).toEqual([25.5, 30.2]);
  });
  it("returns destroyed=false when alive", () => expect(data.destroyed).toBe(false));
});

describe("getInspectorData — destroyed entity", () => {
  it("returns destroyed=true for a destroyed building still in frame", () => {
    const destroyed = { ...BUILDING, hp: 0, destroyed: true };
    const frame = makeFrame({ buildings: [destroyed] });
    const sel: SelectedEntity = { kind: "building", id: 1 };
    const data = getInspectorData(sel, frame)!;
    expect(data.destroyed).toBe(true);
    expect(data.hp).toBe(0);
  });

  it("returns destroyed=true for a destroyed troop still in frame", () => {
    const destroyed = { ...TROOP, hp: 0, destroyed: true };
    const frame = makeFrame({ troops: [destroyed] });
    const sel: SelectedEntity = { kind: "troop", id: 42 };
    const data = getInspectorData(sel, frame)!;
    expect(data.destroyed).toBe(true);
  });
});

describe("getInspectorData — live-update behaviour", () => {
  it("reflects hp changes between frames", () => {
    const frame1 = makeFrame({ buildings: [{ ...BUILDING, hp: 290 }] });
    const frame2 = makeFrame({ buildings: [{ ...BUILDING, hp: 100 }] });
    const sel: SelectedEntity = { kind: "building", id: 1 };
    expect(getInspectorData(sel, frame1)!.hp).toBe(290);
    expect(getInspectorData(sel, frame2)!.hp).toBe(100);
  });

  it("reflects troop position changes between frames", () => {
    const frame1 = makeFrame({ troops: [{ ...TROOP, position: [10, 10] }] });
    const frame2 = makeFrame({ troops: [{ ...TROOP, position: [20, 20] }] });
    const sel: SelectedEntity = { kind: "troop", id: 42 };
    expect(getInspectorData(sel, frame1)!.position).toEqual([10, 10]);
    expect(getInspectorData(sel, frame2)!.position).toEqual([20, 20]);
  });
});
