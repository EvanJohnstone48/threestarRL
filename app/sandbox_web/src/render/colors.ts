// Color and label conventions for the procedural top-down view.
// Matches PRD §8.1 / §8.4 — buildings render as colored rectangles with
// short text labels (e.g. "C6"); troops render as colored circles with a
// single-letter label.

import type { BuildingCategory, TroopCategory } from "@/generated_types";

export const COLOR_GRID_BG = 0x141a22;
export const COLOR_GRID_LINE = 0x222a36;
export const COLOR_DEPLOY_RING = 0x2a323e;
export const COLOR_BUILDABLE = 0x1a2230;
export const COLOR_PROJECTILE = 0xffeaa7;
export const COLOR_SPELL_RADIUS = 0xb084ff;
export const COLOR_HP_FULL = 0x4caf50;
export const COLOR_HP_MID = 0xffc107;
export const COLOR_HP_LOW = 0xf44336;

export const BUILDING_COLORS: Record<BuildingCategory, number> = {
  town_hall: 0xf6c453,
  clan_castle: 0xa07cff,
  defense: 0xe57373,
  wall: 0x8d8470,
  resource_collector: 0xffcc80,
  resource_storage: 0xff9933,
  army: 0xc0c0c0,
  builder_hut: 0xb9d4ff,
};

export const TROOP_COLORS: Record<TroopCategory, number> = {
  ground: 0x66bb6a,
  air: 0x29b6f6,
};

const BUILDING_LABEL_PREFIX: Record<string, string> = {
  town_hall: "TH",
  clan_castle: "CC",
  cannon: "C",
  archer_tower: "AT",
  mortar: "MT",
  air_defense: "AD",
  wizard_tower: "WT",
  wall: "",
  army_camp: "AC",
  barracks: "BK",
  laboratory: "LB",
  spell_factory: "SF",
  gold_mine: "GM",
  elixir_collector: "EC",
  gold_storage: "GS",
  elixir_storage: "ES",
  builders_hut: "BH",
};

export function buildingLabel(buildingType: string, level: number): string {
  const prefix = BUILDING_LABEL_PREFIX[buildingType] ?? buildingType.slice(0, 2).toUpperCase();
  if (prefix === "") return "";
  return `${prefix}${level}`;
}

export function troopLabel(troopType: string): string {
  return troopType.charAt(0).toUpperCase();
}

// HP-bar color: green at full, yellow ~50%, red below ~25%.
export function hpBarColor(hp: number, maxHp: number): number {
  if (maxHp <= 0) return COLOR_HP_FULL;
  const ratio = hp / maxHp;
  if (ratio > 0.5) return COLOR_HP_FULL;
  if (ratio > 0.25) return COLOR_HP_MID;
  return COLOR_HP_LOW;
}

export function buildingColor(category: BuildingCategory): number {
  return BUILDING_COLORS[category];
}

export function troopColor(category: TroopCategory): number {
  return TROOP_COLORS[category];
}

// Closed v1 TH6 entity set (PRD §9.7). Used by the renderer to color
// buildings by category without having to load the full content data files
// alongside the replay. Anything not in this map falls back to "defense"
// coloring with a console warning at render time.
const BUILDING_CATEGORY: Record<string, BuildingCategory> = {
  town_hall: "town_hall",
  clan_castle: "clan_castle",
  cannon: "defense",
  archer_tower: "defense",
  mortar: "defense",
  air_defense: "defense",
  wizard_tower: "defense",
  wall: "wall",
  army_camp: "army",
  barracks: "army",
  laboratory: "army",
  spell_factory: "army",
  gold_mine: "resource_collector",
  elixir_collector: "resource_collector",
  gold_storage: "resource_storage",
  elixir_storage: "resource_storage",
  builders_hut: "builder_hut",
};

export function categoryForBuilding(buildingType: string): BuildingCategory {
  return BUILDING_CATEGORY[buildingType] ?? "defense";
}
