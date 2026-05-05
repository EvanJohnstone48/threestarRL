import { describe, expect, it } from "vitest";
import { interpolateFrame, lerpPos } from "./interpolation";
import type { TickFrame } from "@/generated_types";

const emptyScore = { stars: 0, destruction_pct: 0, ticks_elapsed: 0, town_hall_destroyed: false };

const frame = (
  tick: number,
  troops: { id: number; pos: [number, number]; hp?: number }[],
  projectiles: { id: number; pos: [number, number] }[] = [],
): TickFrame => ({
  tick,
  state: {
    tick,
    buildings: [],
    traps: [],
    troops: troops.map((t) => ({
      id: t.id,
      troop_type: "barbarian",
      level: 1,
      position: t.pos,
      hp: t.hp ?? 100,
      max_hp: 100,
      destroyed: false,
    })),
    projectiles: projectiles.map((p) => ({
      id: p.id,
      attacker_id: 0,
      target_id: null,
      attack_kind: "ranged",
      attacker_position: [0, 0],
      current_position: p.pos,
      impact_position: [0, 0],
      damage: 1,
      splash_radius_tiles: 0,
      splash_damages_walls: false,
      ticks_to_impact: 0,
    })),
    spells: [],
    score: emptyScore,
  },
  events: [],
});

describe("lerpPos", () => {
  it("linearly interpolates each axis", () => {
    expect(lerpPos([0, 0], [10, 20], 0.5)).toEqual([5, 10]);
    expect(lerpPos([1, 1], [3, 5], 0)).toEqual([1, 1]);
    expect(lerpPos([1, 1], [3, 5], 1)).toEqual([3, 5]);
  });
});

describe("interpolateFrame", () => {
  it("returns current state untouched when next is null", () => {
    const f = frame(0, [{ id: 1, pos: [2, 3] }]);
    const r = interpolateFrame(f, null, 0.5);
    expect(r.troops[0].position).toEqual([2, 3]);
    expect(r.tick).toBe(0);
  });

  it("returns current state when alpha=0", () => {
    const cur = frame(0, [{ id: 1, pos: [2, 3] }]);
    const nxt = frame(1, [{ id: 1, pos: [4, 6] }]);
    const r = interpolateFrame(cur, nxt, 0);
    expect(r.troops[0].position).toEqual([2, 3]);
  });

  it("lerps matched troop positions toward next frame", () => {
    const cur = frame(0, [{ id: 1, pos: [0, 0] }]);
    const nxt = frame(1, [{ id: 1, pos: [10, 20] }]);
    const r = interpolateFrame(cur, nxt, 0.5);
    expect(r.troops[0].position).toEqual([5, 10]);
  });

  it("holds position for a troop that vanishes next tick (died)", () => {
    const cur = frame(0, [{ id: 1, pos: [3, 3] }]);
    const nxt = frame(1, []);
    const r = interpolateFrame(cur, nxt, 0.5);
    expect(r.troops[0].position).toEqual([3, 3]);
  });

  it("lerps multiple troops independently by id", () => {
    const cur = frame(0, [
      { id: 1, pos: [0, 0] },
      { id: 2, pos: [10, 10] },
    ]);
    const nxt = frame(1, [
      { id: 1, pos: [2, 4] },
      { id: 2, pos: [8, 6] },
    ]);
    const r = interpolateFrame(cur, nxt, 0.5);
    expect(r.troops.find((t) => t.id === 1)?.position).toEqual([1, 2]);
    expect(r.troops.find((t) => t.id === 2)?.position).toEqual([9, 8]);
  });

  it("lerps projectile positions by id", () => {
    const cur = frame(0, [], [{ id: 7, pos: [0, 0] }]);
    const nxt = frame(1, [], [{ id: 7, pos: [4, 8] }]);
    const r = interpolateFrame(cur, nxt, 0.25);
    expect(r.projectiles[0].current_position).toEqual([1, 2]);
  });

  it("HP and destroyed flag come from `current` only (no interp)", () => {
    const cur = frame(0, [{ id: 1, pos: [0, 0], hp: 100 }]);
    const nxt = frame(1, [{ id: 1, pos: [1, 0], hp: 50 }]);
    const r = interpolateFrame(cur, nxt, 0.5);
    expect(r.troops[0].hp).toBe(100);
  });
});
