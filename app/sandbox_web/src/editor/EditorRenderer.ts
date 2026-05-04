import {
  Application,
  Container,
  Graphics,
  Text,
  TextStyle,
  FederatedPointerEvent,
} from "pixi.js";
import type { BuildingPlacement } from "@/generated_types";
import {
  buildingColor,
  buildingLabel,
  categoryForBuilding,
  COLOR_BUILDABLE,
  COLOR_DEPLOY_RING,
  COLOR_GRID_BG,
  COLOR_GRID_LINE,
} from "@/render/colors";
import { footprintFor } from "@/render/footprints";
import {
  BUILDABLE_MAX_EXCLUSIVE,
  BUILDABLE_MIN,
  GRID_SIZE,
  TILE_SIZE,
  gridToScreen,
} from "@/render/projection";
import type { GhostLegality } from "./editorState";

const ZOOM_MIN = 0.25;
const ZOOM_MAX = 4;
const CLICK_THRESHOLD_SQ = 25;

const labelStyleTiny = new TextStyle({
  fontFamily: "monospace",
  fontSize: 9,
  fill: 0x111111,
});

export class EditorRenderer {
  private app: Application;
  private camera: Container;
  private gridLayer: Container;
  private buildingLayer: Container;
  private ghostLayer: Container;
  private dragging = false;
  private lastPointer: { x: number; y: number } | null = null;
  private pointerDownPos: { x: number; y: number } | null = null;

  onTileClick: ((row: number, col: number) => void) | null = null;
  onTileHover: ((row: number, col: number) => void) | null = null;
  onBuildingClick: ((index: number) => void) | null = null;
  onBuildingRightClick: ((index: number) => void) | null = null;
  onTileRightClick: ((row: number, col: number) => void) | null = null;
  onPaintStart: ((row: number, col: number) => boolean) | null = null;
  onPaintMove: ((row: number, col: number) => void) | null = null;
  onPaintEnd: ((row: number, col: number) => void) | null = null;

  private buildingHitAreas: { index: number; x: number; y: number; w: number; h: number }[] = [];
  private paintLayer: Container;
  private highlightLayer: Container;
  private _isPainting = false;

  constructor(app: Application) {
    this.app = app;
    this.camera = new Container();
    this.gridLayer = new Container();
    this.buildingLayer = new Container();
    this.paintLayer = new Container();
    this.highlightLayer = new Container();
    this.ghostLayer = new Container();
    this.camera.addChild(this.gridLayer);
    this.camera.addChild(this.buildingLayer);
    this.camera.addChild(this.paintLayer);
    this.camera.addChild(this.highlightLayer);
    this.camera.addChild(this.ghostLayer);
    this.app.stage.addChild(this.camera);

    this.drawGrid();
    this.attachInteractions();
    this.fitToGrid();
  }

  private drawGrid(): void {
    const bg = new Graphics();
    bg.rect(0, 0, GRID_SIZE * TILE_SIZE, GRID_SIZE * TILE_SIZE).fill(COLOR_GRID_BG);
    this.gridLayer.addChild(bg);

    const inset = BUILDABLE_MIN * TILE_SIZE;
    const innerSize = (BUILDABLE_MAX_EXCLUSIVE - BUILDABLE_MIN) * TILE_SIZE;
    const inner = new Graphics();
    inner.rect(inset, inset, innerSize, innerSize).fill(COLOR_BUILDABLE);
    this.gridLayer.addChild(inner);

    const ring = new Graphics();
    ring
      .rect(0, 0, GRID_SIZE * TILE_SIZE, GRID_SIZE * TILE_SIZE)
      .stroke({ color: COLOR_DEPLOY_RING, width: 2 });
    this.gridLayer.addChild(ring);

    const lines = new Graphics();
    for (let i = 0; i <= GRID_SIZE; i++) {
      const v = i * TILE_SIZE;
      lines.moveTo(v, 0).lineTo(v, GRID_SIZE * TILE_SIZE);
      lines.moveTo(0, v).lineTo(GRID_SIZE * TILE_SIZE, v);
    }
    lines.stroke({ color: COLOR_GRID_LINE, width: 1, alpha: 0.5 });
    this.gridLayer.addChild(lines);

    const innerOutline = new Graphics();
    innerOutline
      .rect(inset, inset, innerSize, innerSize)
      .stroke({ color: 0x4a5568, width: 1.5, alpha: 0.8 });
    this.gridLayer.addChild(innerOutline);
  }

