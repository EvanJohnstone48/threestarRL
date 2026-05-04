# Base Authoring Guide

Reference: `docs/sandbox/prd.md` §10.

---

## File naming and location

All bases live in `data/sample_bases/`. The validator enforces these exact naming patterns:

| File | Purpose |
|------|---------|
| `tracer.json` | Phase 0 smoke-test base — do not modify |
| `eval_01.json` – `eval_05.json` | Frozen held-out eval set |
| `base_01.json` – `base_30.json` | MVP-Real training set |

Names are stable after first commit. Never renumber.

---

## Required metadata fields

Every exported base must have all six fields populated before export:

```json
{
  "metadata": {
    "name": "eval_01",
    "th_level": 6,
    "tags": ["war-base", "compartmentalized"],
    "notes": "Asymmetric anti-3-star; TH tucked behind double compartment.",
    "author": "your-name",
    "created_at": "2026-05-04T12:00:00Z"
  }
}
```

- `name` — matches the filename without extension.
- `th_level` — always `6` in v1.
- `tags` — at least one style tag (see variety guidance below). Free-form chips in the editor UI.
- `notes` — one sentence describing the intent or distinctive feature.
- `author` — your name or handle.
- `created_at` — auto-populated by the editor; leave as-is.

There is no `difficulty` field. Curriculum sequencing is configured in barracks-land by enumerating filenames, not by reading metadata.

---

## Eval-first ordering rule

**Author all 5 eval bases before any training base.**

The eval set is the immutable measurement ruler for the entire project. Once committed, eval bases are never modified — not even cosmetically. If you spot a problem with an eval base after committing it, document the issue in a note rather than editing the file.

The training set (`base_01` – `base_30`) may be revised freely before the MVP-Real run begins.

No pre-commit hook enforces this in v1; the convention is upheld by discipline.

---

## Variety guidance

Avoid placing all buildings in one corner or clustering everything around the TH. Aim for layouts that represent real TH6 attack scenarios. The training set should cover four archetypes:

**Compound-TH** (~10 bases)
TH is centralized and well-defended. Defenses form a perimeter or concentric ring. Hard to reach the TH without clearing outer defenses first. Tags: `compound-th`, `centralized`.

**War-base** (~5 bases)
Asymmetric anti-3-star design. TH is tucked away or protected by compartments. Storages are exposed as bait. Designed to deny stars rather than protect resources. Tags: `war-base`, `anti-3-star`, `compartmentalized`.

**Farming-base** (~10 bases)
Defenses ring the interior; storages placed on the outer edge as sacrificial bait. TH may be exposed to protect resources. Tags: `farming-base`, `storage-protection`.

**Mixed / experimental** (~5 bases)
Box-style, anti-funnel, or other layouts that don't cleanly fit the above. Tags: `box-style`, `anti-funnel`, or describe the distinguishing feature.

For the eval set, use one base per archetype (compound-TH, war-base, farming-base) plus two additional varied layouts.

---

## Editor workflow tips

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| Click palette item | Enter place mode for that building |
| `Esc` | Cancel current mode |
| `W` | Wall-paint mode — click and drag to paint walls along an orthogonal line |
| `E` | Erase mode — click any building or wall to remove it |
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` or `Ctrl+Y` | Redo |

### Mass actions (toolbar)

**Mirror H / Mirror V** — reflects all placements across the vertical or horizontal center axis. Useful for building symmetric bases quickly: author one half, then mirror. The editor refuses the operation if the result violates any constraint (overlap, out-of-bounds) and shows an error toast.

**Rotate 90° CW** — rotates all placements clockwise around the grid center. Useful for producing rotational variants of a base without re-authoring from scratch. Same validation check applies.

**Clear all** — empties the placement list after a confirmation prompt. Undoable via `Ctrl+Z`.

### Recommended authoring flow for 30 training bases

1. Author 10–15 originals spanning all archetypes.
2. Use Mirror H or Rotate 90° CW to produce variants of your strongest layouts.
3. Tweak the variants (move a few buildings, adjust wall clusters) so they don't look identical.
4. Export each, run the CLI smoke check, then commit.

### Smoke-checking a base before committing

```bash
python -m sandbox_core.cli run \
  data/sample_bases/<base>.json \
  data/sample_plans/single_barb.json \
  --output /tmp/check.json
```

The command should exit 0 and produce a valid replay. A non-zero exit means the base failed validation or the sim crashed — fix before committing.
