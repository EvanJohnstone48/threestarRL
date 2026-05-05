import { describe, expect, it } from "vitest";
import { computeEventMarks } from "./eventMarks";
import type { TickFrame } from "@/generated_types";

function makeFrame(tick: number, events: TickFrame["events"] = []): TickFrame {
  return {
    tick,
    state: {
      tick,
      buildings: [],
      troops: [],
      traps: [],
      projectiles: [],
      spells: [],
      score: { stars: 0, destruction_pct: 0, ticks_elapsed: tick, town_hall_destroyed: false },
    },
    events,
  };
}

describe("computeEventMarks — deploy", () => {
  it("emits one deploy mark per event", () => {
    const frames = [
      makeFrame(0, [{ type: "deploy", tick: 0, payload: { troop_type: "barbarian", level: 5 } }]),
      makeFrame(1, [{ type: "deploy", tick: 1, payload: { troop_type: "giant", level: 3 } }]),
    ];
    const marks = computeEventMarks(frames).filter((m) => m.type === "deploy");
    expect(marks).toHaveLength(2);
    expect(marks[0].tick).toBe(0);
    expect(marks[1].tick).toBe(1);
  });

  it("deploy mark is green", () => {
    const frames = [
      makeFrame(0, [{ type: "deploy", tick: 0, payload: { troop_type: "barbarian", level: 1 } }]),
    ];
    const mark = computeEventMarks(frames).find((m) => m.type === "deploy")!;
    expect(mark.color).toBe("#66bb6a");
  });

  it("deploy tooltip includes troop type and level", () => {
    const frames = [
      makeFrame(5, [{ type: "deploy", tick: 5, payload: { troop_type: "wizard", level: 4 } }]),
    ];
    const mark = computeEventMarks(frames).find((m) => m.type === "deploy")!;
    expect(mark.tooltip).toContain("wizard");
    expect(mark.tooltip).toContain("lv4");
    expect(mark.tooltip).toContain("tick 5");
  });
});

describe("computeEventMarks — damage", () => {
  it("aggregates multiple damage events at the same tick into one mark", () => {
    const frames = [
      makeFrame(10, [
        { type: "damage", tick: 10, payload: { damage: 50, attacker_id: 1, kind: "ranged", target_id: 2 } },
        { type: "damage", tick: 10, payload: { damage: 30, attacker_id: 1, kind: "ranged", target_id: 3 } },
      ]),
    ];
    const marks = computeEventMarks(frames).filter((m) => m.type === "damage");
    expect(marks).toHaveLength(1);
    expect(marks[0].tooltip).toContain("80");
  });

  it("damage events at different ticks produce separate marks", () => {
    const frames = [
      makeFrame(5, [{ type: "damage", tick: 5, payload: { damage: 20, attacker_id: 1, kind: "melee", target_id: 2 } }]),
      makeFrame(6, [{ type: "damage", tick: 6, payload: { damage: 20, attacker_id: 1, kind: "melee", target_id: 2 } }]),
    ];
    const marks = computeEventMarks(frames).filter((m) => m.type === "damage");
    expect(marks).toHaveLength(2);
  });

  it("damage mark is yellow", () => {
    const frames = [
      makeFrame(1, [{ type: "damage", tick: 1, payload: { damage: 10 } }]),
    ];
    const mark = computeEventMarks(frames).find((m) => m.type === "damage")!;
    expect(mark.color).toBe("#ffc107");
  });

  it("damage mark sizePx scales with magnitude but stays in [4, 10]", () => {
    const small = makeFrame(1, [{ type: "damage", tick: 1, payload: { damage: 1 } }]);
    const large = makeFrame(2, [{ type: "damage", tick: 2, payload: { damage: 10000 } }]);
    const marks = computeEventMarks([small, large]).filter((m) => m.type === "damage");
    const smallMark = marks.find((m) => m.tick === 1)!;
    const largeMark = marks.find((m) => m.tick === 2)!;
    expect(smallMark.sizePx).toBe(4);
    expect(largeMark.sizePx).toBe(10);
    expect(largeMark.sizePx).toBeGreaterThan(smallMark.sizePx);
  });
});

describe("computeEventMarks — destroyed", () => {
  it("regular destroyed mark is red", () => {
    const frames = [
      makeFrame(20, [
        { type: "destroyed", tick: 20, payload: { kind: "troop", troop_id: 5, troop_type: "barbarian" } },
      ]),
    ];
    const mark = computeEventMarks(frames).find((m) => m.type === "destroyed")!;
    expect(mark.color).toBe("#f44336");
  });

  it("town_hall_destroyed mark is gold and uses special type", () => {
    const frames = [
      makeFrame(100, [
        {
          type: "destroyed",
          tick: 100,
          payload: { kind: "building", building_id: 0, building_type: "town_hall", category: "town_hall" },
        },
      ]),
    ];
    const mark = computeEventMarks(frames).find((m) => m.type === "town_hall_destroyed")!;
    expect(mark).toBeDefined();
    expect(mark.color).toBe("#ffd700");
    expect(mark.tooltip).toContain("town hall");
  });

  it("detects TH destruction via building_type field too", () => {
    const frames = [
      makeFrame(50, [
        { type: "destroyed", tick: 50, payload: { building_type: "town_hall", kind: "building" } },
      ]),
    ];
    const marks = computeEventMarks(frames);
    expect(marks.some((m) => m.type === "town_hall_destroyed")).toBe(true);
  });
});

describe("computeEventMarks — spell_cast", () => {
  it("spell mark is purple", () => {
    const frames = [
      makeFrame(10, [
        { type: "spell_cast", tick: 10, payload: { spell_type: "lightning_spell", level: 3, spell_id: 99, center: [24, 24] } },
      ]),
    ];
    const mark = computeEventMarks(frames).find((m) => m.type === "spell_cast")!;
    expect(mark.color).toBe("#b084ff");
    expect(mark.tooltip).toContain("lightning_spell");
  });
});

describe("computeEventMarks — non-display event types", () => {
  it("projectile_fired and sim_terminated produce no marks", () => {
    const frames = [
      makeFrame(0, [
        { type: "projectile_fired", tick: 0, payload: { attacker_id: 1, projectile_id: 2, target_id: 3, ticks_to_impact: 4 } },
        { type: "sim_terminated", tick: 0, payload: {} },
      ]),
    ];
    const marks = computeEventMarks(frames);
    expect(marks).toHaveLength(0);
  });
});

describe("computeEventMarks — empty input", () => {
  it("returns empty array for no frames", () => {
    expect(computeEventMarks([])).toEqual([]);
  });

  it("returns empty array for frames with no events", () => {
    expect(computeEventMarks([makeFrame(0), makeFrame(1)])).toEqual([]);
  });
});
