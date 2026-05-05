import { useEffect, useRef, useState, useCallback } from "react";
import { Application, Texture } from "pixi.js";
import { footprintFor } from "@/render/footprints";
import { BUILDING_TYPES, EFFECT_TYPES, TRAP_TYPES, TROOP_TYPES, loadAllSprites } from "@/render/spriteLoader";
import type { SpriteMap } from "@/render/spriteLoader";
import {
  DEFAULT_CALIBRATION,
  emptyCalibrations,
  getCalibration,
  loadCalibrations,
  saveCalibrationsLocal,
  serializeForDownload,
  setCalibration,
  type Calibration,
  type CalibrationKind,
  type SpriteCalibrations,
} from "./calibrations";
import { SpriteCalibratorScene, type CalibratorSelection } from "./SpriteCalibratorScene";

interface PaletteEntry {
  kind: CalibrationKind;
  name: string;
  display: string;
}

interface PaletteGroup {
  label: string;
  entries: PaletteEntry[];
}

const PALETTE: PaletteGroup[] = [
  {
    label: "Buildings",
    entries: BUILDING_TYPES.map((t) => ({ kind: "buildings" as const, name: t, display: t })),
  },
  {
    label: "Troops",
    entries: TROOP_TYPES.map((t) => ({ kind: "troops" as const, name: t, display: t })),
  },
  {
    label: "Traps",
    entries: TRAP_TYPES.map((t) => ({ kind: "traps" as const, name: t, display: t })),
  },
  {
    label: "Effects",
    entries: EFFECT_TYPES.map((t) => ({ kind: "effects" as const, name: t, display: t })),
  },
];

function spriteKeyFor(entry: PaletteEntry): string {
  switch (entry.kind) {
    case "buildings":
      return `building:${entry.name}`;
    case "troops":
      return `troop:${entry.name}`;
    case "traps":
      return `trap:${entry.name}`;
    case "effects":
      return `effect:${entry.name}`;
  }
}

function selectionFor(entry: PaletteEntry): CalibratorSelection {
  if (entry.kind === "buildings" || entry.kind === "traps") {
    const [fh] = footprintFor(entry.name);
    return { kind: entry.kind, name: entry.name, footprintSize: fh };
  }
  return { kind: entry.kind, name: entry.name, footprintSize: 3 };
}

