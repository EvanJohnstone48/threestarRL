// Building footprint sizes (square at TH6 — PRD §5.1).
// The replay JSON does not carry footprints; we mirror the content data here.
// When TH7+ entities are added in a future phase, replace this with a loader
// that reads buildings.json from app/data/.

const FOOTPRINTS: Record<string, [number, number]> = {
  town_hall: [4, 4],
  clan_castle: [3, 3],
  army_camp: [4, 4],
  cannon: [3, 3],
  archer_tower: [3, 3],
  mortar: [3, 3],
  air_defense: [3, 3],
  wizard_tower: [3, 3],
  barracks: [3, 3],
  laboratory: [3, 3],
  spell_factory: [3, 3],
  gold_mine: [3, 3],
  elixir_collector: [3, 3],
  gold_storage: [3, 3],
  elixir_storage: [3, 3],
  builders_hut: [2, 2],
  wall: [1, 1],
};

export function footprintFor(buildingType: string): [number, number] {
  return FOOTPRINTS[buildingType] ?? [1, 1];
}

// Troop visual radius in tiles (single-letter circle marker — PRD §8.1).
export const TROOP_VISUAL_RADIUS_TILES = 0.4;
