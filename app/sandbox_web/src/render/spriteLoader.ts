// Sprite loader — PRD §8.3.
// Attempts to load every expected sprite path on app start. Successful loads
// return a Texture; missing files resolve to null (caller renders magenta placeholder).

import { Assets, Texture } from "pixi.js";
import {
  BUILDING_TYPES,
  EFFECT_TYPES,
  TERRAIN_TYPES,
  TROOP_TYPES,
  buildingSpriteUrlCandidates,
  terrainSpriteUrlCandidates,
} from "./spritePaths";
export {
  BUILDING_TYPES,
  EFFECT_TYPES,
  TERRAIN_TYPES,
  TROOP_TYPES,
  buildingSpriteUrlCandidates,
  terrainSpriteUrlCandidates,
} from "./spritePaths";

export type SpriteMap = Map<string, Texture | null>;

async function tryLoad(url: string): Promise<Texture | null> {
  try {
    return await Assets.load<Texture>(url);
  } catch {
    return null;
  }
}

async function tryLoadFirst(urls: string[]): Promise<Texture | null> {
  for (const url of urls) {
    const tex = await tryLoad(url);
    if (tex !== null) return tex;
  }
  return null;
}

export async function loadAllSprites(): Promise<SpriteMap> {
  const entries = await Promise.all([
    ...BUILDING_TYPES.map(async (t) => {
      const tex = await tryLoadFirst(buildingSpriteUrlCandidates(t));
      return [`building:${t}`, tex] as const;
    }),
    ...TROOP_TYPES.map(async (t) => {
      const tex = await tryLoad(`/sprites/troops/${t}.png`);
      return [`troop:${t}`, tex] as const;
    }),
    ...EFFECT_TYPES.map(async (t) => {
      const tex = await tryLoad(`/sprites/effects/${t}.png`);
      return [`effect:${t}`, tex] as const;
    }),
    ...TERRAIN_TYPES.map(async (t) => {
      const tex = await tryLoadFirst(terrainSpriteUrlCandidates(t));
      return [`terrain:${t}`, tex] as const;
    }),
  ]);
  // Maintain backward-compat: also register building sprites under their bare
  // type name so the existing iso renderer's map.get(building_type) still works.
  const map = new Map<string, Texture | null>(entries);
  for (const t of BUILDING_TYPES) map.set(t, map.get(`building:${t}`) ?? null);
  return map;
}

export function anySpritesLoaded(map: SpriteMap): boolean {
  for (const tex of map.values()) {
    if (tex !== null) return true;
  }
  return false;
}