  renderBuildings(placements: BuildingPlacement[]): void {
    this.buildingLayer.removeChildren();
    this.buildingHitAreas = [];

    for (let i = 0; i < placements.length; i++) {
      const p = placements[i];
      const [rows, cols] = footprintFor(p.building_type);
      const { x, y } = gridToScreen(p.origin[0], p.origin[1]);
      const w = cols * TILE_SIZE;
      const h = rows * TILE_SIZE;

      const rect = new Graphics();
      const cat = categoryForBuilding(p.building_type);
      rect.rect(x, y, w, h).fill(buildingColor(cat));
      rect.rect(x, y, w, h).stroke({ color: 0x000000, width: 1, alpha: 0.4 });
      this.buildingLayer.addChild(rect);

      const label = buildingLabel(p.building_type, p.level ?? 1);
      if (label) {
        const text = new Text({ text: label, style: labelStyleTiny });
        text.x = x + w / 2 - text.width / 2;
        text.y = y + h / 2 - text.height / 2;
        this.buildingLayer.addChild(text);
      }

      this.buildingHitAreas.push({ index: i, x, y, w, h });
    }
  }

  renderGhost(
    buildingType: string,
    origin: [number, number],
    legality: GhostLegality,
  ): void {
    this.ghostLayer.removeChildren();
    const [rows, cols] = footprintFor(buildingType);
    const { x, y } = gridToScreen(origin[0], origin[1]);
    const w = cols * TILE_SIZE;
    const h = rows * TILE_SIZE;

    const color = legality === "legal" ? 0x00ff00 : 0xff4444;
    const ghost = new Graphics();
    ghost.rect(x, y, w, h).fill({ color, alpha: 0.35 });
    ghost.rect(x, y, w, h).stroke({ color, width: 2, alpha: 0.9 });
    this.ghostLayer.addChild(ghost);
  }

  clearGhost(): void {
    this.ghostLayer.removeChildren();
  }

  renderWallPreview(tiles: [number, number][]): void {
    this.paintLayer.removeChildren();
    for (const [row, col] of tiles) {
      const { x, y } = gridToScreen(row, col);
      const g = new Graphics();
      g.rect(x, y, TILE_SIZE, TILE_SIZE).fill({ color: 0x44aaff, alpha: 0.5 });
      g.rect(x, y, TILE_SIZE, TILE_SIZE).stroke({ color: 0x88ccff, width: 1, alpha: 0.8 });
      this.paintLayer.addChild(g);
    }
  }

  clearWallPreview(): void {
    this.paintLayer.removeChildren();
  }

  renderHoverHighlight(tile: [number, number] | null): void {
    this.highlightLayer.removeChildren();
    if (!tile) return;
    const { x, y } = gridToScreen(tile[0], tile[1]);
    const g = new Graphics();
    g.rect(x, y, TILE_SIZE, TILE_SIZE).fill({ color: 0xff4444, alpha: 0.4 });
    this.highlightLayer.addChild(g);
  }

  fitToGrid(): void {
    const screen = this.app.screen;
    const gridPx = GRID_SIZE * TILE_SIZE;
    const scale = Math.min(screen.width / gridPx, screen.height / gridPx) * 0.95;
    this.camera.scale.set(scale, scale);
    this.camera.x = (screen.width - gridPx * scale) / 2;
    this.camera.y = (screen.height - gridPx * scale) / 2;
  }

  private screenToTile(screenX: number, screenY: number): { row: number; col: number } {
    const worldX = (screenX - this.camera.x) / this.camera.scale.x;
    const worldY = (screenY - this.camera.y) / this.camera.scale.y;
    return {
      row: Math.floor(worldY / TILE_SIZE),
      col: Math.floor(worldX / TILE_SIZE),
    };
  }

