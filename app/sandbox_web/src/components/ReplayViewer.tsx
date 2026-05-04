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
  seek,
  setSpeed,
  stepTick,
  togglePlay,
  type PlaybackState,
} from "@/replay/playback";
import { TopDownRenderer } from "@/render/topdown";

const RUNTIME_SIM_VERSION = "0.1.0";
const SPEEDS = [0.25, 0.5, 1, 2, 4, 8];

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

  const [playbackTick, setPlaybackTick] = useState(0);
  const [replay, setReplay] = useState<Replay | null>(null);
  const [playing, setPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
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
    setPlaybackSpeed(1);
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

  const onSeek = useCallback((tick: number) => {
    if (!playbackRef.current) return;
    const next = seek(playbackRef.current, tick);
    playbackRef.current = next;
    setPlaybackTick(Math.floor(next.currentTime));
  }, []);

  const onStep = useCallback((delta: 1 | -1) => {
    if (!playbackRef.current) return;
    const next = stepTick(playbackRef.current, delta);
    playbackRef.current = next;
    setPlaybackTick(Math.floor(next.currentTime));
  }, []);

  const onSetSpeed = useCallback((speed: number) => {
    if (!playbackRef.current) return;
    const next = setSpeed(playbackRef.current, speed);
    playbackRef.current = next;
    setPlaybackSpeed(speed);
  }, []);

  const onFitToGrid = useCallback(() => {
    handleRef.current?.renderer.fitToGrid();
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (ev: KeyboardEvent) => {
      if (ev.target instanceof HTMLInputElement || ev.target instanceof HTMLTextAreaElement) return;
      if (ev.code === "Space") {
        ev.preventDefault();
        onTogglePlay();
      } else if (ev.code === "ArrowLeft") {
        ev.preventDefault();
        onStep(-1);
      } else if (ev.code === "ArrowRight") {
        ev.preventDefault();
        onStep(1);
      } else if (ev.key === "[") {
        ev.preventDefault();
        if (!playbackRef.current) return;
        const idx = SPEEDS.indexOf(playbackRef.current.speed);
        if (idx > 0) onSetSpeed(SPEEDS[idx - 1]);
      } else if (ev.key === "]") {
        ev.preventDefault();
        if (!playbackRef.current) return;
        const idx = SPEEDS.indexOf(playbackRef.current.speed);
        if (idx < SPEEDS.length - 1) onSetSpeed(SPEEDS[idx + 1]);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onTogglePlay, onStep, onSetSpeed]);

  const banner =
    replay && crossVersionBanner(replay, RUNTIME_SCHEMA_VERSION)
      ? crossVersionBanner(replay, RUNTIME_SCHEMA_VERSION)
      : replay && replay.metadata.sim_version !== RUNTIME_SIM_VERSION
        ? `Replay sim_version ${replay.metadata.sim_version} loaded under runtime ${RUNTIME_SIM_VERSION} — playback only.`
        : null;

  const totalTicks = replay ? replay.frames.length - 1 : 0;

  return (
    <div className="viewer-root">
      <header className="viewer-header">
        <h1>threestarRL — Sandbox Replay Viewer</h1>
        <div className="viewer-toolbar">
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
      <div className="viewer-bottom" aria-label="Playback controls">
        <input
          type="range"
          className="scrub-bar"
          data-testid="scrub-bar"
          min={0}
          max={totalTicks}
          step={1}
          value={playbackTick}
          disabled={!replay}
          onChange={(e) => onSeek(Number(e.target.value))}
          aria-label="Scrub timeline"
        />
        <div className="bottom-controls">
          <button
            type="button"
            onClick={() => onStep(-1)}
            disabled={!replay || playing}
            aria-label="Step back one tick"
            title="Step back (←)"
          >
            −1
          </button>
          <button
            type="button"
            onClick={onTogglePlay}
            disabled={!replay}
            aria-label={playing ? "Pause" : "Play"}
            title="Play/Pause (Space)"
          >
            {playing ? "⏸" : "▶"}
          </button>
          <button
            type="button"
            onClick={() => onStep(1)}
            disabled={!replay || playing}
            aria-label="Step forward one tick"
            title="Step forward (→)"
          >
            +1
          </button>
          <select
            className="speed-select"
            data-testid="speed-select"
            value={playbackSpeed}
            disabled={!replay}
            onChange={(e) => onSetSpeed(Number(e.target.value))}
            aria-label="Playback speed"
          >
            {SPEEDS.map((s) => (
              <option key={s} value={s}>
                {s}×
              </option>
            ))}
          </select>
          {replay && (
            <span className="tick-counter" data-testid="tick-counter">
              {playbackTick} / {totalTicks}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