export function SpriteCalibratorPage() {
  const canvasRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<Application | null>(null);
  const sceneRef = useRef<SpriteCalibratorScene | null>(null);
  const spritesRef = useRef<SpriteMap | null>(null);

  const [cals, setCals] = useState<SpriteCalibrations>(() => emptyCalibrations());
  const [selectedEntry, setSelectedEntry] = useState<PaletteEntry>(PALETTE[0]!.entries[0]!);
  const [savedToast, setSavedToast] = useState(false);
  const [spritesReady, setSpritesReady] = useState(false);

  const selectedCal = getCalibration(cals, selectedEntry.kind, selectedEntry.name);

  // Load calibrations once on mount.
  useEffect(() => {
    setCals(loadCalibrations());
  }, []);

  // Init Pixi + scene once.
  useEffect(() => {
    if (!canvasRef.current) return;
    const container = canvasRef.current;
    let cancelled = false;
    let cleanup: (() => void) | null = null;

    const app = new Application();
    app
      .init({ background: 0x0d1117, resizeTo: container, antialias: true })
      .then(async () => {
        if (cancelled) {
          app.destroy(true);
          return;
        }
        appRef.current = app;
        container.appendChild(app.canvas);
        const scene = new SpriteCalibratorScene(app);
        sceneRef.current = scene;

        const sprites = await loadAllSprites();
        spritesRef.current = sprites;
        setSpritesReady(true);

        scene.onCalibrationChange = (next) => {
          // Push from the scene (drag/wheel) into React state.
          setCals((prev) => {
            const updated = setCalibration(prev, selectedEntryRef.current.kind, selectedEntryRef.current.name, next);
            saveCalibrationsLocal(updated);
            return updated;
          });
        };

        cleanup = () => {
          sceneRef.current?.destroy();
          sceneRef.current = null;
          app.destroy(true);
          appRef.current = null;
        };
      });

    const onResize = (): void => {
      sceneRef.current?.resize();
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelled = true;
      window.removeEventListener("resize", onResize);
      if (cleanup) cleanup();
    };
  }, []);

  // Keep a ref to selectedEntry so the scene's pointer callback always sees the
  // current selection without re-binding.
  const selectedEntryRef = useRef(selectedEntry);
  selectedEntryRef.current = selectedEntry;

  // Push selection + calibration into the scene whenever they change.
  useEffect(() => {
    const scene = sceneRef.current;
    const sprites = spritesRef.current;
    if (!scene || !sprites) return;
    const tex: Texture | null = sprites.get(spriteKeyFor(selectedEntry)) ?? null;
    scene.setSelection(selectionFor(selectedEntry), selectedCal, tex);
  }, [selectedEntry, selectedCal, spritesReady]);

  const updateCal = useCallback(
    (patch: Partial<Calibration>) => {
      setCals((prev) => {
        const cur = getCalibration(prev, selectedEntry.kind, selectedEntry.name);
        const next: Calibration = { ...cur, ...patch };
        const updated = setCalibration(prev, selectedEntry.kind, selectedEntry.name, next);
        saveCalibrationsLocal(updated);
        sceneRef.current?.setCalibration(next);
        return updated;
      });
    },
    [selectedEntry],
  );

  const resetCurrent = useCallback(() => {
    updateCal(DEFAULT_CALIBRATION);
  }, [updateCal]);

  const handleDownload = useCallback(() => {
    const text = serializeForDownload(cals);
    const blob = new Blob([text], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sprite_calibrations.json";
    a.click();
    URL.revokeObjectURL(url);
    setSavedToast(true);
    setTimeout(() => setSavedToast(false), 2500);
  }, [cals]);

  const overriddenCount =
    Object.keys(cals.buildings).length +
    Object.keys(cals.troops).length +
    Object.keys(cals.effects).length +
    Object.keys(cals.traps).length;

  return (
    <div style={styles.root}>
      <div style={styles.palette}>
        <div style={styles.panelTitle}>Sprite</div>
        {PALETTE.map((group) => (
          <div key={group.label} style={{ marginBottom: 12 }}>
            <div style={styles.groupLabel}>{group.label}</div>
            {group.entries.map((entry) => {
              const isSel =
                entry.kind === selectedEntry.kind && entry.name === selectedEntry.name;
              const hasOverride = cals[entry.kind][entry.name] !== undefined;
              return (
                <button
                  key={`${entry.kind}:${entry.name}`}
                  onClick={() => setSelectedEntry(entry)}
                  style={{
                    ...styles.paletteBtn,
                    background: isSel ? "#2a5298" : "#1e2a3a",
                    borderColor: isSel ? "#4a90e2" : "#2a3a4a",
                  }}
                >
                  <span style={{ flex: 1, textAlign: "left" }}>{entry.display}</span>
                  {hasOverride && <span style={styles.dot} title="calibrated" />}
                </button>
              );
            })}
          </div>
        ))}
      </div>

      <div style={styles.centerCol}>
        <div style={styles.statusBar}>
          {selectedEntry.kind} / {selectedEntry.name} — drag the sprite to position; mouse wheel to scale
        </div>
        <div ref={canvasRef} style={styles.canvas} />
      </div>

      <div style={styles.controls}>
        <div style={styles.panelTitle}>Calibration</div>

        <NumberField
          label="offset_x (px)"
          value={selectedCal.offset_x}
          step={1}
          onChange={(v) => updateCal({ offset_x: v })}
        />
        <NumberField
          label="offset_y (px)"
          value={selectedCal.offset_y}
          step={1}
          onChange={(v) => updateCal({ offset_y: v })}
        />
        <NumberField
          label="scale"
          value={selectedCal.scale}
          step={0.01}
          min={0.05}
          onChange={(v) => updateCal({ scale: Math.max(0.05, v) })}
        />

        <button onClick={resetCurrent} style={{ ...styles.actionBtn, width: "100%", marginTop: 8 }}>
          Reset this sprite
        </button>

        <div style={{ ...styles.panelTitle, marginTop: 16 }}>Saving</div>
        <div style={styles.helpText}>
          Edits autosave to localStorage. Click below to download a merged
          sprite_calibrations.json — copy it into <code>app/data/</code> to commit.
        </div>
        <div style={styles.helpText}>
          Calibrated entities: <strong>{overriddenCount}</strong>
        </div>
        <button onClick={handleDownload} style={{ ...styles.exportBtn, width: "100%" }}>
          Download sprite_calibrations.json
        </button>

        <div style={{ ...styles.panelTitle, marginTop: 16 }}>Hints</div>
        <div style={styles.helpText}>
          • Buildings: align the sprite over the red hitbox rectangle. The yellow dot is the
          default anchor (south corner of the footprint).
        </div>
        <div style={styles.helpText}>
          • Troops & effects: scale and position the sprite relative to the 3×3 reference grid.
        </div>
        <div style={styles.helpText}>
          • Missing PNGs render as a magenta placeholder you can still drag to set a default.
        </div>
      </div>

      {savedToast && <div style={styles.toast}>Downloaded sprite_calibrations.json</div>}
    </div>
  );
}

function NumberField({
  label,
  value,
  step,
  min,
  onChange,
}: {
  label: string;
  value: number;
  step: number;
  min?: number;
  onChange: (v: number) => void;
}) {
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={styles.fieldLabel}>{label}</div>
      <input
        style={styles.input}
        type="number"
        step={step}
        {...(min !== undefined ? { min } : {})}
        value={Number.isFinite(value) ? value : 0}
        onChange={(e) => {
          const parsed = parseFloat(e.target.value);
          if (Number.isFinite(parsed)) onChange(parsed);
        }}
      />
    </div>
  );
}

