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
// Public export
// ---------------------------------------------------------------------------

export function CartographerPage() {
  const params = new URLSearchParams(window.location.search);
  const mode = params.get("mode") ?? "calibrate";

  if (mode === "calibrate") return <CalibrateMode />;

  // mode=review — stub for issue 035
  return (
    <div style={{ color: "#8b949e", padding: 24, fontFamily: "monospace" }}>
      Review mode — not yet implemented (issue #35).
    </div>
  );
}
