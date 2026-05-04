// Isometric PixiJS renderer — PRD §8.2.
//
// Projection: 2:1 dimetric, 64×32 px tile diamonds.
//   screen_x = (col − row) × 32;  screen_y = (col + row) × 16
// Sprite anchor: bottom-center of PNG canvas pinned to the south corner of the
// building's footprint diamond (footprint = placement geometry = hitbox for
// sprite purposes). Z-order by (south_row + south_col) of entity footprint.

import {
  Application,
  Container,
  Graphics,
  Sprite,
  Text,
  TextStyle,
  FederatedPointerEvent,
} from "pixi.js";

import type { BuildingState, TickFrame } from "@/generated_types";
import type { InterpolatedFrame } from "@/replay/interpolation";
import {
  COLOR_BUILDABLE,
  COLOR_GRID_BG,
  COLOR_PROJECTILE,
  buildingLabel,
  hpBarColor,
} from "./colors";
import { footprintFor, TROOP_VISUAL_RADIUS_TILES } from "./footprints";
import { gridToIsoScreen, ISO_TILE_H, ISO_TILE_W } from "./isoProjection";
import { GRID_SIZE, TILE_SIZE, isInDeployRing } from "./projection";
import type { SpriteMap } from "./spriteLoader";
import {
  DEFAULT_CALIBRATION,
  getCalibration,
  loadCalibrations,
  type Calibration,
  type SpriteCalibrations,
} from "@/sprites/calibrations";

const ZOOM_MIN = 0.25;
const ZOOM_MAX = 4;
const CLICK_THRESHOLD_SQ = 25; // 5px

const HP_BAR_BUILDING_W = 24;
const HP_BAR_BUILDING_H = 4;
const HP_BAR_TROOP_W = 16;
const HP_BAR_TROOP_H = 3;

const placeholderStyle = new TextStyle({
  fontFamily: "monospace",
  fontSize: 9,
  fill: 0xffffff,
});

const troopLabelStyle = new TextStyle({
  fontFamily: "monospace",
  fontSize: 10,
  fill: 0xffffff,
});

type EntityHitArea =
  | { kind: "building"; id: number; left: number; right: number; top: number; bottom: number }
  | { kind: "troop"; id: number; cx: number; cy: number; r: number };

// Full iso world extents (GRID_SIZE = 50):
//   x: [−GRID_SIZE*32, GRID_SIZE*32] = [−1600, 1600]  → width 3200
//   y: [0, GRID_SIZE*32]             = [0, 1600]        → height 1600
const ISO_WORLD_W = GRID_SIZE * ISO_TILE_W; // 3200
const ISO_WORLD_H = GRID_SIZE * ISO_TILE_H; // 1600

// Troop circle radius in iso world pixels (same scale as top-down).
const TROOP_ISO_RADIUS = TROOP_VISUAL_RADIUS_TILES * TILE_SIZE;

export class IsoRenderer {
  private app: Application;
  private camera: Container;
  private gridLayer: Container;
  private entityLayer: Container;
  private hpBarLayer: Container;
  private sprites: SpriteMap;
  private calibrations: SpriteCalibrations;
  private terrainSignature: string | null = null;

  private dragging = false;
  private lastPointer: { x: number; y: number } | null = null;
  private pointerDownPos: { x: number; y: number } | null = null;
  private entityHitAreas: EntityHitArea[] = [];

  onEntityClick: ((kind: "building" | "troop", id: number) => void) | null = null;
  onBackgroundClick: (() => void) | null = null;

  constructor(app: Application, sprites: SpriteMap, calibrations?: SpriteCalibrations) {
    this.app = app;
    this.sprites = sprites;
    this.calibrations = calibrations ?? loadCalibrations();

    this.camera = new Container();
    this.gridLayer = new Container();
    this.entityLayer = new Container();
    this.hpBarLayer = new Container();

    this.camera.addChild(this.gridLayer);
    this.camera.addChild(this.entityLayer);
    this.camera.addChild(this.hpBarLayer);
    this.app.stage.addChild(this.camera);

    this.attachInteractions();
    this.fitToGrid();
  }

  setVisible(visible: boolean): void {
    this.camera.visible = visible;
  }