const styles = {
  root: {
    display: "flex",
    height: "100%",
    background: "#0d1117",
    color: "#cdd9e5",
    fontFamily: "monospace",
    fontSize: 12,
    overflow: "hidden",
  } as React.CSSProperties,
  palette: {
    width: 200,
    minWidth: 200,
    background: "#161b22",
    borderRight: "1px solid #21262d",
    padding: "12px 8px",
    overflowY: "auto",
    flexShrink: 0,
  } as React.CSSProperties,
  controls: {
    width: 240,
    minWidth: 240,
    background: "#161b22",
    borderLeft: "1px solid #21262d",
    padding: "12px 10px",
    overflowY: "auto",
    flexShrink: 0,
  } as React.CSSProperties,
  centerCol: {
    flex: 1,
    display: "flex",
    flexDirection: "column" as const,
    minWidth: 0,
  } as React.CSSProperties,
  statusBar: {
    background: "#21262d",
    padding: "6px 12px",
    fontSize: 11,
    color: "#8b949e",
    borderBottom: "1px solid #30363d",
    flexShrink: 0,
  } as React.CSSProperties,
  canvas: {
    flex: 1,
    minHeight: 0,
    overflow: "hidden",
  } as React.CSSProperties,
  panelTitle: {
    fontSize: 11,
    fontWeight: "bold",
    color: "#8b949e",
    textTransform: "uppercase" as const,
    letterSpacing: 1,
    marginBottom: 8,
  } as React.CSSProperties,
  groupLabel: {
    fontSize: 10,
    color: "#6e7681",
    textTransform: "uppercase" as const,
    letterSpacing: 0.5,
    marginBottom: 4,
    marginTop: 4,
  } as React.CSSProperties,
  paletteBtn: {
    display: "flex",
    alignItems: "center",
    width: "100%",
    padding: "5px 6px",
    marginBottom: 2,
    border: "1px solid #2a3a4a",
    borderRadius: 4,
    color: "#cdd9e5",
    fontSize: 11,
    cursor: "pointer",
    outline: "none",
  } as React.CSSProperties,
  dot: {
    display: "inline-block",
    width: 6,
    height: 6,
    borderRadius: 6,
    background: "#f6c453",
    marginLeft: 6,
  } as React.CSSProperties,
  fieldLabel: {
    color: "#8b949e",
    fontSize: 10,
    marginBottom: 2,
  } as React.CSSProperties,
  input: {
    width: "100%",
    background: "#0d1117",
    border: "1px solid #30363d",
    borderRadius: 4,
    color: "#cdd9e5",
    fontSize: 11,
    padding: "3px 5px",
    boxSizing: "border-box" as const,
    outline: "none",
  } as React.CSSProperties,
  actionBtn: {
    padding: "5px 0",
    background: "#1e2a3a",
    border: "1px solid #2a3a4a",
    borderRadius: 4,
    color: "#cdd9e5",
    fontSize: 11,
    fontFamily: "monospace",
    cursor: "pointer",
  } as React.CSSProperties,
  exportBtn: {
    padding: "7px 0",
    background: "#238636",
    border: "1px solid #2ea043",
    borderRadius: 4,
    color: "#ffffff",
    fontSize: 12,
    fontFamily: "monospace",
    marginTop: 4,
    cursor: "pointer",
  } as React.CSSProperties,
  helpText: {
    fontSize: 11,
    color: "#8b949e",
    marginBottom: 6,
    lineHeight: 1.4,
  } as React.CSSProperties,
  toast: {
    position: "fixed" as const,
    bottom: 24,
    left: "50%",
    transform: "translateX(-50%)",
    background: "#238636",
    color: "#fff",
    padding: "6px 14px",
    borderRadius: 4,
    fontSize: 12,
    fontFamily: "monospace",
    zIndex: 1000,
    pointerEvents: "none" as const,
  } as React.CSSProperties,
} as const;
