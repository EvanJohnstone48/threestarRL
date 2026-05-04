import { describe, expect, it } from "vitest";
import {
  ReplayLoadError,
  crossVersionBanner,
  parseReplay,
  simVersionBanner,
  validateReplay,
} from "./loader";
import type { Replay } from "@/generated_types";

const minimalReplay = (overrides: Partial<Replay> = {}): Replay => ({
  schema_version: 1,
  metadata: {
    sim_version: "0.1.0",
    base_name: "tracer",
    plan_name: "single_barb",
    run_id: "r1",
    episode_id: "e1",
    total_ticks: 1,
    final_score: { stars: 0, destruction_pct: 0, ticks_elapsed: 0, town_hall_destroyed: false },
    started_at: "2026-01-01T00:00:00Z",
    git_sha: "deadbeef",
    config_hash: "cafebabe",
  },
  initial_state: {
    tick: 0,
    buildings: [],
    troops: [],
    projectiles: [],
    spells: [],
    score: { stars: 0, destruction_pct: 0, ticks_elapsed: 0, town_hall_destroyed: false },
  },
  frames: [],
  ...overrides,
});

describe("parseReplay", () => {
  it("accepts a valid replay JSON string", () => {
    const text = JSON.stringify(minimalReplay());
    const parsed = parseReplay(text);
    expect(parsed.schema_version).toBe(1);
    expect(parsed.metadata.sim_version).toBe("0.1.0");
  });

  it("throws ReplayLoadError on malformed JSON", () => {
    expect(() => parseReplay("{not json")).toThrow(ReplayLoadError);
  });
});

describe("validateReplay", () => {
  it("rejects non-object payloads", () => {
    expect(() => validateReplay([])).toThrow(/object/);
    expect(() => validateReplay("hello")).toThrow(/object/);
    expect(() => validateReplay(null)).toThrow(/object/);
  });

  it("rejects missing required fields", () => {
    expect(() => validateReplay({ schema_version: 1, metadata: {}, initial_state: {} })).toThrow(
      /frames/,
    );
  });

  it("rejects non-array frames", () => {
    const bad = { ...minimalReplay(), frames: "not-an-array" as unknown };
    expect(() => validateReplay(bad)).toThrow(/array/);
  });

  it("rejects missing sim_version", () => {
    const bad = minimalReplay();
    delete (bad.metadata as Partial<Replay["metadata"]>).sim_version;
    expect(() => validateReplay(bad)).toThrow(/sim_version/);
  });
});

describe("crossVersionBanner / simVersionBanner", () => {
  it("returns null when schema_version matches", () => {
    expect(crossVersionBanner(minimalReplay({ schema_version: 1 }), 1)).toBeNull();
  });

  it("returns a banner message when schema versions differ", () => {
    const banner = crossVersionBanner(minimalReplay({ schema_version: 1 }), 2);
    expect(banner).toMatch(/schema_version 1.*runtime 2.*playback only/);
  });

  it("returns null when sim_version matches", () => {
    expect(simVersionBanner(minimalReplay(), "0.1.0")).toBeNull();
  });

  it("returns a banner when sim_versions differ", () => {
    const banner = simVersionBanner(minimalReplay(), "0.2.0");
    expect(banner).toMatch(/sim_version 0\.1\.0.*runtime 0\.2\.0/);
  });
});
