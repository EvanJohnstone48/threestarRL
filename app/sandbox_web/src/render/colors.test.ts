import { describe, expect, it } from "vitest";
import {
  COLOR_HP_FULL,
  COLOR_HP_LOW,
  COLOR_HP_MID,
  buildingColor,
  buildingLabel,
  categoryForBuilding,
  hpBarColor,
  troopLabel,
} from "./colors";

describe("buildingLabel", () => {
  it("uses known prefixes and appends level", () => {
    expect(buildingLabel("cannon", 6)).toBe("C6");
    expect(buildingLabel("archer_tower", 4)).toBe("AT4");
    expect(buildingLabel("town_hall", 1)).toBe("TH1");
  });

  it("returns empty label for walls (intentionally unlabeled)", () => {
    expect(buildingLabel("wall", 6)).toBe("");
  });

  it("falls back to first-two-uppercased for unknown types", () => {
    expect(buildingLabel("xyz_thing", 3)).toBe("XY3");
  });
});

describe("troopLabel", () => {
  it("returns single uppercase letter", () => {
    expect(troopLabel("barbarian")).toBe("B");
    expect(troopLabel("giant")).toBe("G");
  });
});

describe("hpBarColor", () => {
  it("green at full HP", () => {
    expect(hpBarColor(100, 100)).toBe(COLOR_HP_FULL);
    expect(hpBarColor(60, 100)).toBe(COLOR_HP_FULL);
  });

  it("yellow between ~50% and ~25%", () => {
    expect(hpBarColor(40, 100)).toBe(COLOR_HP_MID);
    expect(hpBarColor(26, 100)).toBe(COLOR_HP_MID);
  });

  it("red below ~25%", () => {
    expect(hpBarColor(20, 100)).toBe(COLOR_HP_LOW);
    expect(hpBarColor(0, 100)).toBe(COLOR_HP_LOW);
  });

  it("handles zero max_hp gracefully", () => {
    expect(hpBarColor(0, 0)).toBe(COLOR_HP_FULL);
  });
});

describe("buildingColor", () => {
  it("returns a 24-bit color number for each category", () => {
    expect(buildingColor("town_hall")).toBeGreaterThan(0);
    expect(buildingColor("defense")).toBeGreaterThan(0);
    expect(buildingColor("wall")).toBeGreaterThan(0);
  });
});

describe("categoryForBuilding", () => {
  it("maps known TH6 entities to their category", () => {
    expect(categoryForBuilding("cannon")).toBe("defense");
    expect(categoryForBuilding("town_hall")).toBe("town_hall");
    expect(categoryForBuilding("wall")).toBe("wall");
    expect(categoryForBuilding("gold_storage")).toBe("resource_storage");
    expect(categoryForBuilding("army_camp")).toBe("army");
  });

  it("falls back to 'defense' for unknown building types", () => {
    expect(categoryForBuilding("future_building")).toBe("defense");
  });
});
