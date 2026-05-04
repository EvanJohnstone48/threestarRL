// Hitbox geometry — TypeScript port of sandbox-core's grid.py rule.
// PRD §5.4: hitbox_inset default = max(footprint_size / 2 - 0.5, 0.5),
// with army_camp overridden to 1.0 in manual_overrides.json.
// Walls are a special case: footprint = hitbox = 1×1 (the full tile).

const INSET_OVERRIDES: Record<string, number> = {
  army_camp: 1.0,
};

export function hitboxInsetTiles(buildingType: string, footprintSize: number): number {
  if (buildingType === "wall") return 0;
  const override = INSET_OVERRIDES[buildingType];
  if (override !== undefined) return override;
  return Math.max(footprintSize / 2 - 0.5, 0.5);
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
  if (buildingType === "wall") {
    return { rowMin: r0, rowMax: r0 + fh, colMin: c0, colMax: c0 + fw };
  }
  const inset = hitboxInsetTiles(buildingType, fh);
  return {
    rowMin: r0 + inset,
    rowMax: r0 + fh - inset,
    colMin: c0 + inset,
    colMax: c0 + fw - inset,
  };
}
