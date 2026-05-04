// Sprite loader — PRD §8.3.
// Attempts to load every expected sprite path on app start. Successful loads
// return a Texture; missing files resolve to null (caller renders magenta placeholder).

import { Assets, Texture } from "pixi.js";

export const BUILDING_TYPES = [
  "town_hall",
  "clan_castle",
  "army_camp",
  "cannon",
  "archer_tower",
  "mortar",
  "air_defense",
  "wizard_tower",
  "barracks",
  "laboratory",
  "spell_factory",
  "gold_mine",
  "elixir_collector",
  "gold_storage",
  "elixir_storage",
  "builders_hut",
  "wall",
];

export const TROOP_TYPES = ["barbarian", "archer", "giant", "goblin", "wall_breaker", "wizard"];

export const EFFECT_TYPES = ["explosion", "bolt", "splash"];

export type SpriteMap = Map<string, Texture | null>;

async function tryLoad(url: string): Promise<Texture | null> {
  try {
    return await Assets.load<Texture>(url);
  } catch {
    return null;
  }
}

export async function loadAllSprites(): Promise<SpriteMap> {
  const entries = await Promise.all([
    ...BUILDING_TYPES.map(async (t) => {
      const tex = await tryLoad(`/sprites/buildings/${t}.png`);
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
