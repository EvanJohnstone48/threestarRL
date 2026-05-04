// Per-render-tick interpolation between consecutive replay frames.
//
// PRD §8.4: troop and projectile positions interp linearly between two
// adjacent TickFrames; buildings + HP bars are tick-quantized.
// 6 render frames per sim tick at 60 fps / 10 Hz.

import type { Projectile, TickFrame, TroopState, WorldState } from "@/generated_types";

export interface InterpolatedTroop {
  id: number;
  troop_type: string;
  level: number;
  position: [number, number];
  hp: number;
  max_hp: number;
  destroyed: boolean;
}

export interface InterpolatedProjectile {
  id: number;
  current_position: [number, number];
  splash_radius_tiles: number;
}

export interface InterpolatedFrame {
  tick: number;
  state: WorldState;
  troops: InterpolatedTroop[];
  projectiles: InterpolatedProjectile[];
}

// Lerp a position by `alpha` from `from` toward `to`.
export function lerpPos(
  from: [number, number],
  to: [number, number],
  alpha: number,
): [number, number] {
  return [from[0] + (to[0] - from[0]) * alpha, from[1] + (to[1] - from[1]) * alpha];
}

// Compute the visual frame at fractional tick `index + alpha` from the two
// adjacent TickFrames. Buildings and HP bars come from `current` (no interp);
// troops + projectiles match by id and lerp positions toward `next`. Entities
// only present in `current` (died this tick) hold their `current` position;
// entities only in `next` (newly spawned) appear at `next` position with
// alpha=0 effectively (they "pop in" on the tick boundary, matching sim
// semantics).
export function interpolateFrame(
  current: TickFrame,
  next: TickFrame | null,
  alpha: number,
): InterpolatedFrame {
  const state = current.state;
  if (next === null || alpha <= 0) {
    return {
      tick: current.tick,
      state,
      troops: state.troops.map(troopFromState),
      projectiles: state.projectiles.map(projFromState),
    };
  }
  const nextTroops = new Map<number, TroopState>();
  for (const t of next.state.troops) nextTroops.set(t.id, t);
  const troops: InterpolatedTroop[] = state.troops.map((t) => {
    const n = nextTroops.get(t.id);
    if (!n) return troopFromState(t);
    return { ...troopFromState(t), position: lerpPos(t.position, n.position, alpha) };
  });

  const nextProj = new Map<number, Projectile>();
  for (const p of next.state.projectiles) nextProj.set(p.id, p);
  const projectiles: InterpolatedProjectile[] = state.projectiles.map((p) => {
    const n = nextProj.get(p.id);
    if (!n) return projFromState(p);
    return {
      id: p.id,
      current_position: lerpPos(p.current_position, n.current_position, alpha),
      splash_radius_tiles: p.splash_radius_tiles,
    };
  });

  return { tick: current.tick, state, troops, projectiles };
}

function troopFromState(t: TroopState): InterpolatedTroop {
  return {
    id: t.id,
    troop_type: t.troop_type,
    level: t.level,
    position: t.position,
    hp: t.hp,
    max_hp: t.max_hp,
    destroyed: t.destroyed,
  };
}

function projFromState(p: Projectile): InterpolatedProjectile {
  return {
    id: p.id,
    current_position: p.current_position,
    splash_radius_tiles: p.splash_radius_tiles,
  };
}