  renderFrame(frame: InterpolatedFrame, currentTickFrame: TickFrame): void {
    this.updateTerrain(currentTickFrame.state.buildings);
    this.entityLayer.removeChildren();
    this.hpBarLayer.removeChildren();
    this.entityHitAreas = [];

    type DrawItem = { z: number; draw: () => void; hp?: (() => void) | undefined };
    const items: DrawItem[] = [];

    for (const b of currentTickFrame.state.buildings) {
      if (b.destroyed) continue;
      const [fh, fw] = footprintFor(b.building_type);
      const r0 = b.origin[0];
      const c0 = b.origin[1];
      // South corner of footprint — anchor point for sprite
      const south = gridToIsoScreen(r0 + fh, c0 + fw);
      const z = r0 + fh + c0 + fw;

      // Diamond corners for placeholder / hit area
      const dN = gridToIsoScreen(r0, c0);
      const dE = gridToIsoScreen(r0, c0 + fw);
      const dW = gridToIsoScreen(r0 + fh, c0);

      // Screen bounding box of footprint diamond (for hit detection)
      const left = dW.x;
      const right = dE.x;
      const top = dN.y;
      const bottom = south.y;

      const tex = this.sprites.get(b.building_type) ?? null;
      const cal = getCalibration(this.calibrations, "buildings", b.building_type);

      items.push({
        z,
        draw: () => {
          if (tex) {
            const spr = new Sprite(tex);
            spr.anchor.set(0.5, 1.0);
            spr.x = south.x + cal.offset_x;
            spr.y = south.y + cal.offset_y;
            spr.scale.set(cal.scale, cal.scale);
            this.entityLayer.addChild(spr);
          } else {
            this.drawPlaceholderBuilding(b.building_type, b.level, r0, c0, fh, fw);
          }
        },
        hp:
          b.hp < b.max_hp
            ? () => {
                this.drawHpBar(
                  south.x - HP_BAR_BUILDING_W / 2,
                  top - HP_BAR_BUILDING_H - 2,
                  HP_BAR_BUILDING_W,
                  HP_BAR_BUILDING_H,
                  b.hp,
                  b.max_hp,
                );
              }
            : undefined,
      });

      this.entityHitAreas.push({ kind: "building", id: b.id, left, right, top, bottom });
    }

    for (const p of frame.projectiles) {
      const pos = gridToIsoScreen(p.current_position[0], p.current_position[1]);
      const z = p.current_position[0] + p.current_position[1];
      items.push({
        z,
        draw: () => {
          const dot = new Graphics();
          dot.circle(pos.x, pos.y, 3).fill(COLOR_PROJECTILE);
          this.entityLayer.addChild(dot);
        },
      });
    }

    for (const t of frame.troops) {
      if (t.destroyed) continue;
      const pos = gridToIsoScreen(t.position[0], t.position[1]);
      const z = t.position[0] + t.position[1];
      const troopTex = this.sprites.get(`troop:${t.troop_type}`) ?? null;
      const cal: Calibration = troopTex
        ? getCalibration(this.calibrations, "troops", t.troop_type)
        : DEFAULT_CALIBRATION;
      items.push({
        z,
        draw: () => {
          if (troopTex) {
            const spr = new Sprite(troopTex);
            spr.anchor.set(0.5, 0.5);
            spr.x = pos.x + cal.offset_x;
            spr.y = pos.y + cal.offset_y;
            spr.scale.set(cal.scale, cal.scale);
            this.entityLayer.addChild(spr);
          } else {
            const circle = new Graphics();
            circle.circle(pos.x, pos.y, TROOP_ISO_RADIUS).fill(0x66bb6a);
            circle
              .circle(pos.x, pos.y, TROOP_ISO_RADIUS)
              .stroke({ color: 0x000000, width: 1, alpha: 0.6 });
            this.entityLayer.addChild(circle);

            const label = t.troop_type.charAt(0).toUpperCase();
            const text = new Text({ text: label, style: troopLabelStyle });
            text.x = pos.x - text.width / 2;
            text.y = pos.y - text.height / 2;
            this.entityLayer.addChild(text);
          }
        },
        hp:
          t.hp < t.max_hp
            ? () => {
                this.drawHpBar(
                  pos.x - HP_BAR_TROOP_W / 2,
                  pos.y - TROOP_ISO_RADIUS - HP_BAR_TROOP_H - 2,
                  HP_BAR_TROOP_W,
                  HP_BAR_TROOP_H,
                  t.hp,
                  t.max_hp,
                );
              }
            : undefined,
      });

      this.entityHitAreas.push({
        kind: "troop",
        id: t.id,
        cx: pos.x,
        cy: pos.y,
        r: TROOP_ISO_RADIUS,
      });
    }

    items.sort((a, b) => a.z - b.z);
    for (const item of items) {
      item.draw();
      item.hp?.();
    }
  }

