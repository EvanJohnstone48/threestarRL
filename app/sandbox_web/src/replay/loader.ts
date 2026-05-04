// Replay loading + lightweight validation.
//
// The viewer never re-validates the full Pydantic schema; we only check the
// fields we actually consume so a forward-compatible replay (newer
// schema_version with extra fields) still loads.

import type { Replay } from "@/generated_types";
import { SCHEMA_VERSION } from "@/generated_types";

export class ReplayLoadError extends Error {}

export function parseReplay(text: string): Replay {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch (err) {
    throw new ReplayLoadError(
      `Failed to parse JSON: ${err instanceof Error ? err.message : String(err)}`,
    );
  }
  return validateReplay(parsed);
}

export function validateReplay(value: unknown): Replay {
  if (!isObject(value)) {
    throw new ReplayLoadError("Replay must be a JSON object.");
  }
  for (const key of ["schema_version", "metadata", "initial_state", "frames"]) {
    if (!(key in value)) {
      throw new ReplayLoadError(`Replay is missing required field "${key}".`);
    }
  }
  if (!Array.isArray(value.frames)) {
    throw new ReplayLoadError(`Replay.frames must be an array.`);
  }
  if (!isObject(value.metadata) || typeof value.metadata.sim_version !== "string") {
    throw new ReplayLoadError(`Replay.metadata.sim_version must be a string.`);
  }
  return value as unknown as Replay;
}

export async function loadReplayFromFile(file: File): Promise<Replay> {
  const text = await file.text();
  return parseReplay(text);
}

export async function loadReplayFromUrl(url: string): Promise<Replay> {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new ReplayLoadError(
      `Failed to fetch replay from "${url}": HTTP ${resp.status} ${resp.statusText}.`,
    );
  }
  const text = await resp.text();
  return parseReplay(text);
}

// Returns null if the replay schema_version matches the runtime; otherwise
// returns a banner message per PRD §8.5.
export function crossVersionBanner(replay: Replay, runtimeSchemaVersion: number): string | null {
  if (replay.schema_version === runtimeSchemaVersion) return null;
  return `Replay schema_version ${replay.schema_version} loaded under runtime ${runtimeSchemaVersion} — playback only.`;
}

export function simVersionBanner(replay: Replay, runtimeSimVersion: string): string | null {
  if (replay.metadata.sim_version === runtimeSimVersion) return null;
  return `Replay sim_version ${replay.metadata.sim_version} loaded under runtime ${runtimeSimVersion} — playback only.`;
}

export const RUNTIME_SCHEMA_VERSION = SCHEMA_VERSION;

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
