// Top-down PixiJS renderer for the Phase 0 tracer view.
//
// Layout (PRD §8.1, §8.4):
//   - 50×50 grid as axis-aligned 32 px squares
//   - Inner buildable region is a slightly different shade than the deploy ring
//   - Buildings render as colored rectangles with a short text label
//   - Troops render as colored circles with a single-letter label
//   - HP bars overlay damaged entities (hidden at full HP)
//   - In-flight projectiles render as small yellow dots with a faint splash ring

import { Application, Container, Graphics, Text, TextStyle, FederatedPointerEvent } from "pixi.js";

import type { TickFrame } from "@/generated_types";
import {
  COLOR_BUILDABLE,
  COLOR_DEPLOY_RING,
  COLOR_GRID_BG,
  COLOR_GRID_LINE,
  COLOR_HP_FULL,
  COLOR_PROJECTILE,
  buildingColor,
  buildingLabel,
  categoryForBuilding,
  hpBarColor,
  troopColor,
  troopLabel,
} from "./colors";
import { footprintFor, TROOP_VISUAL_RADIUS_TILES } from "./footprints";
import {
  BUILDABLE_MAX_EXCLUSIVE,
  BUILDABLE_MIN,
  GRID_SIZE,
  TILE_SIZE,
  gridToScreen,
} from "./projection";
import type { InterpolatedFrame } from "@/replay/interpolation";

const HP_BAR_BUILDING_W = 24;
const HP_BAR_BUILDING_H = 4;
const HP_BAR_TROOP_W = 16;
const HP_BAR_TROOP_H = 3;

const ZOOM_MIN = 0.25;
const ZOOM_MAX = 4;

// Click threshold in screen pixels — below this distance a pointerup is a click.
const CLICK_THRESHOLD_SQ = 25; // 5px

const labelStyleSmall = new TextStyle({
  fontFamily: "monospace",
  fontSize: 10,
  fill: 0xffffff,
});
const labelStyleTiny = new TextStyle({
  fontFamily: "monospace",
  fontSize: 9,
  fill: 0x111111,
});

type EntityHitArea =
  | { kind: "building"; id: number; x: number; y: number; w: number; h: number }
  | { kind: "troop"; id: number; cx: number; cy: number; r: number };

export class TopDownRenderer {
  private app: Application;
  private camera: Container;
  private gridLayer: Container;
  private buildingLayer: Container;
  private troopLayer: Container;
  private projectileLayer: Container;
  private hpBarLayer: Container;
  private dragging = false;
  private lastPointer: { x: number; y: number } | null = null;
  private pointerDownPos: { x: number; y: number } | null = null;
  private entityHitAreas: EntityHitArea[] = [];

  // Set these to receive entity-click and background-click callbacks.
  onEntityClick: ((kind: "building" | "troop", id: number) => void) | null = null;
  onBackgroundClick: (() => void) | null = null;

  constructor(app: Application) {
    this.app = app;
    this.camera = new Container();
    this.gridLayer = new Container();
    this.buildingLayer = new Container();
    this.troopLayer = new Container();
    this.projectileLayer = new Container();
    this.hpBarLayer = new Container();
    this.camera.addChild(this.gridLayer);
    this.camera.addChild(this.buildingLayer);
    this.camera.addChild(this.projectileLayer);
    this.camera.addChild(this.troopLayer);
    this.camera.addChild(this.hpBarLayer);
    this.app.stage.addChild(this.camera);

    this.drawGrid();
    this.attachInteractions();
    this.fitToGrid();
  }

