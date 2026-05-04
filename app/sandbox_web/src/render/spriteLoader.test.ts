import { describe, expect, it } from "vitest";
import {
  BUILDING_TYPES,
  TERRAIN_TYPES,
  buildingSpriteUrlCandidates,
  terrainSpriteUrlCandidates,
} from "./spritePaths";

describe("buildingSpriteUrlCandidates", () => {
  it("uses the canonical sprite path first for every building", () => {
    for (const buildingType of BUILDING_TYPES) {
      expect(buildingSpriteUrlCandidates(buildingType)[0]).toBe(
        `/sprites/buildings/${buildingType}.png`,
      );
    }
  });

  it("keeps compatibility with known bad local sprite filenames", () => {
    expect(buildingSpriteUrlCandidates("barracks")).toContain("/sprites/buildings/barracls.png");
    expect(buildingSpriteUrlCandidates("spell_factory")).toContain(
      "/sprites/buildings/spell+factory.png",
    );
    expect(buildingSpriteUrlCandidates("builders_hut")).toContain(
      "/sprites/buildings/builder_hut.png",
    );
  });
});

describe("terrainSpriteUrlCandidates", () => {
  it("uses canonical terrain paths", () => {
    for (const terrainType of TERRAIN_TYPES) {
      expect(terrainSpriteUrlCandidates(terrainType)[0]).toBe(
        `/sprites/terrain/${terrainType}.png`,
      );
    }
  });

  it("keeps compatibility with the requested building underspace terrain name", () => {
    expect(terrainSpriteUrlCandidates("building_grass")).toContain(
      "/sprites/terrain/building_underspace_grass.png",
    );
  });
});
