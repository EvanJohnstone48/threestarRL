import { useEffect, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Types matching the server API
// ---------------------------------------------------------------------------

interface DetectionInfo {
  class_name: string;
  bbox_xyxy: [number, number, number, number];
  confidence: number;
}

interface ScreenshotEntry {
  filename: string;
  image_url: string;
  detections: DetectionInfo[];
}

interface BuildingsMap {
  [class_name: string]: [number, number];
}

interface CalibConfig {
  dataset_version: string;
  [k: string]: unknown;
}

interface PlacedRecord {
  filename: string;
  class_name: string;
  bbox_xyxy: [number, number, number, number];
  placed_anchor_xy: [number, number];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function bboxBottomCenter(bbox: [number, number, number, number]): [number, number] {
  return [(bbox[0] + bbox[2]) / 2, bbox[3]];
}

// ---------------------------------------------------------------------------
// Draggable footprint overlay drawn on a canvas on top of the screenshot img
// ---------------------------------------------------------------------------

interface FootprintState {
  detIdx: number;
  anchorX: number;
  anchorY: number;
}

interface CalibrateViewProps {
  entry: ScreenshotEntry;
  buildings: BuildingsMap;
  onSaved: (records: PlacedRecord[]) => void;
}

function CalibrateView({ entry, buildings, onSaved }: CalibrateViewProps) {
  const imgRef = useRef<HTMLImageElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Footprint anchors: keyed by detection index, in *image* pixel coords
  const [footprints, setFootprints] = useState<FootprintState[]>(() =>
    entry.detections.map((det, i) => {
      const [ax, ay] = bboxBottomCenter(det.bbox_xyxy);
      return { detIdx: i, anchorX: ax, anchorY: ay };
    }),
  );

  const dragging = useRef<{ fpIdx: number; offsetX: number; offsetY: number } | null>(null);

  // Scale factor: image natural coords → canvas display coords
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const img = imgRef.current;
    if (!img) return;
    const updateScale = () => {
      if (img.naturalWidth) setScale(img.clientWidth / img.naturalWidth);
    };
    img.addEventListener("load", updateScale);
    updateScale();
    return () => img.removeEventListener("load", updateScale);
  }, [entry.image_url]);

  // Redraw canvas on every footprint change
  useEffect(() => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img || !img.naturalWidth) return;

    const w = img.clientWidth;
    const h = img.clientHeight;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d")!;
    ctx.clearRect(0, 0, w, h);
    const s = scale;

    // Draw bounding boxes
    ctx.strokeStyle = "rgba(255,200,0,0.9)";
    ctx.lineWidth = 2;
    for (const det of entry.detections) {
      const [x1, y1, x2, y2] = det.bbox_xyxy;
      ctx.strokeRect(x1 * s, y1 * s, (x2 - x1) * s, (y2 - y1) * s);
      ctx.fillStyle = "rgba(255,200,0,0.9)";
      ctx.font = `${Math.max(10, 11 * s)}px monospace`;
      ctx.fillText(det.class_name, x1 * s + 2, y1 * s - 3);
    }

    // Draw footprint highlights
    for (const fp of footprints) {
      const det = entry.detections[fp.detIdx];
      const fp_size = buildings[det.class_name] ?? [1, 1];
      // We treat placed_anchor_xy as the bottom-center of the footprint in image coords.
      // Footprint tile size in screen pixels is unknown here, so just draw a coloured dot + cross.
      const cx = fp.anchorX * s;
      const cy = fp.anchorY * s;
      const r = Math.max(8, 16 * s);
      ctx.strokeStyle = "rgba(0,200,255,0.95)";
      ctx.lineWidth = 2;
      ctx.strokeRect(cx - r, cy - r * (fp_size[1] / fp_size[0]), r * 2, r * 2 * (fp_size[1] / fp_size[0]));
      ctx.beginPath();
      ctx.arc(cx, cy, 4, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(0,200,255,0.95)";
      ctx.fill();
    }
  }, [footprints, scale, entry, buildings]);

  function canvasCoordToImage(ex: number, ey: number): [number, number] {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    return [(ex - rect.left) / scale, (ey - rect.top) / scale];
  }

  function onMouseDown(e: React.MouseEvent) {
    const [ix, iy] = canvasCoordToImage(e.clientX, e.clientY);
    // Find the nearest footprint anchor within 30px
    let best: number | null = null;
    let bestDist = 30;
    for (let i = 0; i < footprints.length; i++) {
      const fp = footprints[i];
      const d = Math.hypot(fp.anchorX - ix, fp.anchorY - iy);
      if (d < bestDist) {
        bestDist = d;
        best = i;
      }
    }
    if (best !== null) {
      dragging.current = {
        fpIdx: best,
        offsetX: footprints[best].anchorX - ix,
        offsetY: footprints[best].anchorY - iy,
      };
    }
  }

  function onMouseMove(e: React.MouseEvent) {
    if (!dragging.current) return;
    const [ix, iy] = canvasCoordToImage(e.clientX, e.clientY);
    const { fpIdx, offsetX, offsetY } = dragging.current;
    setFootprints((prev) =>
      prev.map((fp, i) =>
        i === fpIdx ? { ...fp, anchorX: ix + offsetX, anchorY: iy + offsetY } : fp,
      ),
    );
  }

  function onMouseUp() {
    dragging.current = null;
  }

  function handleSave() {
    const records: PlacedRecord[] = footprints.map((fp) => {
      const det = entry.detections[fp.detIdx];
      return {
        filename: entry.filename,
        class_name: det.class_name,
        bbox_xyxy: det.bbox_xyxy,
        placed_anchor_xy: [fp.anchorX, fp.anchorY],
      };
    });
    onSaved(records);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, height: "100%" }}>
      <div
        style={{ position: "relative", flex: 1, overflow: "hidden", cursor: "crosshair" }}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
      >
        <img
          ref={imgRef}
          src={entry.image_url}
          alt={entry.filename}
          style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
        />
        <canvas
          ref={canvasRef}
          style={{ position: "absolute", top: 0, left: 0, pointerEvents: "none" }}
        />
      </div>
      <div style={{ display: "flex", gap: 8, padding: "8px 0", flexShrink: 0 }}>
        <button
          onClick={handleSave}
          style={{
            padding: "6px 18px",
            background: "#238636",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            fontFamily: "monospace",
            fontSize: 13,
            cursor: "pointer",
          }}
        >
          Save &amp; exit
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Calibrate mode root
// ---------------------------------------------------------------------------

