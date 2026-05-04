import { describe, expect, it } from "vitest";
import {
  advance,
  createPlayback,
  frameAlpha,
  frameIndex,
  pause,
  play,
  seek,
  setSpeed,
  stepTick,
  togglePlay,
  TICKS_PER_SECOND,
} from "./playback";

describe("createPlayback", () => {
  it("starts at tick 0, paused, speed 1", () => {
    const s = createPlayback(100);
    expect(s).toEqual({ totalTicks: 100, currentTime: 0, playing: false, speed: 1 });
  });

  it("accepts a custom initial speed", () => {
    expect(createPlayback(100, 2).speed).toBe(2);
  });
});

describe("advance", () => {
  it("is a no-op when paused", () => {
    const s = createPlayback(100);
    expect(advance(s, 1000)).toEqual(s);
  });

  it("advances 10 ticks per second at speed 1", () => {
    const s = play(createPlayback(100));
    const after = advance(s, 1000);
    expect(after.currentTime).toBeCloseTo(TICKS_PER_SECOND * 1, 5);
  });

  it("advances faster at higher speeds", () => {
    const s = setSpeed(play(createPlayback(100)), 4);
    const after = advance(s, 100); // 100ms × 10 ticks/sec × 4 = 4 ticks
    expect(after.currentTime).toBeCloseTo(4, 5);
  });

  it("clamps at end and pauses", () => {
    const s = { ...play(createPlayback(20)), currentTime: 18 };
    const after = advance(s, 1000); // would push way past
    expect(after.currentTime).toBe(19);
    expect(after.playing).toBe(false);
  });

  it("does not mutate the input state", () => {
    const s = play(createPlayback(100));
    const snapshot = { ...s };
    advance(s, 500);
    expect(s).toEqual(snapshot);
  });
});

describe("play / pause / togglePlay", () => {
  it("play sets playing=true and preserves currentTime mid-replay", () => {
    const s = seek(createPlayback(100), 25);
    const p = play(s);
    expect(p.playing).toBe(true);
    expect(p.currentTime).toBe(25);
  });

  it("play restarts from 0 if currently at end", () => {
    const s = seek(createPlayback(100), 99);
    const p = play(s);
    expect(p.currentTime).toBe(0);
    expect(p.playing).toBe(true);
  });

  it("pause sets playing=false and preserves currentTime", () => {
    const s = play(seek(createPlayback(100), 25));
    const p = pause(s);
    expect(p.playing).toBe(false);
    expect(p.currentTime).toBe(25);
  });

  it("togglePlay flips playing state", () => {
    const a = createPlayback(100);
    const b = togglePlay(a);
    expect(b.playing).toBe(true);
    expect(togglePlay(b).playing).toBe(false);
  });
});

describe("seek", () => {
  it("clamps to [0, totalTicks-1]", () => {
    const s = createPlayback(100);
    expect(seek(s, -10).currentTime).toBe(0);
    expect(seek(s, 50).currentTime).toBe(50);
    expect(seek(s, 200).currentTime).toBe(99);
  });
});

describe("frameIndex / frameAlpha", () => {
  it("returns floor and fractional part of currentTime", () => {
    const s = { ...createPlayback(100), currentTime: 12.4 };
    expect(frameIndex(s)).toBe(12);
    expect(frameAlpha(s)).toBeCloseTo(0.4, 5);
  });

  it("alpha is 0 at exact tick boundary", () => {
    const s = { ...createPlayback(100), currentTime: 12 };
    expect(frameAlpha(s)).toBe(0);
  });

  it("alpha is 0 at last frame (no next frame to interp toward)", () => {
    const s = { ...createPlayback(100), currentTime: 99 };
    expect(frameIndex(s)).toBe(99);
    expect(frameAlpha(s)).toBe(0);
  });

  it("frameIndex clamps when state is somehow past end", () => {
    const s = { ...createPlayback(10), currentTime: 1000 };
    expect(frameIndex(s)).toBe(9);
  });
});

describe("setSpeed", () => {
  it("updates speed, leaves currentTime/playing alone", () => {
    const s = play(createPlayback(100));
    const t = setSpeed(s, 8);
    expect(t.speed).toBe(8);
    expect(t.playing).toBe(true);
    expect(t.currentTime).toBe(0);
  });
});

describe("stepTick", () => {
  it("advances by one tick when paused", () => {
    const s = seek(createPlayback(100), 10);
    expect(stepTick(s, 1).currentTime).toBe(11);
  });

  it("retreats by one tick when paused", () => {
    const s = seek(createPlayback(100), 10);
    expect(stepTick(s, -1).currentTime).toBe(9);
  });

  it("is a no-op while playing", () => {
    const s = play(seek(createPlayback(100), 10));
    expect(stepTick(s, 1)).toEqual(s);
  });

  it("clamps at 0 when stepping back from tick 0", () => {
    const s = createPlayback(100); // currentTime = 0
    expect(stepTick(s, -1).currentTime).toBe(0);
  });

  it("clamps at totalTicks-1 when stepping past end", () => {
    const s = seek(createPlayback(100), 99);
    expect(stepTick(s, 1).currentTime).toBe(99);
  });

  it("snaps fractional currentTime to floor before stepping forward", () => {
    const s = { ...createPlayback(100), currentTime: 5.7 };
    // floor(5.7) + 1 = 6
    expect(stepTick(s, 1).currentTime).toBe(6);
  });

  it("snaps fractional currentTime to floor before stepping back", () => {
    const s = { ...createPlayback(100), currentTime: 5.7 };
    // floor(5.7) - 1 = 4
    expect(stepTick(s, -1).currentTime).toBe(4);
  });

  it("does not mutate input state", () => {
    const s = seek(createPlayback(100), 10);
    const snapshot = { ...s };
    stepTick(s, 1);
    expect(s).toEqual(snapshot);
  });
});

const SPEEDS = [0.25, 0.5, 1, 2, 4, 8];

describe("speed cycling ([ / ] keyboard shortcut behaviour)", () => {
  it("cycles forward through all speeds", () => {
    let s = createPlayback(100);
    for (let i = 0; i < SPEEDS.length - 1; i++) {
      s = setSpeed(s, SPEEDS[i]);
      const idx = SPEEDS.indexOf(s.speed);
      s = setSpeed(s, SPEEDS[idx + 1]);
    }
    expect(s.speed).toBe(8);
  });

  it("does not exceed max speed (8×)", () => {
    const s = setSpeed(createPlayback(100), 8);
    const idx = SPEEDS.indexOf(s.speed);
    // at max index, no further step possible
    expect(idx).toBe(SPEEDS.length - 1);
  });

  it("does not go below min speed (0.25×)", () => {
    const s = setSpeed(createPlayback(100), 0.25);
    const idx = SPEEDS.indexOf(s.speed);
    expect(idx).toBe(0);
  });

  it("each speed in the list is honored by advance", () => {
    for (const spd of SPEEDS) {
      const s = play(setSpeed(createPlayback(100), spd));
      const after = advance(s, 1000); // 1 second
      expect(after.currentTime).toBeCloseTo(TICKS_PER_SECOND * spd, 4);
    }
  });
});