  private drawGrid(): void {
    // Solid background
    const bg = new Graphics();
    bg.rect(0, 0, GRID_SIZE * TILE_SIZE, GRID_SIZE * TILE_SIZE).fill(COLOR_GRID_BG);
    this.gridLayer.addChild(bg);

    // Inner buildable region — slightly lighter shade
    const inner = new Graphics();
    const inset = BUILDABLE_MIN * TILE_SIZE;
    const innerSize = (BUILDABLE_MAX_EXCLUSIVE - BUILDABLE_MIN) * TILE_SIZE;
    inner.rect(inset, inset, innerSize, innerSize).fill(COLOR_BUILDABLE);
    this.gridLayer.addChild(inner);

    // Deploy ring outline (a 3-tile-wide frame)
    const ring = new Graphics();
    ring
      .rect(0, 0, GRID_SIZE * TILE_SIZE, GRID_SIZE * TILE_SIZE)
      .stroke({ color: COLOR_DEPLOY_RING, width: 2 });
    this.gridLayer.addChild(ring);

    // Tile gridlines (every tile)
    const lines = new Graphics();
    for (let i = 0; i <= GRID_SIZE; i++) {
      const v = i * TILE_SIZE;
      lines.moveTo(v, 0).lineTo(v, GRID_SIZE * TILE_SIZE);
      lines.moveTo(0, v).lineTo(GRID_SIZE * TILE_SIZE, v);
    }
    lines.stroke({ color: COLOR_GRID_LINE, width: 1, alpha: 0.5 });
    this.gridLayer.addChild(lines);

    // Inner-region boundary, drawn once and prominent
    const innerOutline = new Graphics();
    innerOutline
      .rect(inset, inset, innerSize, innerSize)
      .stroke({ color: 0x4a5568, width: 1.5, alpha: 0.8 });
    this.gridLayer.addChild(innerOutline);
  }

  // Render one interpolated frame. Buildings rebuilt on every call (cheap
  // for ~100 buildings at TH6); troops + projectiles likewise.
  renderFrame(frame: InterpolatedFrame, currentTickFrame: TickFrame): void {
    this.buildingLayer.removeChildren();
    this.troopLayer.removeChildren();
    this.projectileLayer.removeChildren();
    this.hpBarLayer.removeChildren();
    this.entityHitAreas = [];

    for (const b of currentTickFrame.state.buildings) {
      if (b.destroyed) continue;
      const [h, w] = footprintFor(b.building_type);
      const { x, y } = gridToScreen(b.origin[0], b.origin[1]);
      const rect = new Graphics();
      const cat = categoryForBuilding(b.building_type);
      rect.rect(x, y, w * TILE_SIZE, h * TILE_SIZE).fill(buildingColor(cat));
      rect
        .rect(x, y, w * TILE_SIZE, h * TILE_SIZE)
        .stroke({ color: 0x000000, width: 1, alpha: 0.4 });
      this.buildingLayer.addChild(rect);

      const label = buildingLabel(b.building_type, b.level);
      if (label) {
        const text = new Text({ text: label, style: labelStyleTiny });
        text.x = x + (w * TILE_SIZE) / 2 - text.width / 2;
        text.y = y + (h * TILE_SIZE) / 2 - text.height / 2;
        this.buildingLayer.addChild(text);
      }

      if (b.hp < b.max_hp) {
        this.drawHpBar(
          x + (w * TILE_SIZE - HP_BAR_BUILDING_W) / 2,
          y - HP_BAR_BUILDING_H - 2,
          HP_BAR_BUILDING_W,
          HP_BAR_BUILDING_H,
          b.hp,
          b.max_hp,
        );
      }

      this.entityHitAreas.push({ kind: "building", id: b.id, x, y, w: w * TILE_SIZE, h: h * TILE_SIZE });
    }

    for (const p of frame.projectiles) {
      const { x, y } = gridToScreen(p.current_position[0], p.current_position[1]);
      const dot = new Graphics();
      dot.circle(x, y, 3).fill(COLOR_PROJECTILE);
      this.projectileLayer.addChild(dot);
    }

    for (const t of frame.troops) {
      if (t.destroyed) continue;
      const { x, y } = gridToScreen(t.position[0], t.position[1]);
      const radius = TROOP_VISUAL_RADIUS_TILES * TILE_SIZE;
      const circle = new Graphics();
      circle.circle(x, y, radius).fill(troopColor("ground"));
      circle.circle(x, y, radius).stroke({ color: 0x000000, width: 1, alpha: 0.6 });
      this.troopLayer.addChild(circle);

      const text = new Text({ text: troopLabel(t.troop_type), style: labelStyleSmall });
      text.x = x - text.width / 2;
      text.y = y - text.height / 2;
      this.troopLayer.addChild(text);

      if (t.hp < t.max_hp) {
        this.drawHpBar(
          x - HP_BAR_TROOP_W / 2,
          y - radius - HP_BAR_TROOP_H - 2,
          HP_BAR_TROOP_W,
          HP_BAR_TROOP_H,
          t.hp,
          t.max_hp,
        );
      }

      this.entityHitAreas.push({ kind: "troop", id: t.id, cx: x, cy: y, r: radius });
    }
  }

