"""The Sim class: deterministic per-tick orchestrator.

Per PRD §7.2, each tick executes:
  1. Resolve in-flight projectiles -> impact events; despawn silently if homing target died.
  2. Apply scheduled deployments queued for this tick.
  3. Tick active spell casts.
  4. Update troop targeting.            [Placeholder per PRD §13.3]
  5. Advance troop positions.            [Placeholder per PRD §13.3]
  6. Troops attack in range with cooldown ready; create projectiles or apply melee.
  7. Update defense targeting.           [Placeholder per PRD §13.3]
  8. Defenses attack in range; create projectiles.
  9. Apply accumulated damage events; mark destroyed; emit `destroyed` events.
  10. Update score.
  11. Emit `sim_terminated` if termination fires.
  12. Increment tick.

Pathfinding/targeting is a single-target straight-line walk to the nearest non-wall
building; defenses pick the nearest in-range troop. Real targeting is the
deferred grilling.
"""

# Placeholder per PRD §13.3 — replace once pathfinding/targeting grilling lands.

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

from sandbox_core.combat import DamageEvent, defense_damage, troop_damage_against
from sandbox_core.grid import (
    distance_point_to_square_hitbox,
    euclidean,
    footprint_center,
    in_buildable_region,
    in_deploy_ring,
)
from sandbox_core.schemas import (
    AttackKind,
    BaseLayout,
    BuildingState,
    BuildingType,
    DeploymentAction,
    DeploymentPlan,
    Event,
    EventType,
    InvalidDeploymentError,
    Projectile,
    Replay,
    ReplayMetadata,
    Score,
    SimTerminatedError,
    TickFrame,
    TroopState,
    TroopType,
    WorldState,
)
from sandbox_core.scoring import compute_score, is_terminal

TICKS_PER_SECOND: int = 10


@dataclass(slots=True)
class _AttackerCooldown:
    next_ready_tick: int = 0
    has_fired: bool = False


@dataclass(slots=True)
class _SimContext:
    """Per-Sim mutable bookkeeping kept off the WorldState (out of the Replay)."""

    next_entity_id: int = 0
    troop_cd: dict[int, _AttackerCooldown] = field(
        default_factory=lambda: dict[int, _AttackerCooldown]()
    )
    building_cd: dict[int, _AttackerCooldown] = field(
        default_factory=lambda: dict[int, _AttackerCooldown]()
    )
    troop_target: dict[int, int | None] = field(default_factory=lambda: dict[int, int | None]())
    end_attack_emitted: bool = False
    spells_cast_count: int = 0
    pending_damage: dict[int, list[DamageEvent]] = field(
        default_factory=lambda: dict[int, list[DamageEvent]]()
    )


