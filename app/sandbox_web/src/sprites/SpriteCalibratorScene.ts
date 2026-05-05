// PixiJS scene for the Sprite Calibrator page.
// Renders an iso reference grid (footprint for buildings, 3×3 for troops/effects),
// a square hitbox overlay for buildings, and the sprite under calibration. The
// sprite is draggable to adjust offset; mouse wheel adjusts scale.

import {
  Application,
  Container,
  Graphics,
  Sprite,
  Text,
  TextStyle,
  Texture,
  FederatedPointerEvent,
} from "pixi.js";

import { gridToIsoScreen, ISO_TILE_W } from "@/render/isoProjection";
import { hitboxRect } from "./hitbox";
import type { Calibration, CalibrationKind } from "./calibrations";

const TROOP_REF_GRID = 3;

const COLOR_BG = 0x0d1117;
const COLOR_GRID = 0x4a90e2;
const COLOR_FOOTPRINT_FILL = 0x1f2937;
const COLOR_HITBOX = 0xff5252;
const COLOR_PLACEHOLDER = 0xff00ff;
const COLOR_ANCHOR = 0xf6c453;

const labelStyle = new TextStyle({
  fontFamily: "monospace",
  fontSize: 12,
  fill: 0xcdd9e5,
});

export interface CalibratorSelection {
  kind: CalibrationKind;
  name: string;
  /** For buildings only — square footprint side length in tiles. */
  footprintSize: number;
}

export class SpriteCalibratorScene {
  private app: Application;
  private camera: Container;
  private gridLayer: Container;
  private spriteLayer: Container;
  private currentSprite: Sprite | Graphics | null = null;
  private currentTexture: Texture | null = null;

  private dragging = false;
  private dragStart: { x: number; y: number } | null = null;
  private dragStartOffset: { x: number; y: number } | null = null;

  onCalibrationChange: ((cal: Calibration) => void) | null = null;

  private selection: CalibratorSelection | null = null;
  private calibration: Calibration = { offset_x: 0, offset_y: 0, scale: 1 };

  constructor(app: Application) {
    this.app = app;
    this.app.renderer.background.color = COLOR_BG;

    this.camera = new Container();
    this.gridLayer = new Container();
    this.spriteLayer = new Container();
    this.camera.addChild(this.gridLayer);
    this.camera.addChild(this.spriteLayer);
    this.app.stage.addChild(this.camera);

    this.app.stage.eventMode = "static";
    this.app.stage.hitArea = this.app.screen;

    this.attachInteractions();
    this.recenter();
  }

  private recenter(): void {
    this.camera.x = this.app.screen.width / 2;
    this.camera.y = this.app.screen.height / 2;
  }

  resize(): void {
    this.app.stage.hitArea = this.app.screen;
    this.recenter();
  }

  setSelection(
    selection: CalibratorSelection,
    calibration: Calibration,
    texture: Texture | null,
  ): void {
    this.selection = selection;
    this.calibration = calibration;
    this.currentTexture = texture;
    this.redraw();
  }

  setCalibration(calibration: Calibration): void {
    this.calibration = calibration;
    this.redraw();
  }

  private redraw(): void {
    this.gridLayer.removeChildren();
    this.spriteLayer.removeChildren();
    this.currentSprite = null;
    if (!this.selection) return;

    if (this.selection.kind === "buildings" || this.selection.kind === "traps") {
      this.drawBuildingGrid(this.selection.name, this.selection.footprintSize);
    } else {
      this.drawTroopGrid();
    }

    this.drawSprite();
  }

