# 004 — Wiki scraper + manual overrides loader

**GitHub Issue:** #4

## Parent PRD

`app/docs/sandbox/prd.md` (§3.3, §9)

## What to build

The deterministic offline scraper that produces v1 content data files from the Clash of Clans Fan Wiki, plus the runtime loader's manual-overrides merge layer.

Scraper:

- `python -m sandbox_core.tools.scrape_wiki [--out app/data/] [--refresh] [--only buildings|troops|spells|caps|all] [--cache-dir app/data/.wiki_cache]`.
- Hard-coded entity list per §9.7.
- Sources: `https://clashofclans.fandom.com/wiki/<EntityName>` for stats; `https://clashofclans.fandom.com/wiki/Troop_Movement_Speed` for tile-per-second movement.
- HTML cache at `app/data/.wiki_cache/<entity>.html` (gitignored) plus per-page `.metadata.json` with `{url, etag, last_modified, sha256, scraped_at}`.
- Defensive parsing per §9.6: missing fields → `null` + warning; never silent. The output validator catches required-field misses.
- Stat-name normalization per §9.5 (e.g., `Damage per Hit` ≡ `Damage per Shot` ≡ `Damage per Attack` → `damage_per_shot`; `Attack Speed (sec) → attack_cooldown_ticks` via `round(s × 10)`; `DPS` dropped).
- Output: `app/data/buildings.json`, `troops.json`, `spells.json`, `th_caps.json`. Pretty-printed, sorted keys, UTF-8.
- Each output validates against its Pydantic schema before writing.
- Reruns with the same cache produce byte-identical output.

Loader:

- `content.py` already merges scraped data; this issue adds the `manual_overrides.json` overlay merge per §9.4.
- Merge order: `wiki scrape → manual_overrides → final BuildingType / TroopType / SpellType objects`.
- Merge happens **once per sim startup**, not per tick.
- Commit a small example `app/data/manual_overrides.json` with at least the Army Camp `hitbox_inset: 1.0` override and the Wall Breaker `damage_multiplier_default` override.

After this issue, the hand-written 2-entity data files from issue 001 are replaced wholesale with scraped + overridden full TH6 content.

## Acceptance criteria

- [ ] `python -m sandbox_core.tools.scrape_wiki --out app/data/` produces all 4 JSONs without errors.
- [ ] All 17 buildings, 6 troops, and 1 spell scraped and validate against their schemas.
- [ ] `th_caps.json` covers TH1–TH6 entries for every entity.
- [ ] Reruns are byte-identical given the cache (deterministic).
- [ ] `--refresh` invalidates and re-fetches the cache; warnings logged for parsing fallbacks.
- [ ] `--only buildings` / `--only troops` etc. work as filters.
- [ ] `manual_overrides.json` example committed; loader merges correctly (unit test with synthetic override verifies the merge).
- [ ] After replacing hand-written data with scraped data, the `tracer_smoke.json` golden replay still passes (re-record with `pytest --update-golden` if intended changes).
- [ ] Stat-name normalizations covered by unit tests for each normalizer rule.

## Blocked by

- Blocked by `issues/open/001-sandbox-core-tracer.md`

## User stories addressed

- FR-S10, FR-S11 (overrides + per-level data).
- FR-C1, FR-C2, FR-C3, FR-C4, FR-C5.
- AC-S1.1.
