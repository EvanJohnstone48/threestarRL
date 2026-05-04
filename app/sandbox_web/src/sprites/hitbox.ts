// Hitbox geometry — TypeScript port of sandbox-core's grid.py rule.
// PRD §5.4: hitbox_inset default = 0.5 tiles for every footprint size.
// Per-entity overrides (kept in sync with app/data/manual_overrides.json):
//   - army_camp → 1.0 (4×4 footprint shrinks to a 2×2 hitbox)
//   - wall      → 0.0 (footprint = hitbox = the full tile)

const INSET_OVERRIDES: Record<string, number> = {
  army_camp: 1.0,
  wall: 0.0,
};

export const DEFAULT_HITBOX_INSET = 0.5;

export function hitboxInsetTiles(buildingType: string, _footprintSize: number): number {
  const override = INSET_OVERRIDES[buildingType];
  return override !== undefined ? override : DEFAULT_HITBOX_INSET;
}

export interface HitboxRect {
  rowMin: number;
  rowMax: number;
  colMin: number;
  colMax: number;
}

// Square hitbox in tile coordinates (footprint shrunk by inset on every side).
export function hitboxRect(
  buildingType: string,
  origin: [number, number],
  footprint: [number, number],
): HitboxRect {
  const [r0, c0] = origin;
  const [fh, fw] = footprint;
  const inset = hitboxInsetTiles(buildingType, fh);
  return {
    rowMin: r0 + inset,
    rowMax: r0 + fh - inset,
    colMin: c0 + inset,
    colMax: c0 + fw - inset,
  };
}