function CalibrateMode() {
  const [screenshots, setScreenshots] = useState<ScreenshotEntry[] | null>(null);
  const [buildings, setBuildings] = useState<BuildingsMap | null>(null);
  const [config, setConfig] = useState<CalibConfig | null>(null);
  const [activeIdx, setActiveIdx] = useState(0);
  const [allRecords, setAllRecords] = useState<PlacedRecord[]>([]);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetch("/api/screenshots").then((r) => r.json()),
      fetch("/api/buildings").then((r) => r.json()),
      fetch("/api/config").then((r) => r.json()),
    ])
      .then(([s, b, c]) => {
        setScreenshots(s as ScreenshotEntry[]);
        setBuildings(b as BuildingsMap);
        setConfig(c as CalibConfig);
      })
      .catch((e: unknown) => setError(String(e)));
  }, []);

  function handleScreenshotSaved(records: PlacedRecord[]) {
    const merged = [...allRecords.filter((r) => r.filename !== screenshots![activeIdx].filename), ...records];
    if (activeIdx < screenshots!.length - 1) {
      setAllRecords(merged);
      setActiveIdx((i) => i + 1);
    } else {
      // Last screenshot — POST everything
      fetch("/api/calibration", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(merged),
      })
        .then(() => setSaved(true))
        .catch((e: unknown) => setError(String(e)));
    }
  }

  if (error) return <div style={{ color: "#f85149", padding: 24, fontFamily: "monospace" }}>{error}</div>;
  if (!screenshots || !buildings || !config)
    return <div style={{ color: "#8b949e", padding: 24, fontFamily: "monospace" }}>Loading…</div>;
  if (saved)
    return (
      <div style={{ color: "#3fb950", padding: 24, fontFamily: "monospace" }}>
        Calibration saved. You can close this tab.
      </div>
    );

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", padding: 8 }}>
      {/* Thumbnail strip */}
      {screenshots.length > 1 && (
        <div style={{ display: "flex", gap: 6, marginBottom: 8, flexShrink: 0, overflowX: "auto" }}>
          {screenshots.map((s, i) => (
            <button
              key={s.filename}
              onClick={() => setActiveIdx(i)}
              style={{
                padding: "3px 10px",
                background: i === activeIdx ? "#1f2937" : "transparent",
                border: i === activeIdx ? "1px solid #4a90e2" : "1px solid #30363d",
                color: "#cdd9e5",
                fontFamily: "monospace",
                fontSize: 11,
                cursor: "pointer",
                borderRadius: 3,
                flexShrink: 0,
              }}
            >
              {s.filename}
            </button>
          ))}
        </div>
      )}
      <div style={{ flex: 1, minHeight: 0 }}>
        <CalibrateView
          key={activeIdx}
          entry={screenshots[activeIdx]}
          buildings={buildings}
          onSaved={handleScreenshotSaved}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Review mode types
