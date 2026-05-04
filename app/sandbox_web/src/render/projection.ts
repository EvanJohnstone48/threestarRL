// Top-down projection helpers for the 50x50 sandbox grid.
//
// Coordinate convention (matches sandbox-core PRD §5.1): row increases
// downward, col increases rightward, origin at the top-left tile.

export const GRID_SIZE = 50;
export const TILE_SIZE = 32;

// Inner buildable region (PRD §5.1): rows 3..46, cols 3..46.
export const BUILDABLE_MIN = 3;
export const BUILDABLE_MAX_EXCLUSIVE = 47;

export interface ScreenPoint {
  x: number;
  y: number;
}

export function gridToScreen(row: number, col: number, tileSize: number = TILE_SIZE): ScreenPoint {
  return { x: col * tileSize, y: row * tileSize };
}

export function screenToGrid(
  x: number,
  y: number,
  tileSize: number = TILE_SIZE,
): { row: number; col: number } {
  return { row: y / tileSize, col: x / tileSize };
}

export function isInDeployRing(row: number, col: number): boolean {
  if (row < 0 || row >= GRID_SIZE || col < 0 || col >= GRID_SIZE) return false;
  return (
    row < BUILDABLE_MIN ||
    row >= BUILDABLE_MAX_EXCLUSIVE ||
    col < BUILDABLE_MIN ||
    col >= BUILDABLE_MAX_EXCLUSIVE
  );
}