  private setZoom(newScale: number, centerX: number, centerY: number): void {
    const clamped = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, newScale));
    const old = this.camera.scale.x;
    if (clamped === old) return;
    const worldX = (centerX - this.camera.x) / old;
    const worldY = (centerY - this.camera.y) / old;
    this.camera.scale.set(clamped, clamped);
    this.camera.x = centerX - worldX * clamped;
    this.camera.y = centerY - worldY * clamped;
  }

  private attachInteractions(): void {
    const stage = this.app.stage;
    stage.eventMode = "static";
    stage.hitArea = this.app.screen;

    stage.on("pointerdown", (e: FederatedPointerEvent) => {
      this.dragging = false;
      this.lastPointer = { x: e.global.x, y: e.global.y };
      this.pointerDownPos = { x: e.global.x, y: e.global.y };
      if (e.button === 0 && this.onPaintStart) {
        const tile = this.screenToTile(e.global.x, e.global.y);
        const accepted = this.onPaintStart(tile.row, tile.col);
        if (accepted) this._isPainting = true;
      }
    });

    stage.on("pointermove", (e: FederatedPointerEvent) => {
      if (this.lastPointer !== null) {
        const dx = e.global.x - this.lastPointer.x;
        const dy = e.global.y - this.lastPointer.y;
        if (dx * dx + dy * dy > CLICK_THRESHOLD_SQ) {
          this.dragging = true;
        }
        if (this.dragging && !this._isPainting) {
          this.camera.x += dx;
          this.camera.y += dy;
        }
        this.lastPointer = { x: e.global.x, y: e.global.y };
      }
      const tile = this.screenToTile(e.global.x, e.global.y);
      this.onTileHover?.(tile.row, tile.col);
      if (this._isPainting) {
        this.onPaintMove?.(tile.row, tile.col);
      }
    });

    stage.on("pointerup", (e: FederatedPointerEvent) => {
      const tile = this.screenToTile(e.global.x, e.global.y);
      const worldX = (e.global.x - this.camera.x) / this.camera.scale.x;
      const worldY = (e.global.y - this.camera.y) / this.camera.scale.y;

      if (this._isPainting) {
        this._isPainting = false;
        this.onPaintEnd?.(tile.row, tile.col);
      } else if (!this.dragging && this.pointerDownPos) {
        const dx = e.global.x - this.pointerDownPos.x;
        const dy = e.global.y - this.pointerDownPos.y;
        if (dx * dx + dy * dy < CLICK_THRESHOLD_SQ) {
          const isRight = e.button === 2;
          // Check building hit areas first
          let hitBuilding = false;
          for (let i = this.buildingHitAreas.length - 1; i >= 0; i--) {
            const h = this.buildingHitAreas[i];
            if (worldX >= h.x && worldX < h.x + h.w && worldY >= h.y && worldY < h.y + h.h) {
              if (isRight) {
                this.onBuildingRightClick?.(h.index);
              } else {
                this.onBuildingClick?.(h.index);
              }
              hitBuilding = true;
              break;
            }
          }
          if (!hitBuilding) {
            if (isRight) {
              this.onTileRightClick?.(tile.row, tile.col);
            } else {
              this.onTileClick?.(tile.row, tile.col);
            }
          }
        }
      }
      this.dragging = false;
      this._isPainting = false;
      this.lastPointer = null;
      this.pointerDownPos = null;
    });

    stage.on("pointerupoutside", () => {
      if (this._isPainting) {
        this._isPainting = false;
        // fire paintEnd at last known tile — no-op is fine
      }
      this.dragging = false;
      this._isPainting = false;
      this.lastPointer = null;
      this.pointerDownPos = null;
    });

    const canvas = this.app.canvas;
    canvas.addEventListener("contextmenu", (ev: MouseEvent) => {
      ev.preventDefault();
    });
    canvas.addEventListener("wheel", (ev: WheelEvent) => {
      ev.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const factor = ev.deltaY < 0 ? 1.15 : 1 / 1.15;
      this.setZoom(this.camera.scale.x * factor, ev.clientX - rect.left, ev.clientY - rect.top);
    });
  }

  destroy(): void {
    this.camera.destroy({ children: true });
  }
}