// ---------------------------------------------------------------------------

interface CandidatePlacement {
  building_type: string;
  origin: [number, number]; // [row, col] tile coords
}

interface ReviewPayload {
  screenshot_url: string;
  candidate_baselayout: {
    placements: Array<{ building_type: string; origin: [number, number] }>;
    traps: Array<{ trap_type: string; origin: [number, number] }>;
  };
  derived_pitch_px: number;
  derived_origin_px: [number, number];
}

// ---------------------------------------------------------------------------
// ISO basis helpers (must match Python: ISO_ANGLE_1=atan2(1,2), ISO_ANGLE_2=π-ISO_ANGLE_1)
// ---------------------------------------------------------------------------

const ISO_ANGLE_1 = Math.atan2(1, 2);
const ISO_ANGLE_2 = Math.PI - ISO_ANGLE_1;

function tileToPixel(
  col: number,
  row: number,
  pitch: number,
  originPx: [number, number],
): [number, number] {
  const ax = Math.cos(ISO_ANGLE_1) * pitch * col + Math.cos(ISO_ANGLE_2) * pitch * row + originPx[0];
  const ay = Math.sin(ISO_ANGLE_1) * pitch * col + Math.sin(ISO_ANGLE_2) * pitch * row + originPx[1];
  return [ax, ay];
}

function pixelToTile(
  px: number,
  py: number,
  pitch: number,
  originPx: [number, number],
): [number, number] {
  const dx = px - originPx[0];
  const dy = py - originPx[1];
  // 2x2 basis matrix columns: [cos1*p, sin1*p] and [cos2*p, sin2*p]
  const a = Math.cos(ISO_ANGLE_1) * pitch;
  const b = Math.cos(ISO_ANGLE_2) * pitch;
  const c = Math.sin(ISO_ANGLE_1) * pitch;
  const d = Math.sin(ISO_ANGLE_2) * pitch;
  const det = a * d - b * c;
  const col = (d * dx - b * dy) / det;
  const row = (a * dy - c * dx) / det;
  return [col, row];
}

// ---------------------------------------------------------------------------
// ReviewView — canvas overlay with draggable tile placements
// ---------------------------------------------------------------------------

interface ReviewPlacementState {
  idx: number;
  building_type: string;
  col: number;
  row: number;
}