  private updateTerrain(buildings: BuildingState[]): void {
    const signature = this.terrainMaskSignature(buildings);
    if (signature === this.terrainSignature) return;
    this.terrainSignature = signature;
    this.gridLayer.removeChildren();

    const buildingTiles = this.buildingFootprintTiles(buildings);
    for (let row = 0; row < GRID_SIZE; row++) {
      for (let col = 0; col < GRID_SIZE; col++) {
        const terrainKey = this.terrainKeyForTile(row, col, buildingTiles);
        this.drawTerrainTile(row, col, terrainKey);
      }
    }
  }

  private terrainMaskSignature(buildings: BuildingState[]): string {
    return buildings
      .map((b) => `${b.id}:${b.building_type}:${b.origin[0]},${b.origin[1]}`)
      .sort()
      .join("|");
  }

  private buildingFootprintTiles(buildings: BuildingState[]): Set<string> {
    const out = new Set<string>();
    for (const building of buildings) {
      const [fh, fw] = footprintFor(building.building_type);
      const [r0, c0] = building.origin;
      for (let row = r0; row < r0 + fh; row++) {
        for (let col = c0; col < c0 + fw; col++) {
          if (row >= 0 && row < GRID_SIZE && col >= 0 && col < GRID_SIZE) {
            out.add(`${row},${col}`);
          }
        }
      }
    }
    return out;
  }

  private terrainKeyForTile(row: number, col: number, buildingTiles: Set<string>): string {
    if (isInDeployRing(row, col)) return "deploy_zone";
    if (buildingTiles.has(`${row},${col}`)) return "building_grass";
    return (row + col) % 2 === 0 ? "grass" : "darkgrass";
  }

  private drawTerrainTile(row: number, col: number, terrainKey: string): void {
    const tex = this.sprites.get(`terrain:${terrainKey}`) ?? null;
    const north = gridToIsoScreen(row, col);
    if (tex) {
      const tile = new Sprite(tex);
      tile.anchor.set(0.5, 0);
      tile.x = north.x;
      tile.y = north.y;
      tile.width = ISO_TILE_W;
      tile.height = ISO_TILE_H;
      this.gridLayer.addChild(tile);
      return;
    }

    const N = north;
    const E = gridToIsoScreen(row, col + 1);
    const S = gridToIsoScreen(row + 1, col + 1);
    const W = gridToIsoScreen(row + 1, col);
    const color =
      terrainKey === "deploy_zone"
        ? COLOR_GRID_BG
        : terrainKey === "building_grass"
          ? COLOR_BUILDABLE
          : terrainKey === "grass"
            ? 0x20331f
            : 0x182818;
    const fallback = new Graphics();
    fallback.poly([N.x, N.y, E.x, E.y, S.x, S.y, W.x, W.y]).fill(color);
    this.gridLayer.addChild(fallback);
  }

  private drawPlaceholderBuilding(
    buildingType: string,
    level: number,
    r0: number,
    c0: number,
    fh: number,
    fw: number,
  ): void {
    const N = gridToIsoScreen(r0, c0);
    const E = gridToIsoScreen(r0, c0 + fw);
    const S = gridToIsoScreen(r0 + fh, c0 + fw);
    const W = gridToIsoScreen(r0 + fh, c0);

    const g = new Graphics();
    g.poly([N.x, N.y, E.x, E.y, S.x, S.y, W.x, W.y]).fill(0xff00ff);
    g.poly([N.x, N.y, E.x, E.y, S.x, S.y, W.x, W.y]).stroke({
      color: 0x000000,
      width: 1,
      alpha: 0.4,
    });
    this.entityLayer.addChild(g);

    const label = buildingLabel(buildingType, level) || buildingType.slice(0, 3);
    const text = new Text({ text: label, style: placeholderStyle });
    const cx = (N.x + S.x) / 2;
    const cy = (N.y + S.y) / 2;
    text.x = cx - text.width / 2;
    text.y = cy - text.height / 2;
    this.entityLayer.addChild(text);
  }

  private drawHpBar(x: number, y: number, w: number, h: number, hp: number, maxHp: number): void {
    const bg = new Graphics();
    bg.rect(x, y, w, h).fill(0x0a0a0a);
    this.hpBarLayer.addChild(bg);
    const ratio = Math.max(0, Math.min(1, hp / Math.max(1, maxHp)));
    const fg = new Graphics();
    fg.rect(x, y, w * ratio, h).fill(hpBarColor(hp, maxHp));
    this.hpBarLayer.addChild(fg);
  }

