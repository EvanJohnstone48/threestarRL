// Integration smoke test: load the committed Phase 0 tracer replay from
// disk through the same parser the viewer uses. Catches schema drift between
// sandbox-core's emitted JSON and the loader's expectations.

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { parseReplay } from "./loader";
import { interpolateFrame } from "./interpolation";

const TRACER_PATH = resolve(__dirname, "../../../../tests/golden/replays/tracer_smoke.json");

describe("Phase 0 tracer_smoke replay", () => {
  const text = readFileSync(TRACER_PATH, "utf-8");

  it("parses without error", () => {
    const replay = parseReplay(text);
    expect(replay.schema_version).toBe(1);
    expect(replay.frames.length).toBeGreaterThan(0);
    expect(replay.metadata.base_name).toBe("tracer");
  });

  it("first frame has the Town Hall + Cannon + one Barbarian", () => {
    const replay = parseReplay(text);
    const f0 = replay.frames[0];
    const buildingTypes = f0.state.buildings.map((b) => b.building_type).sort();
    expect(buildingTypes).toEqual(["cannon", "town_hall"]);
    expect(f0.state.troops).toHaveLength(1);
    expect(f0.state.troops[0].troop_type).toBe("barbarian");
  });

  it("replay terminates with Town Hall destroyed and >=50% destruction (per AC-S0.2)", () => {
    const replay = parseReplay(text);
    const score = replay.metadata.final_score;
    expect(score.town_hall_destroyed).toBe(true);
    expect(score.destruction_pct).toBeGreaterThanOrEqual(50);
    expect(score.stars).toBeGreaterThanOrEqual(1);
  });

  it("interpolates between consecutive frames without throwing", () => {
    const replay = parseReplay(text);
    // Sample a handful of frames including beginning, middle, end.
    const indices = [0, 1, Math.floor(replay.frames.length / 2), replay.frames.length - 2];
    for (const i of indices) {
      const f = interpolateFrame(replay.frames[i], replay.frames[i + 1] ?? null, 0.5);
      expect(f.tick).toBe(replay.frames[i].tick);
    }
  });
});