  // The footprint diamond + per-tile gridlines + square hitbox overlay.
  private drawBuildingGrid(buildingType: string, n: number): void {
    // Translate so footprint center is at world (0, 0).
    // Center of N×N at origin (0,0) in iso: (0, N*16).
    const centerY = n * 16;
    this.gridLayer.x = 0;
    this.gridLayer.y = -centerY;

    // Footprint diamond fill.
    const fill = new Graphics();
    const N = gridToIsoScreen(0, 0);
    const E = gridToIsoScreen(0, n);
    const S = gridToIsoScreen(n, n);
    const W = gridToIsoScreen(n, 0);
    fill.poly([N.x, N.y, E.x, E.y, S.x, S.y, W.x, W.y]).fill(COLOR_FOOTPRINT_FILL);
    fill.poly([N.x, N.y, E.x, E.y, S.x, S.y, W.x, W.y]).stroke({
      color: COLOR_GRID,
      width: 2,
      alpha: 0.9,
    });
    this.gridLayer.addChild(fill);

    // Per-tile gridlines.
    const lines = new Graphics();
    for (let r = 0; r <= n; r++) {
      const a = gridToIsoScreen(r, 0);
      const b = gridToIsoScreen(r, n);
      lines.moveTo(a.x, a.y).lineTo(b.x, b.y);
    }
    for (let c = 0; c <= n; c++) {
      const a = gridToIsoScreen(0, c);
      const b = gridToIsoScreen(n, c);
      lines.moveTo(a.x, a.y).lineTo(b.x, b.y);
    }
    lines.stroke({ color: COLOR_GRID, width: 1, alpha: 0.4 });
    this.gridLayer.addChild(lines);

    // Square hitbox overlay (in tile coords, then projected). Per PRD §5.4 the
    // hitbox is square in tile space — its 4 corners project to a diamond on iso.
    const hb = hitboxRect(buildingType, [0, 0], [n, n]);
    if (hb.rowMax > hb.rowMin && hb.colMax > hb.colMin) {
      const hN = gridToIsoScreen(hb.rowMin, hb.colMin);
      const hE = gridToIsoScreen(hb.rowMin, hb.colMax);
      const hS = gridToIsoScreen(hb.rowMax, hb.colMax);
      const hW = gridToIsoScreen(hb.rowMax, hb.colMin);
      const hbg = new Graphics();
      hbg.poly([hN.x, hN.y, hE.x, hE.y, hS.x, hS.y, hW.x, hW.y]).fill({
        color: COLOR_HITBOX,
        alpha: 0.18,
      });
      hbg.poly([hN.x, hN.y, hE.x, hE.y, hS.x, hS.y, hW.x, hW.y]).stroke({
        color: COLOR_HITBOX,
        width: 2,
        alpha: 0.85,
      });
      this.gridLayer.addChild(hbg);
    }

    // Anchor dot — south corner of the footprint diamond (where sprite's
    // bottom-center pins by default).
    const anchorDot = new Graphics();
    anchorDot.circle(S.x, S.y, 3).fill(COLOR_ANCHOR);
    this.gridLayer.addChild(anchorDot);

    // Caption.
    const caption = new Text({
      text: `${buildingType}  footprint ${n}×${n}  hitbox ${(hb.rowMax - hb.rowMin).toFixed(2)}×${(hb.colMax - hb.colMin).toFixed(2)}`,
      style: labelStyle,
    });
    caption.x = -caption.width / 2;
    caption.y = N.y - 24;
    this.gridLayer.addChild(caption);
  }

  // 3×3 reference grid, centered on world origin, with anchor at the grid's
  // center tile center.
  private drawTroopGrid(): void {
    const n = TROOP_REF_GRID;
    const centerY = n * 16;
    this.gridLayer.x = 0;
    this.gridLayer.y = -centerY;

    const fill = new Graphics();
    const N = gridToIsoScreen(0, 0);
    const E = gridToIsoScreen(0, n);
    const S = gridToIsoScreen(n, n);
    const W = gridToIsoScreen(n, 0);
    fill.poly([N.x, N.y, E.x, E.y, S.x, S.y, W.x, W.y]).fill(COLOR_FOOTPRINT_FILL);
    fill.poly([N.x, N.y, E.x, E.y, S.x, S.y, W.x, W.y]).stroke({
      color: COLOR_GRID,
      width: 2,
      alpha: 0.9,
    });
    this.gridLayer.addChild(fill);

    const lines = new Graphics();
    for (let r = 0; r <= n; r++) {
      const a = gridToIsoScreen(r, 0);
      const b = gridToIsoScreen(r, n);
      lines.moveTo(a.x, a.y).lineTo(b.x, b.y);
    }
    for (let c = 0; c <= n; c++) {
      const a = gridToIsoScreen(0, c);
      const b = gridToIsoScreen(n, c);
      lines.moveTo(a.x, a.y).lineTo(b.x, b.y);
    }
    lines.stroke({ color: COLOR_GRID, width: 1, alpha: 0.4 });
    this.gridLayer.addChild(lines);

    // Anchor dot at the grid's center (where the entity stands).
    const center = gridToIsoScreen(n / 2, n / 2);
    const anchorDot = new Graphics();
    anchorDot.circle(center.x, center.y, 3).fill(COLOR_ANCHOR);
    this.gridLayer.addChild(anchorDot);

    const sel = this.selection;
    if (sel) {
      const caption = new Text({
        text: `${sel.kind}: ${sel.name}  reference grid 3×3`,
        style: labelStyle,
      });
      caption.x = -caption.width / 2;
      caption.y = N.y - 24;
      this.gridLayer.addChild(caption);
    }
  }

