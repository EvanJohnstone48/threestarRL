import { useEffect, useRef, useState, useCallback } from "react";
import { Application } from "pixi.js";
import type { BuildingPlacement, BaseLayout, BaseLayoutMetadata } from "@/generated_types";
import { TH6_CAPS } from "./th6Caps";
import {
  createEditorState,
  enterPlaceMode,
  exitCurrentMode,
  enterPaintMode,
  enterEraseMode,
  placeBuildingAt,
  removeBuilding,
  eraseAtTile,
  getGhostLegality,
  startPaintDrag,
  commitWallPaint,
  resolveOrthoLine,
  type EditorState,
} from "./editorState";
import { validateLayout, type ConstraintResult } from "./validator";
import { EditorRenderer } from "./EditorRenderer";
import { categoryForBuilding } from "@/render/colors";

// --- Palette configuration ---

interface PaletteEntry {
  type: string;
  displayName: string;
}

interface PaletteGroup {
  label: string;
  entries: PaletteEntry[];
}

const PALETTE_GROUPS: PaletteGroup[] = [
  {
    label: "Town Hall + CC",
    entries: [
      { type: "town_hall", displayName: "Town Hall" },
      { type: "clan_castle", displayName: "Clan Castle" },
    ],
  },
  {
    label: "Defenses",
    entries: [
      { type: "cannon", displayName: "Cannon" },
      { type: "archer_tower", displayName: "Archer Tower" },
      { type: "mortar", displayName: "Mortar" },
      { type: "air_defense", displayName: "Air Defense" },
      { type: "wizard_tower", displayName: "Wizard Tower" },
    ],
  },
  {
    label: "Resources",
    entries: [
      { type: "gold_mine", displayName: "Gold Mine" },
      { type: "elixir_collector", displayName: "Elixir Collector" },
      { type: "gold_storage", displayName: "Gold Storage" },
      { type: "elixir_storage", displayName: "Elixir Storage" },
    ],
  },
  {
    label: "Army",
    entries: [
      { type: "army_camp", displayName: "Army Camp" },
      { type: "barracks", displayName: "Barracks" },
      { type: "laboratory", displayName: "Laboratory" },
      { type: "spell_factory", displayName: "Spell Factory" },
    ],
  },
  {
    label: "Builder's Hut",
    entries: [{ type: "builders_hut", displayName: "Builder's Hut" }],
  },
  {
    label: "Walls",
    entries: [{ type: "wall", displayName: "Wall" }],
  },
];

// --- Helper ---

function countPlaced(placements: BuildingPlacement[], type: string): number {
  return placements.filter((p) => p.building_type === type).length;
}

function buildingDisplayColor(type: string): string {
  // We can't use Pixi hex numbers in CSS directly — map category to CSS color
  const cat = categoryForBuilding(type);
  switch (cat) {
    case "town_hall":
      return "#f6c453";
    case "clan_castle":
      return "#a07cff";
    case "defense":
      return "#e57373";
    case "wall":
      return "#8d8470";
    case "resource_collector":
      return "#ffcc80";
    case "resource_storage":
      return "#ff9933";
    case "army":
      return "#c0c0c0";
    case "builder_hut":
      return "#b9d4ff";
  }
}

// --- Subcomponents ---

interface PaletteProps {
  placements: BuildingPlacement[];
  selectedType: string | null;
  mode: import("./editorState").EditorMode;
  onSelect: (type: string) => void;
}

