import type { TickFrame } from "@/generated_types";

export interface EventMark {
  tick: number;
  type: "deploy" | "damage" | "destroyed" | "spell_cast" | "town_hall_destroyed";
  color: string;
  sizePx: number;
  tooltip: string;
}

const BASE_PX = 4;
const MAX_DAMAGE_PX = 10;

// Build the list of timeline marks from all frames. Damage events are
// aggregated per tick so marks stay countable on long replays.
export function computeEventMarks(frames: TickFrame[]): EventMark[] {
  const marks: EventMark[] = [];
  const damageTotals = new Map<number, number>();

  for (const frame of frames) {
    for (const ev of frame.events) {
      switch (ev.type) {
        case "deploy": {
          const p = ev.payload as { troop_type?: string; level?: number };
          marks.push({
            tick: ev.tick,
            type: "deploy",
            color: "#66bb6a",
            sizePx: BASE_PX,
            tooltip: `deploy • tick ${ev.tick}: ${p.troop_type ?? "troop"} lv${p.level ?? "?"}`,
          });
          break;
        }
        case "damage": {
          const p = ev.payload as { damage?: number };
          const dmg = typeof p.damage === "number" ? p.damage : 0;
          damageTotals.set(ev.tick, (damageTotals.get(ev.tick) ?? 0) + dmg);
          break;
        }
        case "destroyed": {
          const p = ev.payload as {
            category?: string;
            building_type?: string;
            troop_type?: string;
            kind?: string;
          };
          const isTH = p.category === "town_hall" || p.building_type === "town_hall";
          const entityName = p.building_type ?? p.troop_type ?? "entity";
          marks.push({
            tick: ev.tick,
            type: isTH ? "town_hall_destroyed" : "destroyed",
            color: isTH ? "#ffd700" : "#f44336",
            sizePx: isTH ? MAX_DAMAGE_PX : BASE_PX,
            tooltip: isTH
              ? `★ town hall destroyed • tick ${ev.tick}`
              : `destroyed • tick ${ev.tick}: ${entityName} (${p.kind ?? "?"})`,
          });
          break;
        }
        case "spell_cast": {
          const p = ev.payload as { spell_type?: string; level?: number };
          marks.push({
            tick: ev.tick,
            type: "spell_cast",
            color: "#b084ff",
            sizePx: BASE_PX + 2,
            tooltip: `spell_cast • tick ${ev.tick}: ${p.spell_type ?? "spell"} lv${p.level ?? "?"}`,
          });
          break;
        }
        default:
          break;
      }
    }
  }

  for (const [tick, total] of damageTotals) {
    const sizePx = Math.min(MAX_DAMAGE_PX, Math.max(BASE_PX, Math.round(total / 50)));
    marks.push({
      tick,
      type: "damage",
      color: "#ffc107",
      sizePx,
      tooltip: `damage • tick ${tick}: ${total.toFixed(0)} total`,
    });
  }

  return marks;
}