interface ReviewViewProps {
  payload: ReviewPayload;
  buildings: BuildingsMap;
  onSaved: (corrected: CandidatePlacement[]) => void;
}

function ReviewView({ payload, buildings, onSaved }: ReviewViewProps) {
  const imgRef = useRef<HTMLImageElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [scale, setScale] = useState(1);

  const allPlacements: CandidatePlacement[] = [
    ...payload.candidate_baselayout.placements,
    ...payload.candidate_baselayout.traps.map((t) => ({
      building_type: t.trap_type,
      origin: t.origin,
    })),
  ];

  const [placements, setPlacements] = useState<ReviewPlacementState[]>(() =>
    allPlacements.map((p, i) => ({
      idx: i,
      building_type: p.building_type,
      col: p.origin[1], // origin is [row, col] in Python convention
      row: p.origin[0],
    })),
  );

  const dragging = useRef<{ pIdx: number; startCol: number; startRow: number } | null>(null);

  useEffect(() => {
    const img = imgRef.current;
    if (!img) return;
    const updateScale = () => {
      if (img.naturalWidth) setScale(img.clientWidth / img.naturalWidth);
    };
    img.addEventListener("load", updateScale);
    updateScale();
    return () => img.removeEventListener("load", updateScale);
  }, [payload.screenshot_url]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img || !img.naturalWidth) return;

    const w = img.clientWidth;
    const h = img.clientHeight;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d")!;
    ctx.clearRect(0, 0, w, h);

    const pitch = payload.derived_pitch_px * scale;
    const origin: [number, number] = [
      payload.derived_origin_px[0] * scale,
      payload.derived_origin_px[1] * scale,
    ];

    for (const p of placements) {
      const fp = buildings[p.building_type] ?? [1, 1];
      const [cols, rows] = fp; // footprint is [cols, rows] from buildings.json
      const [x0, y0] = tileToPixel(p.col, p.row, pitch, origin);
      const [x1, y1] = tileToPixel(p.col + cols, p.row + rows, pitch, origin);
      ctx.strokeStyle = "rgba(0,200,255,0.95)";
      ctx.lineWidth = 2;
      // Draw the footprint as a parallelogram via all 4 corners
      const [ax, ay] = tileToPixel(p.col, p.row, pitch, origin);
      const [bx, by] = tileToPixel(p.col + cols, p.row, pitch, origin);
      const [cx, cy] = tileToPixel(p.col + cols, p.row + rows, pitch, origin);
      const [dx, dy] = tileToPixel(p.col, p.row + rows, pitch, origin);
      ctx.beginPath();
      ctx.moveTo(ax, ay);
      ctx.lineTo(bx, by);
      ctx.lineTo(cx, cy);
      ctx.lineTo(dx, dy);
      ctx.closePath();
      ctx.stroke();
      ctx.fillStyle = "rgba(0,200,255,0.15)";
      ctx.fill();

      // Label
      ctx.fillStyle = "rgba(0,200,255,0.95)";
      ctx.font = `${Math.max(9, 10 * scale)}px monospace`;
      ctx.fillText(p.building_type, ax + 2, ay - 3);

      // Suppress unused vars warning from the simplified bbox path
      void x0; void y0; void x1; void y1;
    }
  }, [placements, scale, payload, buildings]);

  function canvasCoordToImage(ex: number, ey: number): [number, number] {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    return [(ex - rect.left) / scale, (ey - rect.top) / scale];
  }

  function findNearestPlacement(ix: number, iy: number): number | null {
    const pitch = payload.derived_pitch_px;
    const origin = payload.derived_origin_px as [number, number];
    let best: number | null = null;
    let bestDist = 40;
    for (let i = 0; i < placements.length; i++) {
      const p = placements[i];
      const [px, py] = tileToPixel(p.col, p.row, pitch, origin);
      const d = Math.hypot(px - ix, py - iy);
      if (d < bestDist) {
        bestDist = d;
        best = i;
      }
    }
    return best;
  }

  function onMouseDown(e: React.MouseEvent) {
    const [ix, iy] = canvasCoordToImage(e.clientX, e.clientY);
    const idx = findNearestPlacement(ix, iy);
    if (idx !== null) {
      dragging.current = {
        pIdx: idx,
        startCol: placements[idx].col,
        startRow: placements[idx].row,
      };
    }
  }

  function onMouseMove(e: React.MouseEvent) {
    if (!dragging.current) return;
    const [ix, iy] = canvasCoordToImage(e.clientX, e.clientY);
    const [colF, rowF] = pixelToTile(ix, iy, payload.derived_pitch_px, payload.derived_origin_px as [number, number]);
    const col = Math.round(colF);
    const row = Math.round(rowF);
    const { pIdx } = dragging.current;
    setPlacements((prev) =>
      prev.map((p, i) => (i === pIdx ? { ...p, col, row } : p)),
    );
  }

  function onMouseUp() {
    dragging.current = null;
  }

  function handleSave() {
    const corrected: CandidatePlacement[] = placements.map((p) => ({
      building_type: p.building_type,
      origin: [p.row, p.col], // back to [row, col] for the server
    }));
    onSaved(corrected);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, height: "100%" }}>
      <div
        style={{ position: "relative", flex: 1, overflow: "hidden", cursor: "crosshair" }}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
      >
        <img
          ref={imgRef}
          src={payload.screenshot_url}
          alt="screenshot"
          style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
        />
        <canvas
          ref={canvasRef}
          style={{ position: "absolute", top: 0, left: 0, pointerEvents: "none" }}
        />
      </div>
      <div style={{ display: "flex", gap: 8, padding: "8px 0", flexShrink: 0 }}>
        <button
          onClick={handleSave}
          style={{
            padding: "6px 18px",
            background: "#238636",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            fontFamily: "monospace",
            fontSize: 13,
            cursor: "pointer",
          }}
        >
          Save corrected layout
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Review mode root
// ---------------------------------------------------------------------------