function Palette({ placements, selectedType, mode, onSelect }: PaletteProps) {
  return (
    <div style={styles.panel}>
      <div style={styles.panelTitle}>Palette</div>
      {PALETTE_GROUPS.map((group) => (
        <div key={group.label} style={{ marginBottom: 12 }}>
          <div style={styles.groupLabel}>{group.label}</div>
          {group.entries.map(({ type, displayName }) => {
            const placed = countPlaced(placements, type);
            const cap = TH6_CAPS[type] ?? 0;
            const atCap = placed >= cap;
            const isSelected = mode === "placing" && selectedType === type;
            return (
              <button
                key={type}
                disabled={atCap}
                title={atCap ? `TH6 cap: ${placed} of ${cap} placed` : undefined}
                onClick={() => onSelect(type)}
                style={{
                  ...styles.paletteBtn,
                  opacity: atCap ? 0.4 : 1,
                  background: isSelected ? "#2a5298" : "#1e2a3a",
                  borderColor: isSelected ? "#4a90e2" : "#2a3a4a",
                  cursor: atCap ? "not-allowed" : "pointer",
                }}
              >
                <span
                  style={{
                    display: "inline-block",
                    width: 10,
                    height: 10,
                    borderRadius: 2,
                    background: buildingDisplayColor(type),
                    marginRight: 6,
                    flexShrink: 0,
                  }}
                />
                <span style={{ flex: 1, textAlign: "left" }}>{displayName}</span>
                <span style={styles.capCount}>
                  {placed}/{cap}
                </span>
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}

interface ValidationPanelProps {
  constraints: ConstraintResult[];
  placements: BuildingPlacement[];
  onHighlightIndices: (indices: number[]) => void;
  metadata: BaseLayoutMetadata;
  onMetadataChange: (meta: BaseLayoutMetadata) => void;
  onExport: () => void;
}

function ValidationPanel({
  constraints,
  placements,
  onHighlightIndices,
  metadata,
  onMetadataChange,
  onExport,
}: ValidationPanelProps) {
  const allPassing = constraints.every((c) => c.passing);
  const metaValid = metadata.name.trim().length > 0 && metadata.author.trim().length > 0;

  return (
    <div style={styles.panel}>
      <div style={styles.panelTitle}>Validation</div>
      {constraints.map((c) => (
        <div
          key={c.label}
          style={{
            ...styles.constraint,
            cursor: !c.passing && c.conflictingIndices.length > 0 ? "pointer" : "default",
          }}
          onClick={() => {
            if (!c.passing && c.conflictingIndices.length > 0) {
              onHighlightIndices(c.conflictingIndices);
            }
          }}
          title={!c.passing && c.conflictingIndices.length > 0 ? "Click to highlight conflicts" : undefined}
        >
          <span style={{ color: c.passing ? "#4caf50" : "#f44336", marginRight: 6 }}>
            {c.passing ? "✓" : "✗"}
          </span>
          {c.label}
        </div>
      ))}

      <div style={{ marginTop: 16, marginBottom: 8, ...styles.panelTitle }}>Metadata</div>
      <MetaField
        label="Name *"
        value={metadata.name}
        onChange={(v) => onMetadataChange({ ...metadata, name: v })}
      />
      <MetaField
        label="Author *"
        value={metadata.author}
        onChange={(v) => onMetadataChange({ ...metadata, author: v })}
      />
      <MetaField
        label="Notes"
        value={metadata.notes ?? ""}
        onChange={(v) => onMetadataChange({ ...metadata, notes: v || null })}
      />
      <div style={{ marginBottom: 6 }}>
        <div style={styles.fieldLabel}>Tags (comma-separated)</div>
        <input
          style={styles.input}
          value={metadata.tags.join(", ")}
          onChange={(e) => {
            const tags = e.target.value
              .split(",")
              .map((t) => t.trim())
              .filter(Boolean);
            onMetadataChange({ ...metadata, tags });
          }}
        />
      </div>
      <div style={{ marginBottom: 8, fontSize: 11, color: "#888" }}>
        Buildings: {placements.length}
      </div>
      <button
        disabled={!allPassing || !metaValid}
        title={
          !allPassing
            ? "Fix validation errors before exporting"
            : !metaValid
              ? "Name and Author are required"
              : "Export base.json"
        }
        onClick={onExport}
        style={{
          ...styles.exportBtn,
          opacity: allPassing && metaValid ? 1 : 0.4,
          cursor: allPassing && metaValid ? "pointer" : "not-allowed",
        }}
      >
        Export base.json
      </button>
    </div>
  );
}

function MetaField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={styles.fieldLabel}>{label}</div>
      <input style={styles.input} value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

// --- Main editor page ---

interface ContextMenu {
  x: number;
  y: number;
  buildingIndex: number | null;
  tile: [number, number] | null;
}

export function EditorPage() {
  const canvasRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<Application | null>(null);
  const rendererRef = useRef<EditorRenderer | null>(null);

  const [editorState, setEditorState] = useState<EditorState>(createEditorState);
  const [ghostOrigin, setGhostOrigin] = useState<[number, number] | null>(null);
  const [hoverTile, setHoverTile] = useState<[number, number] | null>(null);
  const [paintCurrentTile, setPaintCurrentTile] = useState<[number, number] | null>(null);
  const [wallCapTooltip, setWallCapTooltip] = useState(false);
  const [contextMenu, setContextMenu] = useState<ContextMenu | null>(null);
  const [constraints, setConstraints] = useState<ConstraintResult[]>(() =>
    validateLayout([]),
  );
  const [_highlightedIndices, setHighlightedIndices] = useState<number[]>([]);
  const [metadata, setMetadata] = useState<BaseLayoutMetadata>({
    name: "",
    th_level: 6,
    tags: [],
    notes: null,
    author: "",
    created_at: new Date().toISOString(),
  });

  // Keep a ref to editorState for callbacks inside Pixi
  const editorStateRef = useRef(editorState);
  editorStateRef.current = editorState;

  // Init Pixi once
  useEffect(() => {
    if (!canvasRef.current) return;
    const app = new Application();
    appRef.current = app;

    app
      .init({
        background: 0x141a22,
        resizeTo: canvasRef.current,
        antialias: true,
      })
      .then(() => {
        if (!canvasRef.current) return;
        canvasRef.current.appendChild(app.canvas);
        const renderer = new EditorRenderer(app);
        rendererRef.current = renderer;

        renderer.onTileHover = (row, col) => {
          const s = editorStateRef.current;
          setHoverTile([row, col]);
          if (s.mode === "placing") {
            setGhostOrigin([row, col]);
          } else {
            setGhostOrigin(null);
          }
          if (s.mode === "painting") {
            setPaintCurrentTile([row, col]);
          }
        };

        renderer.onTileClick = (row, col) => {
          const s = editorStateRef.current;
          if (s.mode === "placing") {
            setEditorState((prev) => {
              const [next, result] = placeBuildingAt(prev, [row, col]);
              if (result === "placed") {
                setConstraints(validateLayout(next.placements));
              }
              return next;
            });
          } else if (s.mode === "erasing") {
            setEditorState((prev) => {
              const next = eraseAtTile(prev, [row, col]);
              setConstraints(validateLayout(next.placements));
              return next;
            });
          }
        };

        renderer.onBuildingClick = (index) => {
          const s = editorStateRef.current;
          if (s.mode === "erasing" || s.mode === "idle") {
            setEditorState((prev) => {
              const next = removeBuilding(prev, index);
              setConstraints(validateLayout(next.placements));
              return next;
            });
          }
        };

        renderer.onBuildingRightClick = (index) => {
          setContextMenu({ x: 0, y: 0, buildingIndex: index, tile: null });
        };

        renderer.onTileRightClick = (row, col) => {
          setContextMenu({ x: 0, y: 0, buildingIndex: null, tile: [row, col] });
        };

        renderer.onPaintStart = (row, col) => {
          const s = editorStateRef.current;
          if (s.mode !== "painting") return;
          setEditorState((prev) => startPaintDrag(prev, [row, col]));
          setPaintCurrentTile([row, col]);
        };

        renderer.onPaintMove = (row, col) => {
          const s = editorStateRef.current;
          if (s.mode !== "painting") return;
          setPaintCurrentTile([row, col]);
        };

        renderer.onPaintEnd = (row, col) => {
          const s = editorStateRef.current;
          if (s.mode !== "painting" || s.paintStart === null) return;
          setEditorState((prev) => {
            const [next, result] = commitWallPaint(prev, [row, col]);
            setConstraints(validateLayout(next.placements));
            if (result === "capped") {
              setWallCapTooltip(true);
              setTimeout(() => setWallCapTooltip(false), 2500);
            }
            return next;
          });
          setPaintCurrentTile(null);
        };

        renderer.renderBuildings([]);
      });

    return () => {
      rendererRef.current?.destroy();
      rendererRef.current = null;
      app.destroy(true);
      appRef.current = null;
    };
  }, []);

  // Sync renderer when state changes
  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer) return;
    renderer.renderBuildings(editorState.placements);
  }, [editorState.placements]);

  // Sync ghost
  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer) return;
    if (ghostOrigin && editorState.mode === "placing" && editorState.selectedType) {
      const legality = getGhostLegality(editorState, ghostOrigin);
      renderer.renderGhost(editorState.selectedType, ghostOrigin, legality);
    } else {
      renderer.clearGhost();
    }
  }, [ghostOrigin, editorState]);

  // Sync wall-paint preview
  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer) return;
    if (editorState.mode === "painting" && editorState.paintStart && paintCurrentTile) {
      const tiles = resolveOrthoLine(editorState.paintStart, paintCurrentTile);
      renderer.renderWallPreview(tiles);
    } else {
      renderer.clearWallPreview();
    }
  }, [editorState, paintCurrentTile]);

  // Sync erase hover highlight
  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer) return;
    if (editorState.mode === "erasing" && hoverTile) {
      renderer.renderHoverHighlight(hoverTile);
    } else {
      renderer.renderHoverHighlight(null);
    }
  }, [editorState.mode, hoverTile]);

  // Keyboard shortcuts
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setEditorState((prev) => exitCurrentMode(prev));
        setGhostOrigin(null);
        setPaintCurrentTile(null);
        setContextMenu(null);
      } else if (e.key === "w" || e.key === "W") {
        setEditorState((prev) => enterPaintMode(prev));
        setGhostOrigin(null);
      } else if (e.key === "e" || e.key === "E") {
        setEditorState((prev) => enterEraseMode(prev));
        setGhostOrigin(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const handleSelect = useCallback((type: string) => {
    setEditorState((prev) => enterPlaceMode(prev, type));
    setGhostOrigin(null);
    setPaintCurrentTile(null);
  }, []);

  const handleContextAction = useCallback(
    (action: "erase" | "copy") => {
      if (!contextMenu) return;
      setContextMenu(null);
      if (action === "erase") {
        if (contextMenu.buildingIndex !== null) {
          setEditorState((prev) => {
            const next = removeBuilding(prev, contextMenu.buildingIndex!);
            setConstraints(validateLayout(next.placements));
            return next;
          });
        }
      } else if (action === "copy") {
        if (contextMenu.buildingIndex !== null) {
          setEditorState((prev) => {
            const type = prev.placements[contextMenu.buildingIndex!]?.building_type;
            if (!type) return prev;
            return enterPlaceMode(prev, type);
          });
        }
      }
    },
    [contextMenu],
  );

  const handleExport = useCallback(() => {
    const layout: BaseLayout = {
      schema_version: 1,
      metadata: {
        ...metadata,
        created_at: metadata.created_at || new Date().toISOString(),
      },
      th_level: 6,
      placements: editorState.placements,
      cc_contents: [],
    };
    const blob = new Blob([JSON.stringify(layout, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${metadata.name || "base"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [metadata, editorState.placements]);

  const modeLabel = (() => {
    switch (editorState.mode) {
      case "placing":
        return `Placing: ${editorState.selectedType} (Esc to cancel)`;
      case "painting":
        return "Paint walls: click+drag (W=toggle, Esc=exit)";
      case "erasing":
        return "Erase mode: click to remove (E=toggle, Esc=exit)";
      default:
        return "Click a palette item to place | W=paint walls | E=erase";
    }
  })();

  return (
    <div style={styles.root} onClick={() => setContextMenu(null)}>
      <Palette
        placements={editorState.placements}
        selectedType={editorState.selectedType}
        mode={editorState.mode}
        onSelect={handleSelect}
      />

      <div style={styles.centerCol}>
        <div style={styles.statusBar}>{modeLabel}</div>
        <div ref={canvasRef} style={styles.canvas} />
      </div>

      <ValidationPanel
        constraints={constraints}
        placements={editorState.placements}
        onHighlightIndices={setHighlightedIndices}
        metadata={metadata}
        onMetadataChange={setMetadata}
        onExport={handleExport}
      />

      {wallCapTooltip && (
        <div style={styles.wallCapTooltip}>TH6 wall cap: 75 of 75 placed.</div>
      )}

      {contextMenu && (
        <div
          style={{
            ...styles.contextMenu,
            // For now anchor to bottom-right of canvas area
            position: "fixed",
            top: "50%",
            left: "50%",
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <button style={styles.ctxBtn} onClick={() => handleContextAction("erase")}>
            Erase
          </button>
          {contextMenu.buildingIndex !== null && (
            <button style={styles.ctxBtn} onClick={() => handleContextAction("copy")}>
              Copy (place)
            </button>
          )}
          <button style={styles.ctxBtn} onClick={() => setContextMenu(null)}>
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}

// --- Styles ---

const styles = {
  root: {
    display: "flex",
    height: "100vh",
    background: "#0d1117",
    color: "#cdd9e5",
    fontFamily: "monospace",
    fontSize: 12,
    overflow: "hidden",
  } as React.CSSProperties,
  panel: {
    width: 200,
    minWidth: 200,
    background: "#161b22",
    borderRight: "1px solid #21262d",
    padding: "12px 8px",
    overflowY: "auto" as const,
    flexShrink: 0,
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
    outline: "none",
  } as React.CSSProperties,
  capCount: {
    color: "#6e7681",
    fontSize: 10,
    flexShrink: 0,
    marginLeft: 4,
  } as React.CSSProperties,
  centerCol: {
    flex: 1,
    display: "flex",
    flexDirection: "column" as const,
    overflow: "hidden",
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
    overflow: "hidden",
  } as React.CSSProperties,
  constraint: {
    padding: "3px 0",
    fontSize: 11,
    borderBottom: "1px solid #21262d",
    marginBottom: 2,
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
  exportBtn: {
    width: "100%",
    padding: "7px 0",
    background: "#238636",
    border: "1px solid #2ea043",
    borderRadius: 4,
    color: "#ffffff",
    fontSize: 12,
    fontFamily: "monospace",
    marginTop: 4,
  } as React.CSSProperties,
  wallCapTooltip: {
    position: "fixed" as const,
    bottom: 24,
    left: "50%",
    transform: "translateX(-50%)",
    background: "#f44336",
    color: "#fff",
    padding: "6px 14px",
    borderRadius: 4,
    fontSize: 12,
    fontFamily: "monospace",
    zIndex: 1000,
    pointerEvents: "none" as const,
  } as React.CSSProperties,
  contextMenu: {
    background: "#1e2a3a",
    border: "1px solid #2a3a4a",
    borderRadius: 4,
    padding: 4,
    zIndex: 1000,
    display: "flex",
    flexDirection: "column" as const,
    minWidth: 120,
  } as React.CSSProperties,
  ctxBtn: {
    display: "block",
    width: "100%",
    padding: "5px 10px",
    background: "transparent",
    border: "none",
    color: "#cdd9e5",
    fontSize: 12,
    fontFamily: "monospace",
    textAlign: "left" as const,
    cursor: "pointer",
  } as React.CSSProperties,
} as const;
