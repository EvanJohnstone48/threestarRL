// 2:1 dimetric (isometric) projection helpers — PRD §8.2.
// Formula: screen_x = (col − row) × 32 + canvas_center_x
//          screen_y = (col + row) × 16 + canvas_center_y

export const ISO_TILE_W = 64; // diamond tile width
export const ISO_TILE_H = 32; // diamond tile height

const HALF_W = ISO_TILE_W / 2; // 32 — horizontal stride per row or col step
const HALF_H = ISO_TILE_H / 2; // 16 — vertical stride per row or col step

export interface ScreenPoint {
  x: number;
  y: number;
}

// Returns the screen position of grid corner (row, col). This point is the
// north corner of the diamond for tile (row, col).
// canvasCenterX/Y default to 0; callers let the PixiJS camera container handle
// pan/zoom rather than baking offsets into world coords.
export function gridToIsoScreen(
  row: number,
  col: number,
  canvasCenterX = 0,
  canvasCenterY = 0,
): ScreenPoint {
  return {
    x: (col - row) * HALF_W + canvasCenterX,
    y: (col + row) * HALF_H + canvasCenterY,
  };
}

// Inverse of gridToIsoScreen — returns fractional (row, col) grid coordinates.
// Derived by solving the forward system:
//   dx = (col − row) × 32  →  col − row = dx / 32
//   dy = (col + row) × 16  →  col + row = dy / 16
export function isoScreenToGrid(
  screenX: number,
  screenY: number,
  canvasCenterX = 0,
  canvasCenterY = 0,
): { row: number; col: number } {
  const dx = screenX - canvasCenterX;
  const dy = screenY - canvasCenterY;
  return {
    col: dx / (2 * HALF_W) + dy / (2 * HALF_H),
    row: dy / (2 * HALF_H) - dx / (2 * HALF_W),
  };
}
