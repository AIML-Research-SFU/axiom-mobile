# AXIOM-Mobile Knowledge Graph (KG v1)

Last updated: 2026-07-31 (rebuilt against dataset v4)

## Status

**Populated, rebuilt against dataset v4.** Was blocked since Phase 1 — see
the "before" state this replaces at the bottom of this file. Built
programmatically from the dataset's own `notes`/`question`/`answer`
fields, the same zero-manual-labeling principle the auto-exact scenario
pipeline already uses for screenshots. No separate entity curation effort
was done or is needed; the KG is a derived artifact, regenerated from the
dataset, not hand-maintained. Rebuilding it is a single command
(`python3 ml/scripts/build_kg.py`) with no manual step, so it's re-run
after every dataset version rather than left stale — done here for the
v0.5.0 Safari/Contacts additions (Section 4.1 of `paper/PAPER_DRAFT_v5.md`).

## What's in it

| File | Contents |
|---|---|
| `kg/entities.json` | 264 entities: 11 App, 21 Screen, 20 Attribute, 212 AnswerValue |
| `kg/relations.json` | 1,087 relations across 4 predicate types |

**Honesty note on scale:** the original proposal guessed "~1000 entities"
before anyone had seen the real data. Dataset v3 (751 examples, 9 apps)
produced 235 entities; dataset v4 (797 examples, 11 apps -- Safari and
Contacts added) produces 264. Both are the real numbers, not padded ones
— see `docs/SPEC.md`'s original estimate for context, and treat it as
superseded by what the data actually contains.

### Entity types

- **App** (9): the distinct applications represented — Settings, Maps,
  Clock, Weather, Calculator, Control Center, App Store, Lock Screen,
  Status Bar.
- **Screen** (19): specific screens/sub-pages within an app — e.g.
  `Settings / Wi-Fi`, `Settings / Bluetooth`, `Clock / Alarm`,
  `Control Center / AirDrop`. Parsed from the dataset's `notes` field,
  which already encodes this consistently (e.g.
  `"iOS Clock app → Alarm"`, `"Settings main"`).
- **Attribute** (20): the semantic category a question asks about — time,
  battery_pct, charging, cellular_status, wifi_status,
  bluetooth_status, airplane_mode, apple_account, search_bar,
  temperature, calculator, maps, weather, clock, control_center,
  app_store, battery_settings, visual_detail, location, date,
  map_style, other. This is the *exact same* taxonomy
  `ml/scripts/freeze_dataset_v3.py` uses for stratified splitting — one
  taxonomy shared across the codebase, not two that could silently
  drift apart.
- **AnswerValue** (187): distinct normalized answers observed in the
  dataset (e.g. `"9:41"`, `"Yes"`, `"1"`, `"Apple Maps"`).

### Relation types

| Predicate | Meaning | Count |
|---|---|---|
| `has_screen` | App → Screen | 19 |
| `has_attribute` | Screen → Attribute (this attribute is askable on this screen) | 39 |
| `has_value` | Attribute → AnswerValue (observed value space) | 200 |
| `grounds_example` | Screen → dataset example id (traceability back to the row this fact came from) | 751 |

The `grounds_example` relation is what makes the KG usable for the
grounding check `docs/SPEC.md` describes ("answers must be grounded in
visible content or KG") — every fact traces back to a real dataset row,
not an assertion with no source.

## How it's used

**KG-guided selection strategy** (`ml/src/axiom/selection/kg_guided.py`):
selects training examples to maximize coverage of distinct
`(Screen, Attribute)` regions before depth within any one region —
round-robin across regions in a seeded-shuffled order. Measured directly:
at budget=25 on the current pool (37 distinct regions total), KG-guided
covers **25/37 regions** vs **11/37** for plain random sampling at the
same budget. This is the KG actually being used for something, not just
existing as a static file.

## Regenerating

```bash
python3 ml/scripts/build_kg.py            # writes kg/entities.json + kg/relations.json
python3 ml/scripts/build_kg.py --dry-run  # preview counts only
```

Do not hand-edit `entities.json` or `relations.json` — they're derived
from `data/manifests/*.jsonl` and will be silently overwritten the next
time the dataset changes and this script is re-run (same convention as
`scripts/capture_scenarios.json`).

## Extending

The extraction logic lives in `ml/src/axiom/kg/extract.py`:

- `parse_screen(notes)` — App/Screen extraction. Uses an explicit
  prefix-rule table for notes patterns without a reliable delimiter
  (e.g. `"iOS Bluetooth settings"` has no separator between app and
  screen), enumerated directly from what's actually in the manifests
  rather than guessed. If new scenario types are added to the capture
  pipeline with a new `notes` pattern, add a rule here — an unrecognized
  pattern falls back to treating the whole phrase as the app name rather
  than silently misclassifying it as a known one, so gaps are visible
  (check the App/Screen entity list after regenerating) instead of
  silent.
- `classify_attribute(question)` — reuses the same taxonomy as
  `freeze_dataset_v3.py`. If that taxonomy changes, update both (there's
  no shared import between a script and this library module — same
  duplication pattern already accepted between `freeze_dataset_v2.py`
  and `freeze_dataset_v3.py`).

---

## Before Phase 9 (historical, for reference)

This file was empty. `docs/TIMELINE.md` Phase 1 read:

    [ ] KG v1 (~1000 entities + API + app loader) not implemented yet.

KG-guided selection raised `NotImplementedError` on every call, and the
selection sweep runner recorded it as a skipped strategy. An "app loader"
(bundling the KG into the iOS app for on-device grounding checks) remains
unimplemented — see "Still open" below.

## Still open

- **App loader**: the KG isn't bundled into the iOS app yet. It's used
  offline (by the selection strategy and, potentially, paper-writing
  grounding checks) but not queryable on-device.
- **Query API**: no programmatic query interface beyond loading the JSON
  directly — fine for the current scale (235 entities), would need
  revisiting if the KG grows substantially (e.g. after further dataset
  scaling phases add new apps/screens).
