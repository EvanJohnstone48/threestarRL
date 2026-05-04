import { describe, it, expect, beforeEach } from "vitest";
import {
  saveToLocalStorage,
  loadFromLocalStorage,
  clearLocalStorage,
} from "./autosave";
import type { BuildingPlacement, BaseLayoutMetadata } from "@/generated_types";

const META: BaseLayoutMetadata = {
  name: "test-base",
  th_level: 6,
  tags: ["compound"],
  notes: null,
  author: "tester",
  created_at: "2026-01-01T00:00:00.000Z",
};

const PLACEMENTS: BuildingPlacement[] = [
  { building_type: "cannon", origin: [10, 10], level: 1 },
];

beforeEach(() => {
  localStorage.clear();
});

describe("autosave — saveToLocalStorage / loadFromLocalStorage", () => {
  it("returns null when nothing is saved", () => {
    expect(loadFromLocalStorage()).toBeNull();
  });

  it("round-trips placements and metadata", () => {
    saveToLocalStorage(PLACEMENTS, META);
    const draft = loadFromLocalStorage();
    expect(draft).not.toBeNull();
    expect(draft!.placements).toEqual(PLACEMENTS);
    expect(draft!.metadata).toEqual(META);
  });

  it("draft includes a savedAt timestamp", () => {
    saveToLocalStorage(PLACEMENTS, META);
    const draft = loadFromLocalStorage();
    expect(typeof draft!.savedAt).toBe("string");
    expect(draft!.savedAt.length).toBeGreaterThan(0);
  });

  it("overwrites a previous draft", () => {
    saveToLocalStorage(PLACEMENTS, META);
    const updated: BuildingPlacement[] = [
      ...PLACEMENTS,
      { building_type: "mortar", origin: [20, 20], level: 1 },
    ];
    saveToLocalStorage(updated, META);
    const draft = loadFromLocalStorage();
    expect(draft!.placements).toHaveLength(2);
  });
});

describe("autosave — clearLocalStorage", () => {
  it("removes the saved draft", () => {
    saveToLocalStorage(PLACEMENTS, META);
    clearLocalStorage();
    expect(loadFromLocalStorage()).toBeNull();
  });
});

describe("autosave — loadFromLocalStorage handles corrupt data", () => {
  it("returns null when localStorage contains invalid JSON", () => {
    localStorage.setItem("editor_autosave", "not-json");
    expect(loadFromLocalStorage()).toBeNull();
  });
});
