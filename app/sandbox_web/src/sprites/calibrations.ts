// Sprite calibration data + loader.
//
// Per-entity offset (in iso world pixels) and scale, applied on top of the
// renderer's natural anchor:
//   - Buildings: anchor = south corner of footprint diamond, anchor (0.5, 1.0).
//   - Troops/effects: anchor = entity's iso screen position, anchor (0.5, 0.5).
//
// Source-of-truth file is committed at app/data/sprite_calibrations.json.
// During calibration the user edits in the third-tab UI, which overlays into
// localStorage; "Export" downloads a merged JSON the user manually replaces in
// app/data/. The iso renderer reads the merged result at startup.

import bundled from "@data/sprite_calibrations.json";

export interface Calibration {
  offset_x: number;
  offset_y: number;
  scale: number;
}

export interface SpriteCalibrations {
  schema_version: 1;
  buildings: Record<string, Calibration>;
  troops: Record<string, Calibration>;
  effects: Record<string, Calibration>;
  traps: Record<string, Calibration>;
}

export type CalibrationKind = "buildings" | "troops" | "effects" | "traps";

export const DEFAULT_CALIBRATION: Calibration = {
  offset_x: 0,
  offset_y: 0,
  scale: 1.0,
};

const LOCAL_STORAGE_KEY = "threestarrl.sprite_calibrations.v1";

export function emptyCalibrations(): SpriteCalibrations {
  return { schema_version: 1, buildings: {}, troops: {}, effects: {}, traps: {} };
}

function isCalibration(value: unknown): value is Calibration {
  if (value === null || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.offset_x === "number" &&
    typeof v.offset_y === "number" &&
    typeof v.scale === "number" &&
    v.scale > 0
  );
}

function sanitizeBucket(raw: unknown): Record<string, Calibration> {
  if (raw === null || typeof raw !== "object") return {};
  const result: Record<string, Calibration> = {};
  for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
    if (isCalibration(value)) result[key] = value;
  }
  return result;
}

function sanitize(raw: unknown): SpriteCalibrations {
  const out = emptyCalibrations();
  if (raw === null || typeof raw !== "object") return out;
  const r = raw as Record<string, unknown>;
  out.buildings = sanitizeBucket(r.buildings);
  out.troops = sanitizeBucket(r.troops);
  out.effects = sanitizeBucket(r.effects);
  out.traps = sanitizeBucket(r.traps);
  return out;
}

// Load merged calibrations: bundled JSON overlaid with localStorage edits.
export function loadCalibrations(): SpriteCalibrations {
  const fromBundle = sanitize(bundled);
  if (typeof window === "undefined" || !window.localStorage) return fromBundle;
  const raw = window.localStorage.getItem(LOCAL_STORAGE_KEY);
  if (!raw) return fromBundle;
  try {
    const fromLocal = sanitize(JSON.parse(raw));
    return {
      schema_version: 1,
      buildings: { ...fromBundle.buildings, ...fromLocal.buildings },
      troops: { ...fromBundle.troops, ...fromLocal.troops },
      effects: { ...fromBundle.effects, ...fromLocal.effects },
      traps: { ...fromBundle.traps, ...fromLocal.traps },
    };
  } catch {
    return fromBundle;
  }
}

export function saveCalibrationsLocal(cals: SpriteCalibrations): void {
  if (typeof window === "undefined" || !window.localStorage) return;
  window.localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(cals));
}

export function getCalibration(
  cals: SpriteCalibrations,
  kind: CalibrationKind,
  name: string,
): Calibration {
  return cals[kind][name] ?? DEFAULT_CALIBRATION;
}

export function setCalibration(
  cals: SpriteCalibrations,
  kind: CalibrationKind,
  name: string,
  cal: Calibration,
): SpriteCalibrations {
  return {
    ...cals,
    [kind]: { ...cals[kind], [name]: cal },
  };
}

// Serialize for download — pretty-printed, sorted keys, matches the data-file
// convention so PR diffs are reviewable.
export function serializeForDownload(cals: SpriteCalibrations): string {
  const sortBucket = (b: Record<string, Calibration>): Record<string, Calibration> => {
    const out: Record<string, Calibration> = {};
    for (const k of Object.keys(b).sort()) out[k] = b[k]!;
    return out;
  };
  const sorted: SpriteCalibrations = {
    schema_version: 1,
    buildings: sortBucket(cals.buildings),
    troops: sortBucket(cals.troops),
    effects: sortBucket(cals.effects),
    traps: sortBucket(cals.traps),
  };
  return JSON.stringify(sorted, null, 2) + "\n";
}