  private drawSprite(): void {
    if (!this.selection) return;
    this.spriteLayer.x = this.gridLayer.x;
    this.spriteLayer.y = this.gridLayer.y;

    // Anchor point in iso world coords (relative to gridLayer origin).
    let anchorX: number;
    let anchorY: number;
    let anchorMode: { ax: number; ay: number };

    if (this.selection.kind === "buildings" || this.selection.kind === "traps") {
      const n = this.selection.footprintSize;
      const S = gridToIsoScreen(n, n);
      anchorX = S.x;
      anchorY = S.y;
      anchorMode = { ax: 0.5, ay: 1.0 };
    } else {
      const n = TROOP_REF_GRID;
      const center = gridToIsoScreen(n / 2, n / 2);
      anchorX = center.x;
      anchorY = center.y;
      anchorMode = { ax: 0.5, ay: 0.5 };
    }

    const node: Sprite | Graphics =
      this.currentTexture !== null
        ? this.makeSprite(this.currentTexture, anchorMode.ax, anchorMode.ay)
        : this.makePlaceholder(anchorMode.ax, anchorMode.ay);

    node.x = anchorX + this.calibration.offset_x;
    node.y = anchorY + this.calibration.offset_y;
    if (node instanceof Sprite) {
      node.scale.set(this.calibration.scale, this.calibration.scale);
    } else {
      node.scale.set(this.calibration.scale, this.calibration.scale);
    }
    node.eventMode = "static";
    node.cursor = "grab";
    this.spriteLayer.addChild(node);
    this.currentSprite = node;

    this.attachSpriteDrag(node);
  }

  private makeSprite(tex: Texture, ax: number, ay: number): Sprite {
    const spr = new Sprite(tex);
    spr.anchor.set(ax, ay);
    return spr;
  }

  private makePlaceholder(ax: number, ay: number): Graphics {
    // Default placeholder size: a 3×3 tile-area square (fits the iso reference
    // grid roughly). This makes it draggable + visible even with no PNG.
    const w = ISO_TILE_W * 1.5; // 96
    const h = ISO_TILE_W * 1.0; // 64
    const g = new Graphics();
    g.rect(-w * ax, -h * ay, w, h).fill({ color: COLOR_PLACEHOLDER, alpha: 0.5 });
    g.rect(-w * ax, -h * ay, w, h).stroke({ color: COLOR_PLACEHOLDER, width: 2 });
    return g;
  }

  private attachSpriteDrag(node: Sprite | Graphics): void {
    node.on("pointerdown", (e: FederatedPointerEvent) => {
      this.dragging = true;
      this.dragStart = { x: e.global.x, y: e.global.y };
      this.dragStartOffset = {
        x: this.calibration.offset_x,
        y: this.calibration.offset_y,
      };
      node.cursor = "grabbing";
      e.stopPropagation();
    });
  }

  private attachInteractions(): void {
    const stage = this.app.stage;
    stage.on("pointermove", (e: FederatedPointerEvent) => {
      if (!this.dragging || !this.dragStart || !this.dragStartOffset) return;
      const dx = e.global.x - this.dragStart.x;
      const dy = e.global.y - this.dragStart.y;
      const next: Calibration = {
        offset_x: this.dragStartOffset.x + dx,
        offset_y: this.dragStartOffset.y + dy,
        scale: this.calibration.scale,
      };
      this.calibration = next;
      this.redraw();
      this.onCalibrationChange?.(next);
    });
    const endDrag = (): void => {
      this.dragging = false;
      this.dragStart = null;
      this.dragStartOffset = null;
      if (this.currentSprite) this.currentSprite.cursor = "grab";
    };
    stage.on("pointerup", endDrag);
    stage.on("pointerupoutside", endDrag);

    const canvas = this.app.canvas;
    canvas.addEventListener("wheel", (ev: WheelEvent) => {
      ev.preventDefault();
      const factor = ev.deltaY < 0 ? 1.05 : 1 / 1.05;
      const nextScale = Math.max(0.05, Math.min(10, this.calibration.scale * factor));
      const next: Calibration = {
        offset_x: this.calibration.offset_x,
        offset_y: this.calibration.offset_y,
        scale: nextScale,
      };
      this.calibration = next;
      this.redraw();
      this.onCalibrationChange?.(next);
    });
  }

  destroy(): void {
    this.camera.destroy({ children: true });
  }
}
