// Sprite loader — PRD §8.3.
// Attempts to load every expected sprite path on app start. Successful loads
// return a Texture; missing files resolve to null (caller renders magenta placeholder).

import { Assets, Texture } from "pixi.js";

const BUILDING_TYPES = [
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

const TROOP_TYPES = [
  "barbarian",
  "archer",
  "giant",
  "goblin",
  "wall_breaker",
  "wizard",
];

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
      return [t, tex] as const;
    }),
    ...TROOP_TYPES.map(async (t) => {
      const tex = await tryLoad(`/sprites/troops/${t}.png`);
      return [t, tex] as const;
    }),
  ]);
  return new Map(entries);
}

export function anySpritesLoaded(map: SpriteMap): boolean {
  for (const tex of map.values()) {
    if (tex !== null) return true;
  }
  return false;
}