  private handleEntityClick(screenX: number, screenY: number): void {
    const worldX = (screenX - this.camera.x) / this.camera.scale.x;
    const worldY = (screenY - this.camera.y) / this.camera.scale.y;

    for (const hit of this.entityHitAreas) {
      if (hit.kind === "troop") {
        const dx = worldX - hit.cx;
        const dy = worldY - hit.cy;
        if (dx * dx + dy * dy <= hit.r * hit.r) {
          this.onEntityClick?.("troop", hit.id);
          return;
        }
      }
    }
    for (const hit of this.entityHitAreas) {
      if (hit.kind === "building") {
        if (
          worldX >= hit.left &&
          worldX <= hit.right &&
          worldY >= hit.top &&
          worldY <= hit.bottom
        ) {
          this.onEntityClick?.("building", hit.id);
          return;
        }
      }
    }
    this.onBackgroundClick?.();
  }

  fitToGrid(): void {
    const screen = this.app.screen;
    const scale = Math.min(screen.width / ISO_WORLD_W, screen.height / ISO_WORLD_H) * 0.95;
    this.camera.scale.set(scale, scale);
    // Iso grid is symmetric on the x-axis (world x=0 is the horizontal center).
    // World y spans [0, ISO_WORLD_H]; center at ISO_WORLD_H/2.
    this.camera.x = screen.width / 2;
    this.camera.y = (screen.height - ISO_WORLD_H * scale) / 2;
  }

  setZoom(newScale: number, centerX: number, centerY: number): void {
    const clamped = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, newScale));
    const oldScale = this.camera.scale.x;
    if (clamped === oldScale) return;
    const worldX = (centerX - this.camera.x) / oldScale;
    const worldY = (centerY - this.camera.y) / oldScale;
    this.camera.scale.set(clamped, clamped);
    this.camera.x = centerX - worldX * clamped;
    this.camera.y = centerY - worldY * clamped;
  }

  private attachInteractions(): void {
    const stage = this.app.stage;
    // Stage interactions are shared with TopDownRenderer; only one renderer is
    // visible at a time, so the active one's handlers fire when it's shown.
    // We register on the canvas element directly to avoid double-registering
    // pointer events on the stage (TopDownRenderer already handles those).
    // Instead, iso pointer events are driven by the camera container.
    this.camera.eventMode = "static";
    this.camera.hitArea = {
      contains: () => true,
    } as unknown as { contains: (x: number, y: number) => boolean };

    stage.on("pointerdown", (e: FederatedPointerEvent) => {
      if (!this.camera.visible) return;
      this.dragging = true;
      this.lastPointer = { x: e.global.x, y: e.global.y };
      this.pointerDownPos = { x: e.global.x, y: e.global.y };
    });
    stage.on("pointerup", (e: FederatedPointerEvent) => {
      if (!this.camera.visible) return;
      if (this.pointerDownPos) {
        const dx = e.global.x - this.pointerDownPos.x;
        const dy = e.global.y - this.pointerDownPos.y;
        if (dx * dx + dy * dy < CLICK_THRESHOLD_SQ) {
          this.handleEntityClick(e.global.x, e.global.y);
        }
      }
      this.dragging = false;
      this.lastPointer = null;
      this.pointerDownPos = null;
    });
    stage.on("pointerupoutside", () => {
      if (!this.camera.visible) return;
      this.dragging = false;
      this.lastPointer = null;
      this.pointerDownPos = null;
    });
    stage.on("pointermove", (e: FederatedPointerEvent) => {
      if (!this.camera.visible || !this.dragging || this.lastPointer === null) return;
      const dx = e.global.x - this.lastPointer.x;
      const dy = e.global.y - this.lastPointer.y;
      this.camera.x += dx;
      this.camera.y += dy;
      this.lastPointer = { x: e.global.x, y: e.global.y };
    });

    const canvas = this.app.canvas;
    canvas.addEventListener("wheel", (ev: WheelEvent) => {
      if (!this.camera.visible) return;
      ev.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const cx = ev.clientX - rect.left;
      const cy = ev.clientY - rect.top;
      const factor = ev.deltaY < 0 ? 1.15 : 1 / 1.15;
      this.setZoom(this.camera.scale.x * factor, cx, cy);
    });
  }

  destroy(): void {
    this.camera.destroy({ children: true });
  }
}
