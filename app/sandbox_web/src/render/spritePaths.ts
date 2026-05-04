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

export const TERRAIN_TYPES = ["deploy_zone", "grass", "darkgrass", "building_grass"];

const LEGACY_BUILDING_SPRITE_FILENAMES: Record<string, string[]> = {
  barracks: ["barracls.png"],
  spell_factory: ["spell+factory.png"],
  builders_hut: ["builder_hut.png"],
};

export function buildingSpriteUrlCandidates(buildingType: string): string[] {
  return [
    `/sprites/buildings/${buildingType}.png`,
    ...(LEGACY_BUILDING_SPRITE_FILENAMES[buildingType] ?? []).map(
      (filename) => `/sprites/buildings/${filename}`,
    ),
  ];
}

export function terrainSpriteUrlCandidates(terrainType: string): string[] {
  if (terrainType === "building_grass") {
    return [
      "/sprites/terrain/building_grass.png",
      "/sprites/terrain/building_underspace_grass.png",
    ];
  }
  return [`/sprites/terrain/${terrainType}.png`];
}
