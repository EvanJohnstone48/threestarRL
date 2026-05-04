import { useCallback, useEffect, useRef, useState } from "react";
import { Application } from "pixi.js";

import type { Replay } from "@/generated_types";
import { interpolateFrame } from "@/replay/interpolation";
import {
  ReplayLoadError,
  RUNTIME_SCHEMA_VERSION,
  crossVersionBanner,
  loadReplayFromFile,
  loadReplayFromUrl,
} from "@/replay/loader";
import {
  advance,
  createPlayback,
  frameAlpha,
  frameIndex,
  togglePlay,
  type PlaybackState,
} from "@/replay/playback";
import { TopDownRenderer } from "@/render/topdown";

const RUNTIME_SIM_VERSION = "0.1.0";

interface RendererHandle {
  app: Application;
  renderer: TopDownRenderer;
}

export function ReplayViewer() {
  const canvasContainerRef = useRef<HTMLDivElement | null>(null);
  const handleRef = useRef<RendererHandle | null>(null);
  const playbackRef = useRef<PlaybackState | null>(null);
  const replayRef = useRef<Replay | null>(null);
  const lastFrameTsRef = useRef<number | null>(null);

  // Mirror of playbackRef into React state so the toolbar re-renders.
  const [, setPlaybackTick] = useState(0);
  const [replay, setReplay] = useState<Replay | null>(null);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  // Mount Pixi app once.
  useEffect(() => {
    const container = canvasContainerRef.current;
    if (!container) return;
    let cancelled = false;
    let cleanup: (() => void) | null = null;

    const init = async () => {
      const app = new Application();
      await app.init({
        background: 0x0d1117,
        resizeTo: container,
        antialias: true,
      });
      if (cancelled) {
        app.destroy(true, { children: true });
        return;
      }
      container.appendChild(app.canvas);
      const renderer = new TopDownRenderer(app);
      handleRef.current = { app, renderer };

      app.ticker.add(() => {
        const playback = playbackRef.current;
        const r = replayRef.current;
        const now = performance.now();
        const last = lastFrameTsRef.current;
        lastFrameTsRef.current = now;
        if (!playback || !r || r.frames.length === 0) return;
        if (playback.playing && last !== null) {
          const dt = now - last;
          const next = advance(playback, dt);
          playbackRef.current = next;
          if (next.playing !== playback.playing) setPlaying(next.playing);
          setPlaybackTick(Math.floor(next.currentTime));
        }
        const cur_pb = playbackRef.current;
        if (!cur_pb) return;
        const idx = frameIndex(cur_pb);
        const alpha = frameAlpha(cur_pb);
        const cur = r.frames[idx];
        const nxt = idx + 1 < r.frames.length ? r.frames[idx + 1] : null;
        const interp = interpolateFrame(cur, nxt, alpha);
        renderer.renderFrame(interp, cur);
      });

      cleanup = () => {
        app.destroy(true, { children: true });
        handleRef.current = null;
      };
    };

    void init();

    return () => {
      cancelled = true;
      if (cleanup) cleanup();
    };
  }, []);

  // Load from ?replay=<path> on mount.
  useEffect(() => {
    const url = new URLSearchParams(window.location.search).get("replay");
    if (!url) return;
    setLoading(true);
    loadReplayFromUrl(url)
      .then(adoptReplay)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const adoptReplay = useCallback((r: Replay) => {
    setReplay(r);
    setError(null);
    replayRef.current = r;
    playbackRef.current = createPlayback(r.frames.length);
    lastFrameTsRef.current = null;
    setPlaying(false);
    setPlaybackTick(0);
  }, []);

  const onFilePicked = useCallback(
    (file: File) => {
      setLoading(true);
      setError(null);
      loadReplayFromFile(file)
        .then(adoptReplay)
        .catch((err: unknown) => {
          setError(
            err instanceof ReplayLoadError
              ? err.message
              : `Failed to load replay: ${err instanceof Error ? err.message : String(err)}`,
          );
        })
        .finally(() => setLoading(false));
    },
    [adoptReplay],
  );

  const onDrop = useCallback(
    (ev: React.DragEvent) => {
      ev.preventDefault();
      setDragOver(false);
      const file = ev.dataTransfer.files[0];
      if (file) onFilePicked(file);
    },
    [onFilePicked],
  );

  const onTogglePlay = useCallback(() => {
    if (!playbackRef.current) return;
    const next = togglePlay(playbackRef.current);
    playbackRef.current = next;
    setPlaying(next.playing);
    lastFrameTsRef.current = null;
  }, []);

  const onFitToGrid = useCallback(() => {
    handleRef.current?.renderer.fitToGrid();
  }, []);

  // Keyboard: spacebar = play/pause
  useEffect(() => {
    const handler = (ev: KeyboardEvent) => {
      if (ev.target instanceof HTMLInputElement || ev.target instanceof HTMLTextAreaElement) return;
      if (ev.code === "Space") {
        ev.preventDefault();
        onTogglePlay();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onTogglePlay]);

  const banner =
    replay && crossVersionBanner(replay, RUNTIME_SCHEMA_VERSION)
      ? crossVersionBanner(replay, RUNTIME_SCHEMA_VERSION)
      : replay && replay.metadata.sim_version !== RUNTIME_SIM_VERSION
        ? `Replay sim_version ${replay.metadata.sim_version} loaded under runtime ${RUNTIME_SIM_VERSION} — playback only.`
        : null;

  return (
    <div className="viewer-root">
      <header className="viewer-header">
        <h1>threestarRL — Sandbox Replay Viewer</h1>
        <div className="viewer-toolbar">
          <button type="button" onClick={onTogglePlay} disabled={!replay}>
            {playing ? "Pause" : "Play"}
          </button>
          <button type="button" onClick={onFitToGrid}>
            Fit to grid
          </button>
          <label className="file-picker">
            Load replay…
            <input
              type="file"
              accept="application/json,.json"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onFilePicked(f);
                e.target.value = "";
              }}
            />
          </label>
          {replay && (
            <span className="tick-counter" data-testid="tick-counter">
              {Math.floor(playbackRef.current?.currentTime ?? 0)} / {replay.frames.length - 1}
            </span>
          )}
        </div>
      </header>
      {banner && (
        <div className="banner banner-warn" role="status">
          {banner}
        </div>
      )}
      {error && (
        <div className="banner banner-error" role="alert">
          {error}
        </div>
      )}
      {loading && <div className="banner banner-info">Loading replay…</div>}
      <div
        className={`canvas-container${dragOver ? " drag-over" : ""}`}
        ref={canvasContainerRef}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
      >
        {!replay && !loading && (
          <div className="drop-hint">Drag a replay JSON here, or click "Load replay…"</div>
        )}
      </div>
    </div>
  );
}