  private drawHpBar(x: number, y: number, w: number, h: number, hp: number, maxHp: number): void {
    const bg = new Graphics();
    bg.rect(x, y, w, h).fill(0x0a0a0a);
    this.hpBarLayer.addChild(bg);
    const ratio = Math.max(0, Math.min(1, hp / Math.max(1, maxHp)));
    const fg = new Graphics();
    fg.rect(x, y, w * ratio, h).fill(hpBarColor(hp, maxHp));
    this.hpBarLayer.addChild(fg);
    if (ratio === 1) {
      // Defensive — caller should have skipped at full HP, but if we draw,
      // make it green.
      fg.tint = COLOR_HP_FULL;
    }
  }

  private handleEntityClick(screenX: number, screenY: number): void {
    const worldX = (screenX - this.camera.x) / this.camera.scale.x;
    const worldY = (screenY - this.camera.y) / this.camera.scale.y;

    // Troops first — rendered on top of buildings
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
        if (worldX >= hit.x && worldX < hit.x + hit.w && worldY >= hit.y && worldY < hit.y + hit.h) {
          this.onEntityClick?.("building", hit.id);
          return;
        }
      }
    }
    this.onBackgroundClick?.();
  }

  // Camera controls

  fitToGrid(): void {
    const screen = this.app.screen;
    const gridPx = GRID_SIZE * TILE_SIZE;
    const scale = Math.min(screen.width / gridPx, screen.height / gridPx) * 0.95;
    this.camera.scale.set(scale, scale);
    this.camera.x = (screen.width - gridPx * scale) / 2;
    this.camera.y = (screen.height - gridPx * scale) / 2;
  }

  setZoom(newScale: number, centerX: number, centerY: number): void {
    const clamped = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, newScale));
    const oldScale = this.camera.scale.x;
    if (clamped === oldScale) return;
    // Zoom around (centerX, centerY) in screen space.
    const worldX = (centerX - this.camera.x) / oldScale;
    const worldY = (centerY - this.camera.y) / oldScale;
    this.camera.scale.set(clamped, clamped);
    this.camera.x = centerX - worldX * clamped;
    this.camera.y = centerY - worldY * clamped;
  }

  private attachInteractions(): void {
    const stage = this.app.stage;
    stage.eventMode = "static";
    stage.hitArea = this.app.screen;

    stage.on("pointerdown", (e: FederatedPointerEvent) => {
      this.dragging = true;
      this.lastPointer = { x: e.global.x, y: e.global.y };
      this.pointerDownPos = { x: e.global.x, y: e.global.y };
    });
    stage.on("pointerup", (e: FederatedPointerEvent) => {
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
      this.dragging = false;
      this.lastPointer = null;
      this.pointerDownPos = null;
    });
    stage.on("pointermove", (e: FederatedPointerEvent) => {
      if (!this.dragging || this.lastPointer === null) return;
      const dx = e.global.x - this.lastPointer.x;
      const dy = e.global.y - this.lastPointer.y;
      this.camera.x += dx;
      this.camera.y += dy;
      this.lastPointer = { x: e.global.x, y: e.global.y };
    });

    // Wheel zoom. Pixi v8 doesn't surface wheel through federated events; we
    // hook it on the canvas directly.
    const canvas = this.app.canvas;
    canvas.addEventListener("wheel", (ev: WheelEvent) => {
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