function ReviewMode() {
  const [payload, setPayload] = useState<ReviewPayload | null>(null);
  const [buildings, setBuildings] = useState<BuildingsMap | null>(null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetch("/api/review/baselayout").then((r) => r.json()),
      fetch("/api/buildings").then((r) => r.json()),
    ])
      .then(([p, b]) => {
        setPayload(p as ReviewPayload);
        setBuildings(b as BuildingsMap);
      })
      .catch((e: unknown) => setError(String(e)));
  }, []);

  function handleSaved(corrected: CandidatePlacement[]) {
    fetch("/api/review/baselayout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ corrected_placements: corrected }),
    })
      .then(() => setSaved(true))
      .catch((e: unknown) => setError(String(e)));
  }

  if (error) return <div style={{ color: "#f85149", padding: 24, fontFamily: "monospace" }}>{error}</div>;
  if (!payload || !buildings)
    return <div style={{ color: "#8b949e", padding: 24, fontFamily: "monospace" }}>Loading…</div>;
  if (saved)
    return (
      <div style={{ color: "#3fb950", padding: 24, fontFamily: "monospace" }}>
        Review saved. You can close this tab.
      </div>
    );

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", padding: 8 }}>
      <div style={{ flex: 1, minHeight: 0 }}>
        <ReviewView payload={payload} buildings={buildings} onSaved={handleSaved} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Public export
// ---------------------------------------------------------------------------

export function CartographerPage() {
  const params = new URLSearchParams(window.location.search);
  const mode = params.get("mode") ?? "calibrate";

  if (mode === "calibrate") return <CalibrateMode />;
  if (mode === "review") return <ReviewMode />;

  return (
    <div style={{ color: "#8b949e", padding: 24, fontFamily: "monospace" }}>
      Unknown mode: {mode}
    </div>
  );
}