class Sim:
    """Deterministic sandbox-core simulator."""

    __slots__ = (
        "_base",
        "_catalogue_buildings",
        "_catalogue_spells",
        "_catalogue_troops",
        "_config_hash",
        "_ctx",
        "_initial_state",
        "_pending_deployments",
        "_plan",
        "_replay_frames",
        "_sim_version",
        "_terminated",
        "_world",
    )

    def __init__(
        self,
        base: BaseLayout,
        deployment_plan: DeploymentPlan | None = None,
        *,
        catalogue_buildings: dict[str, BuildingType],
        catalogue_troops: dict[str, TroopType],
        catalogue_spells: dict[str, object] | None = None,
        sim_version: str = "0.1.0",
        config_hash: str = "",
    ) -> None:
        self._base = base
        self._plan = deployment_plan
        self._catalogue_buildings = catalogue_buildings
        self._catalogue_troops = catalogue_troops
        self._catalogue_spells = catalogue_spells or {}
        self._sim_version = sim_version
        self._config_hash = config_hash

        self._validate_base()
        if deployment_plan is not None:
            self._validate_plan(deployment_plan)

        self._ctx = _SimContext()
        self._pending_deployments: dict[int, list[DeploymentAction]] = defaultdict(list)
        if deployment_plan is not None:
            for action in deployment_plan.actions:
                self._pending_deployments[action.tick].append(action)

        self._world = self._build_initial_world()
        self._initial_state = self._world.model_copy(deep=True)
        self._replay_frames: list[TickFrame] = []
        self._terminated = False

    # ------------------------------------------------------------------ public

    def reset(self) -> WorldState:
        self.__init__(
            self._base,
            self._plan,
            catalogue_buildings=self._catalogue_buildings,
            catalogue_troops=self._catalogue_troops,
            catalogue_spells=self._catalogue_spells,
            sim_version=self._sim_version,
            config_hash=self._config_hash,
        )
        return self._world.model_copy(deep=True)

    def is_terminal(self) -> bool:
        return self._terminated

    def score(self) -> Score:
        return self._world.score

    def step_tick(self) -> tuple[WorldState, list[Event]]:
        if self._terminated:
            raise SimTerminatedError("Sim already terminated; call reset() to start a new episode.")

        events: list[Event] = []
        tick = self._world.tick

        self._step_projectiles(tick, events)
        self._step_apply_deployments(tick, events)
        self._step_tick_spell_casts(tick, events)
        self._step_troop_attacks(tick, events)
        self._step_defense_attacks(tick, events)
        damage_events = self._collect_pending_damage_events(events)
        self._apply_damage(damage_events, tick, events)
        self._world.score = compute_score(
            buildings=self._world.buildings,
            building_types=self._catalogue_buildings,
            tick=tick,
        )

        if self._check_termination():
            events.append(Event(type=EventType.SIM_TERMINATED, tick=tick, payload={}))
            self._terminated = True

        frame_state = self._world.model_copy(deep=True)
        frame = TickFrame(tick=tick, state=frame_state, events=list(events))
        self._replay_frames.append(frame)

        self._world.tick = tick + 1
        return frame_state, list(events)

    def advance_to(self, target_tick: int) -> list[TickFrame]:
        if target_tick < self._world.tick:
            raise ValueError(f"advance_to({target_tick}) < current_tick ({self._world.tick})")
        out: list[TickFrame] = []
        while self._world.tick <= target_tick and not self._terminated:
            self.step_tick()
            out.append(self._replay_frames[-1])
        return out

    def run_until_termination(self, max_ticks: int = 1800) -> None:
        while not self._terminated and self._world.tick <= max_ticks:
            self.step_tick()

    def schedule_deployment(self, action: DeploymentAction) -> None:
        if self._terminated:
            raise SimTerminatedError("Sim already terminated; cannot schedule deployment.")
        self._validate_action(action)
        self._pending_deployments[action.tick].append(action)

    def to_replay(
        self,
        *,
        base_name: str = "",
        plan_name: str = "",
        run_id: str = "",
        episode_id: str = "",
        started_at: str = "",
        git_sha: str = "",
    ) -> Replay:
        if not self._terminated:
            raise SimTerminatedError("Sim not terminated yet; replay is incomplete.")
        meta = ReplayMetadata(
            sim_version=self._sim_version,
            base_name=base_name or self._base.metadata.name,
            plan_name=plan_name or (self._plan.metadata.name if self._plan else ""),
            run_id=run_id,
            episode_id=episode_id,
            total_ticks=len(self._replay_frames),
            final_score=self._world.score,
            started_at=started_at,
            git_sha=git_sha,
            config_hash=self._config_hash,
        )
        return Replay(
            metadata=meta,
            initial_state=self._initial_state,
            frames=list(self._replay_frames),
        )

    # ----------------------------------------------------------------- helpers

    def _next_id(self) -> int:
        i = self._ctx.next_entity_id
        self._ctx.next_entity_id = i + 1
        return i

    def _validate_base(self) -> None:
        seen_th = 0
        for placement in self._base.placements:
            if placement.building_type not in self._catalogue_buildings:
                raise InvalidDeploymentError(f"unknown building_type: {placement.building_type!r}")
            bt = self._catalogue_buildings[placement.building_type]
            if bt.category.value == "town_hall":
                seen_th += 1
        if seen_th != 1:
            raise InvalidDeploymentError(
                f"BaseLayout must contain exactly 1 Town Hall; found {seen_th}"
            )

    def _validate_plan(self, plan: DeploymentPlan) -> None:
        for action in plan.actions:
            self._validate_action(action)

    def _validate_action(self, action: DeploymentAction) -> None:
        if action.kind == "deploy_troop":
            if action.entity_type not in self._catalogue_troops:
                raise InvalidDeploymentError(f"unknown troop_type: {action.entity_type!r}")
            r, c = action.position
            ri, ci = math.floor(r), math.floor(c)
            if not in_deploy_ring(ri, ci):
                raise InvalidDeploymentError(
                    f"troop deploy position {action.position} outside deploy ring"
                )
        elif action.kind == "cast_spell":
            if action.entity_type not in self._catalogue_spells:
                raise InvalidDeploymentError(f"unknown spell_type: {action.entity_type!r}")
            r, c = action.position
            ri, ci = math.floor(r), math.floor(c)
            if not in_buildable_region(ri, ci):
                raise InvalidDeploymentError(
                    f"spell cast position {action.position} outside inner buildable region"
                )

    def _build_initial_world(self) -> WorldState:
        buildings: list[BuildingState] = []
        for placement in self._base.placements:
            bt = self._catalogue_buildings[placement.building_type]
            level = placement.level if placement.level is not None else self._base.th_level
            level = min(level, max(s.level for s in bt.levels))
            stats = bt.stats_at(level)
            bid = self._next_id()
            buildings.append(
                BuildingState(
                    id=bid,
                    building_type=placement.building_type,
                    origin=placement.origin,
                    level=level,
                    hp=stats.hp,
                    max_hp=stats.hp,
                )
            )
            self._ctx.building_cd[bid] = _AttackerCooldown()
        score = compute_score(
            buildings=buildings,
            building_types=self._catalogue_buildings,
            tick=0,
        )
        return WorldState(
            tick=0,
            buildings=buildings,
            troops=[],
            projectiles=[],
            spells=[],
            score=score,
        )

    # ----- per-tick steps ---------------------------------------------------

    def _step_projectiles(self, tick: int, events: list[Event]) -> None:
        if not self._world.projectiles:
            return
        survivors: list[Projectile] = []
        damage_events: list[DamageEvent] = []
        for proj in sorted(self._world.projectiles, key=lambda p: p.id):
            new_ttl = proj.ticks_to_impact - 1
            if new_ttl > 0:
                # Advance current_position one step along the line to impact.
                steps_remaining = new_ttl
                cr, cc = proj.current_position
                ir, ic = proj.impact_position
                if steps_remaining > 0:
                    nr = cr + (ir - cr) / (steps_remaining + 1)
                    nc = cc + (ic - cc) / (steps_remaining + 1)
                else:
                    nr, nc = ir, ic
                survivors.append(
                    proj.model_copy(
                        update={
                            "current_position": (nr, nc),
                            "ticks_to_impact": new_ttl,
                        }
                    )
                )
                continue

            # Impact tick.
            if proj.attack_kind == AttackKind.RANGED and proj.target_id is not None:
                target_alive = self._building_alive(proj.target_id) or self._troop_alive(
                    proj.target_id
                )
                if not target_alive:
                    # Homing case — silently despawn (per PRD §5.6).
                    continue
                damage_events.append(
                    DamageEvent(
                        target_id=proj.target_id, damage=proj.damage, attacker_id=proj.attacker_id
                    )
                )
                events.append(
                    Event(
                        type=EventType.DAMAGE,
                        tick=tick,
                        payload={
                            "target_id": proj.target_id,
                            "damage": proj.damage,
                            "attacker_id": proj.attacker_id,
                            "kind": proj.attack_kind.value,
                        },
                    )
                )
        self._world.projectiles = survivors
        self._enqueue_damage(tick, damage_events)

    def _step_apply_deployments(self, tick: int, events: list[Event]) -> None:
        actions = self._pending_deployments.pop(tick, [])
        for action in actions:
            if action.kind == "deploy_troop":
                troop = self._catalogue_troops[action.entity_type]
                level = action.level if action.level is not None else self._base.th_level
                level = min(level, max(s.level for s in troop.levels))
                stats = troop.stats_at(level)
                tid = self._next_id()
                self._world.troops.append(
                    TroopState(
                        id=tid,
                        troop_type=troop.name,
                        level=level,
                        position=action.position,
                        hp=stats.hp,
                        max_hp=stats.hp,
                    )
                )
                self._ctx.troop_cd[tid] = _AttackerCooldown()
                events.append(
                    Event(
                        type=EventType.DEPLOY,
                        tick=tick,
                        payload={
                            "troop_id": tid,
                            "troop_type": troop.name,
                            "position": list(action.position),
                            "level": level,
                        },
                    )
                )
            elif action.kind == "cast_spell":
                # Spells deferred to issue 009; placeholder cast bookkeeping.
                self._ctx.spells_cast_count += 1

    def _step_tick_spell_casts(self, tick: int, events: list[Event]) -> None:
        # Phase 0 has no spells. Issue 009 implements bolt cadence.
        _ = (tick, events)

    def _step_troop_attacks(self, tick: int, events: list[Event]) -> None:
        # Placeholder per PRD §13.3: each troop walks straight at the nearest
        # non-wall building. Melee attack on hitbox-adjacency.
        for troop in sorted(self._world.troops, key=lambda t: t.id):
            if troop.destroyed:
                continue
            tt = self._catalogue_troops[troop.troop_type]
            target = self._nearest_living_building(troop.position, prefer_non_wall=True)
            if target is None:
                continue

            bt = self._catalogue_buildings[target.building_type]
            inset = bt.hitbox_inset if bt.hitbox_inset is not None else 0.5
            dist = distance_point_to_square_hitbox(
                troop.position, target.origin, bt.footprint, inset
            )

            stats = tt.stats_at(troop.level)
            attack_range = max(stats.range_tiles, 0.0)
            in_range = dist <= attack_range + 1e-9

            if in_range:
                cd = self._ctx.troop_cd[troop.id]
                if not cd.has_fired or tick >= cd.next_ready_tick:
                    self._fire_troop_attack(troop, tt, target, bt, tick, events, stats)
                    cd.has_fired = True
                    cd.next_ready_tick = tick + max(stats.attack_cooldown_ticks, 1)
            else:
                # Move toward the target.
                self._move_troop_toward(troop, tt, target, bt, inset)

    def _fire_troop_attack(
        self,
        troop: TroopState,
        tt: TroopType,
        target: BuildingState,
        bt: BuildingType,
        tick: int,
        events: list[Event],
        stats: object,
    ) -> None:
        _ = stats
        damage = troop_damage_against(tt, troop.level, bt.category)
        speed = tt.projectile_speed_tiles_per_sec
        if speed is None or speed <= 0:
            # Melee / instant: enqueue damage immediately.
            self._enqueue_damage(
                tick,
                [DamageEvent(target_id=target.id, damage=damage, attacker_id=troop.id)],
            )
            events.append(
                Event(
                    type=EventType.DAMAGE,
                    tick=tick,
                    payload={
                        "target_id": target.id,
                        "damage": damage,
                        "attacker_id": troop.id,
                        "kind": AttackKind.MELEE.value,
                    },
                )
            )
        else:
            # Ranged projectile.
            target_center = footprint_center(target.origin, bt.footprint)
            distance = euclidean(troop.position, target_center)
            ticks_to_impact = max(1, round(distance / speed * TICKS_PER_SECOND))
            pid = self._next_id()
            self._world.projectiles.append(
                Projectile(
                    id=pid,
                    attacker_id=troop.id,
                    target_id=target.id,
                    attack_kind=AttackKind.RANGED,
                    attacker_position=troop.position,
                    current_position=troop.position,
                    impact_position=target_center,
                    damage=damage,
                    splash_radius_tiles=tt.splash_radius_tiles,
                    splash_damages_walls=tt.splash_damages_walls,
                    ticks_to_impact=ticks_to_impact,
                )
            )
            events.append(
                Event(
                    type=EventType.PROJECTILE_FIRED,
                    tick=tick,
                    payload={
                        "projectile_id": pid,
                        "attacker_id": troop.id,
                        "target_id": target.id,
                        "ticks_to_impact": ticks_to_impact,
                    },
                )
            )

    def _move_troop_toward(
        self,
        troop: TroopState,
        tt: TroopType,
        target: BuildingState,
        bt: BuildingType,
        inset: float,
    ) -> None:
        # Step toward the closest hitbox tile center along a straight line.
        tr, tc = footprint_center(target.origin, bt.footprint)
        pr, pc = troop.position
        dr, dc = tr - pr, tc - pc
        dist = math.hypot(dr, dc)
        if dist <= 1e-9:
            return
        step = tt.speed_tiles_per_sec / TICKS_PER_SECOND
        # Stop at the hitbox edge so we don't penetrate.
        target_dist = distance_point_to_square_hitbox((pr, pc), target.origin, bt.footprint, inset)
        actual_step = min(step, target_dist)
        if actual_step <= 0:
            return
        ux, uy = dr / dist, dc / dist
        troop.position = (pr + ux * actual_step, pc + uy * actual_step)

    def _step_defense_attacks(self, tick: int, events: list[Event]) -> None:
        # Placeholder per PRD §13.3: defenses pick the nearest in-range troop
        # with no preference. Filter respect (ground/air/both) is honored.
        for b in sorted(self._world.buildings, key=lambda x: x.id):
            if b.destroyed:
                continue
            bt = self._catalogue_buildings[b.building_type]
            if bt.category.value != "defense":
                continue
            stats = bt.stats_at(b.level)
            if stats.damage_per_shot <= 0 or stats.range_tiles <= 0:
                continue
            target = self._nearest_in_range_troop(b, bt, stats.range_tiles)
            if target is None:
                continue
            cd = self._ctx.building_cd[b.id]
            if not cd.has_fired or tick >= cd.next_ready_tick:
                self._fire_defense_attack(b, bt, target, tick, events)
                cd.has_fired = True
                cd.next_ready_tick = tick + max(stats.attack_cooldown_ticks, 1)

    def _fire_defense_attack(
        self,
        b: BuildingState,
        bt: BuildingType,
        target: TroopState,
        tick: int,
        events: list[Event],
    ) -> None:
        damage = defense_damage(bt, b.level)
        speed = bt.projectile_speed_tiles_per_sec
        b_center = footprint_center(b.origin, bt.footprint)
        if speed is None or speed <= 0:
            self._enqueue_damage(
                tick,
                [DamageEvent(target_id=target.id, damage=damage, attacker_id=b.id)],
            )
            events.append(
                Event(
                    type=EventType.DAMAGE,
                    tick=tick,
                    payload={
                        "target_id": target.id,
                        "damage": damage,
                        "attacker_id": b.id,
                        "kind": AttackKind.MELEE.value,
                    },
                )
            )
        else:
            distance = euclidean(b_center, target.position)
            ticks_to_impact = max(1, round(distance / speed * TICKS_PER_SECOND))
            pid = self._next_id()
            self._world.projectiles.append(
                Projectile(
                    id=pid,
                    attacker_id=b.id,
                    target_id=target.id,
                    attack_kind=AttackKind.RANGED,
                    attacker_position=b_center,
                    current_position=b_center,
                    impact_position=target.position,
                    damage=damage,
                    splash_radius_tiles=bt.splash_radius_tiles,
                    splash_damages_walls=bt.splash_damages_walls,
                    ticks_to_impact=ticks_to_impact,
                )
            )
            events.append(
                Event(
                    type=EventType.PROJECTILE_FIRED,
                    tick=tick,
                    payload={
                        "projectile_id": pid,
                        "attacker_id": b.id,
                        "target_id": target.id,
                        "ticks_to_impact": ticks_to_impact,
                    },
                )
            )

    # ----- damage bookkeeping ----------------------------------------------

    def _enqueue_damage(self, tick: int, events: list[DamageEvent]) -> None:
        if not events:
            return
        self._ctx.pending_damage.setdefault(tick, []).extend(events)

    def _collect_pending_damage_events(self, _events: list[Event]) -> list[DamageEvent]:
        tick = self._world.tick
        return self._ctx.pending_damage.pop(tick, [])

    def _apply_damage(
        self,
        damage_events: list[DamageEvent],
        tick: int,
        events: list[Event],
    ) -> None:
        if not damage_events:
            return
        building_idx = {b.id: b for b in self._world.buildings}
        troop_idx = {t.id: t for t in self._world.troops}
        for de in damage_events:
            if de.target_id in building_idx:
                target = building_idx[de.target_id]
                if target.destroyed:
                    continue
                target.hp -= de.damage
                if target.hp <= 0:
                    target.hp = 0.0
                    target.destroyed = True
            elif de.target_id in troop_idx:
                target_t = troop_idx[de.target_id]
                if target_t.destroyed:
                    continue
                target_t.hp -= de.damage
                if target_t.hp <= 0:
                    target_t.hp = 0.0
                    target_t.destroyed = True

        # Emit destroyed events in id-ascending order (PRD §7.4).
        destroyed_buildings: list[BuildingState] = [
            b
            for b in sorted(self._world.buildings, key=lambda x: x.id)
            if b.destroyed and b.id in {de.target_id for de in damage_events}
        ]
        for b in destroyed_buildings:
            bt = self._catalogue_buildings[b.building_type]
            events.append(
                Event(
                    type=EventType.DESTROYED,
                    tick=tick,
                    payload={
                        "kind": "building",
                        "building_id": b.id,
                        "building_type": b.building_type,
                        "category": bt.category.value,
                    },
                )
            )

        destroyed_troops = [
            t
            for t in sorted(self._world.troops, key=lambda x: x.id)
            if t.destroyed and t.id in {de.target_id for de in damage_events}
        ]
        for t in destroyed_troops:
            events.append(
                Event(
                    type=EventType.DESTROYED,
                    tick=tick,
                    payload={"kind": "troop", "troop_id": t.id, "troop_type": t.troop_type},
                )
            )

    # ----- targeting helpers ----------------------------------------------

    def _building_alive(self, bid: int) -> bool:
        for b in self._world.buildings:
            if b.id == bid:
                return not b.destroyed
        return False

    def _troop_alive(self, tid: int) -> bool:
        for t in self._world.troops:
            if t.id == tid:
                return not t.destroyed
        return False

    def _nearest_living_building(
        self,
        position: tuple[float, float],
        *,
        prefer_non_wall: bool,
    ) -> BuildingState | None:
        best: BuildingState | None = None
        best_dist = math.inf
        for b in sorted(self._world.buildings, key=lambda x: x.id):
            if b.destroyed:
                continue
            bt = self._catalogue_buildings[b.building_type]
            if prefer_non_wall and bt.is_wall:
                continue
            inset = bt.hitbox_inset if bt.hitbox_inset is not None else 0.5
            d = distance_point_to_square_hitbox(position, b.origin, bt.footprint, inset)
            if d < best_dist:
                best_dist = d
                best = b
        if best is not None:
            return best
        # Fallback: any building including walls (e.g., corridor-blocking).
        if prefer_non_wall:
            return self._nearest_living_building(position, prefer_non_wall=False)
        return None

    def _nearest_in_range_troop(
        self,
        building: BuildingState,
        bt: BuildingType,
        range_tiles: float,
    ) -> TroopState | None:
        b_center = footprint_center(building.origin, bt.footprint)
        target_filter = bt.target_filter.value
        best: TroopState | None = None
        best_dist = math.inf
        for t in sorted(self._world.troops, key=lambda x: x.id):
            if t.destroyed:
                continue
            tt = self._catalogue_troops[t.troop_type]
            cat = tt.category.value
            if target_filter == "ground" and cat != "ground":
                continue
            if target_filter == "air" and cat != "air":
                continue
            d = euclidean(b_center, t.position)
            if d <= range_tiles + 1e-9 and d < best_dist:
                best_dist = d
                best = t
        return best

    # ----- termination -----------------------------------------------------

    def _check_termination(self) -> bool:
        # Count remaining future deployments (for "nothing left" condition).
        future_actions = sum(
            len(actions)
            for tick, actions in self._pending_deployments.items()
            if tick > self._world.tick
        )
        same_tick_pending = len(self._pending_deployments.get(self._world.tick, []))
        troops_in_pipeline = future_actions + same_tick_pending
        return is_terminal(
            world=self._world,
            troops_remaining_in_camps=troops_in_pipeline,
            spells_remaining=0,
            end_attack_emitted=self._ctx.end_attack_emitted,
        )


__all__ = ["TICKS_PER_SECOND", "Sim"]
