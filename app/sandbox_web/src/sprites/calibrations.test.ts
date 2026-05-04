import { describe, it, expect, beforeEach } from "vitest";
import {
  DEFAULT_CALIBRATION,
  emptyCalibrations,
  getCalibration,
  loadCalibrations,
  saveCalibrationsLocal,
  serializeForDownload,
  setCalibration,
} from "./calibrations";

beforeEach(() => {
  window.localStorage.clear();
});

describe("getCalibration", () => {
  it("returns the default when entity has no entry", () => {
    expect(getCalibration(emptyCalibrations(), "buildings", "cannon")).toEqual(DEFAULT_CALIBRATION);
  });

  it("returns the stored entry when set", () => {
    const cal = { offset_x: 5, offset_y: -10, scale: 1.5 };
    const cals = setCalibration(emptyCalibrations(), "buildings", "cannon", cal);
    expect(getCalibration(cals, "buildings", "cannon")).toEqual(cal);
  });
});

describe("loadCalibrations / saveCalibrationsLocal", () => {
  it("round-trips through localStorage", () => {
    const cals = setCalibration(emptyCalibrations(), "troops", "barbarian", {
      offset_x: 1,
      offset_y: 2,
      scale: 0.5,
    });
    saveCalibrationsLocal(cals);
    const loaded = loadCalibrations();
    expect(getCalibration(loaded, "troops", "barbarian")).toEqual({
      offset_x: 1,
      offset_y: 2,
      scale: 0.5,
    });
  });

  it("ignores invalid localStorage payload", () => {
    window.localStorage.setItem("threestarrl.sprite_calibrations.v1", "{not json");
    const loaded = loadCalibrations();
    expect(loaded.schema_version).toBe(1);
  });

  it("rejects calibrations with non-positive scale", () => {
    window.localStorage.setItem(
      "threestarrl.sprite_calibrations.v1",
      JSON.stringify({
        schema_version: 1,
        buildings: { cannon: { offset_x: 0, offset_y: 0, scale: 0 } },
        troops: {},
        effects: {},
      }),
    );
    const loaded = loadCalibrations();
    expect(loaded.buildings.cannon?.scale).toBeGreaterThan(0);
  });
});

describe("serializeForDownload", () => {
  it("sorts entity keys alphabetically", () => {
    let cals = emptyCalibrations();
    cals = setCalibration(cals, "buildings", "wizard_tower", DEFAULT_CALIBRATION);
    cals = setCalibration(cals, "buildings", "cannon", DEFAULT_CALIBRATION);
    const txt = serializeForDownload(cals);
    expect(txt.indexOf("cannon")).toBeLessThan(txt.indexOf("wizard_tower"));
    expect(txt.endsWith("\n")).toBe(true);
  });
});
