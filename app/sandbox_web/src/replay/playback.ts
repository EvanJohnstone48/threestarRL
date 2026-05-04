// Pure playback state for the replay viewer.
//
// Time is tracked as a float in tick-units (0..totalTicks-1). At base speed,
// 10 ticks elapse per real second (sandbox-core runs at 10 Hz — PRD §7).
// The renderer interpolates linearly between consecutive frames; the fractional
// part of `currentTime` IS the interpolation alpha.

export const TICKS_PER_SECOND = 10;

export interface PlaybackState {
  totalTicks: number;
  currentTime: number;
  playing: boolean;
  speed: number;
}

export function createPlayback(totalTicks: number, speed: number = 1): PlaybackState {
  return {
    totalTicks,
    currentTime: 0,
    playing: false,
    speed,
  };
}

// `dtMs` is the wall-clock delta since the last render frame. Returns a new
// state — never mutates the input.
export function advance(state: PlaybackState, dtMs: number): PlaybackState {
  if (!state.playing) return state;
  if (state.totalTicks <= 0) return state;
  const ticksAdvanced = (dtMs / 1000) * TICKS_PER_SECOND * state.speed;
  let newTime = state.currentTime + ticksAdvanced;
  const maxTime = Math.max(0, state.totalTicks - 1);
  let playing: boolean = state.playing;
  if (newTime >= maxTime) {
    newTime = maxTime;
    playing = false; // pause at end of replay
  }
  return { ...state, currentTime: newTime, playing };
}

export function play(state: PlaybackState): PlaybackState {
  // If already at end, restart from 0.
  const maxTime = Math.max(0, state.totalTicks - 1);
  const at = state.currentTime >= maxTime ? 0 : state.currentTime;
  return { ...state, currentTime: at, playing: true };
}

export function pause(state: PlaybackState): PlaybackState {
  return { ...state, playing: false };
}

export function togglePlay(state: PlaybackState): PlaybackState {
  return state.playing ? pause(state) : play(state);
}

export function seek(state: PlaybackState, tick: number): PlaybackState {
  const maxTime = Math.max(0, state.totalTicks - 1);
  const clamped = Math.min(maxTime, Math.max(0, tick));
  return { ...state, currentTime: clamped };
}

export function setSpeed(state: PlaybackState, speed: number): PlaybackState {
  return { ...state, speed };
}

// The integer index into `replay.frames` to render. Always within
// [0, totalTicks - 1].
export function frameIndex(state: PlaybackState): number {
  if (state.totalTicks <= 0) return 0;
  const idx = Math.floor(state.currentTime);
  return Math.min(state.totalTicks - 1, Math.max(0, idx));
}

// Interpolation alpha between `frameIndex(state)` and the next frame.
// Returns 0 when at end-of-replay (no next frame to interp toward).
export function frameAlpha(state: PlaybackState): number {
  const idx = frameIndex(state);
  if (idx >= state.totalTicks - 1) return 0;
  return state.currentTime - idx;
}
