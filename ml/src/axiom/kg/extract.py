"""Extract a compact knowledge graph from the dataset's own manifest fields.

Phase 9 (docs/TIMELINE.md Phase 1 item, carried forward): KG v1 was
originally scoped as "~1000 entities + API + app loader" to be curated
separately. Instead, this builds the KG *programmatically* from ground
truth the dataset already carries in `notes` and `question` -- no new
labeling, no separate curation effort, and the KG stays consistent with
the dataset by construction (regenerate by re-running the extraction, the
same principle `generate_exact_scenarios.py` already follows for
screenshots).

Entity types
------------
App        Top-level application (e.g. "Settings", "Maps", "Clock").
Screen     Specific screen/sub-page within an app (e.g. "main", "Wi-Fi",
           "Alarm"). Derived from the `notes` field, which already
           encodes this consistently (e.g. "iOS Clock app -> Alarm",
           "Settings main").
Attribute  The semantic category a question asks about (time,
           battery_pct, cellular_status, ...). Reuses the exact same
           question-type taxonomy as `freeze_dataset_v3.py`'s
           stratification, so "KG region" and "stratum" mean the same
           thing across the codebase -- not two competing taxonomies.
AnswerValue  A distinct normalized answer string observed for some
           attribute (e.g. "9:41", "Yes", "1").

Relation types
--------------
(App, "has_screen", Screen)
(Screen, "has_attribute", Attribute)   -- which attributes are askable
                                            on which screen
(Attribute, "has_value", AnswerValue)  -- the observed value space
(Screen, "grounds_example", example_id) -- traceability back to the
                                            dataset row that produced
                                            this fact, so grounding
                                            claims (SPEC.md's "answers
                                            must be grounded in visible
                                            content or KG") are checkable

Honesty note: the original proposal guessed "~1000 entities" before
anyone knew the real data shape. This module reports whatever the actual
dataset produces (see kg/README.md for the real count) rather than
padding to hit that number.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from axiom.eval import normalize_text

# Same question-type taxonomy as ml/scripts/freeze_dataset_v3.py's
# stratification, duplicated rather than imported (freeze_dataset_v3.py
# is a script, not an importable library module -- same duplication
# pattern the v2/v3 freeze scripts already use between each other).
_ATTRIBUTE_PATTERNS: list[tuple[str, str]] = [
    ("time", "time"),
    ("battery percentage", "battery_pct"),
    ("battery charging", "charging"),
    ("signed into", "apple_account"),
    ("search bar", "search_bar"),
    ("wi-fi", "wifi_status"),
    ("bluetooth", "bluetooth_status"),
    ("cellular", "cellular_status"),
    ("airplane", "airplane_mode"),
    ("temperature", "temperature"),
    ("lock screen", "lock_screen"),
    ("calculator", "calculator"),
    ("equation", "calculator"),
    ("map", "maps"),
    ("weather", "weather"),
    ("clock", "clock"),
    ("airdrop", "control_center"),
    ("app store", "app_store"),
    ("low power", "battery_settings"),
    ("color", "visual_detail"),
    ("city", "location"),
    ("date", "date"),
    ("visual mode", "map_style"),
]


def classify_attribute(question: str) -> str:
    """Assign an Attribute entity id based on question text."""
    q_lower = question.lower()
    for pattern, attribute in _ATTRIBUTE_PATTERNS:
        if pattern in q_lower:
            return attribute
    return "other"


# Explicit (prefix, App, Screen) rules for the notes patterns that don't
# have a reliable separator to parse generically (e.g. "iOS Bluetooth
# settings" has no delimiter between app and screen). Built directly by
# enumerating every distinct notes-field prefix actually present in
# data/manifests/*.jsonl (29 of them across 751 examples) rather than
# guessed -- ordered longest/most-specific prefix first so e.g. "Control
# Center AirDrop tile" matches before the generic "Control Center tile"
# fallback.
_KNOWN_PREFIX_RULES: list[tuple[str, str, str]] = [
    ("iOS Control Center connectivity panel", "Control Center", "Connectivity"),
    ("Control Center AirDrop tile", "Control Center", "AirDrop"),
    ("Control Center Wi-Fi tile", "Control Center", "Wi-Fi"),
    ("Control Center tile", "Control Center", "default"),
    ("iOS Control Center", "Control Center", "default"),
    ("iOS Apple Maps app", "Maps", "default view"),
    ("Maps default view", "Maps", "default view"),
    ("iOS Weather app", "Weather", "default"),
    ("Weather app header", "Weather", "default"),
    ("Weather app", "Weather", "default"),
    ("iOS Calculator app", "Calculator", "default"),
    ("Status bar battery", "Status Bar", "default"),
    ("iOS status bar", "Status Bar", "default"),
    ("Lock screen date", "Lock Screen", "default"),
    ("iOS lock screen", "Lock Screen", "default"),
    ("iOS Lock Screen", "Lock Screen", "default"),
    ("iOS Wi-Fi settings toggle", "Settings", "Wi-Fi"),
    ("iOS Wi-Fi settings", "Settings", "Wi-Fi"),
    ("iOS Bluetooth settings", "Settings", "Bluetooth"),
    ("iOS Cellular settings", "Settings", "Cellular"),
    ("iOS Airplane Mode settings", "Settings", "Airplane Mode"),
    ("iOS App Store", "App Store", "default"),
    ("Settings main", "Settings", "main"),
]


def parse_screen(notes: str) -> tuple[str, str]:
    """Split a `notes` field into (App, Screen) entities.

    Handles the actual patterns observed in the dataset (checked directly
    against data/manifests/*.jsonl, not assumed):
      "Settings main — iOS 26 layout..."   -> ("Settings", "main")
      "iOS Settings → Wi-Fi"               -> ("Settings", "Wi-Fi")
      "iOS Clock app → Alarm"              -> ("Clock", "Alarm")
      "iOS Bluetooth settings"             -> ("Settings", "Bluetooth")
      "Control Center AirDrop tile"        -> ("Control Center", "AirDrop")
      "Maps default view — status bar..."  -> ("Maps", "default view")
      ""  (missing/empty)                  -> ("Unknown", "unknown")
    """
    notes = (notes or "").strip()
    if not notes:
        return ("Unknown", "unknown")

    # Strip trailing " — ..." or " (..." commentary first.
    head = notes
    for sep in (" — ", " ("):
        if sep in head:
            head = head.split(sep, 1)[0]
            break
    head = head.strip()

    # "App -> Screen" hierarchy, when present -- covers "iOS Settings ->
    # Wi-Fi/Battery/Cellular" and "iOS Clock app -> Alarm/World Clock/
    # Stopwatch", all of which parse correctly via generic app-name
    # normalization.
    if "→" in head:
        app_part, screen_part = head.split("→", 1)
        app = _normalize_app_name(app_part.strip())
        screen = screen_part.strip()
        return (app, screen)

    for prefix, app, screen in _KNOWN_PREFIX_RULES:
        if head.startswith(prefix):
            return (app, screen)

    # Unrecognized pattern: fall back to treating the whole head as the
    # app name rather than silently misclassifying it as a known app.
    return (_normalize_app_name(head), "default")


def _normalize_app_name(raw: str) -> str:
    """Normalize app-name variants seen in notes to one canonical App id."""
    text = raw.strip()
    prefixes = ("iOS ", "Control Center ")
    for p in prefixes:
        if text.startswith(p) and text != p.strip():
            text = text[len(p):]
    text = text.replace(" app", "").strip()
    if text.lower() in ("control center", "airdrop", "wi-fi tile", "tile"):
        return "Control Center"
    if not text:
        return "Unknown"
    return text


def extract_kg(rows: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Extract (entities, relations) from a list of dataset manifest rows.

    Deterministic: same input rows always produce the same entity ids and
    relation list (sorted), so the KG can be regenerated and diffed like
    any other derived artifact.
    """
    entities: dict[str, dict[str, Any]] = {}
    relations: set[tuple[str, str, str]] = set()

    def _add_entity(entity_id: str, entity_type: str, label: str) -> None:
        if entity_id not in entities:
            entities[entity_id] = {"id": entity_id, "type": entity_type, "label": label}

    for row in rows:
        question = str(row.get("question", ""))
        answer = str(row.get("answer", ""))
        notes = str(row.get("notes", ""))
        example_id = str(row.get("id", ""))

        app, screen = parse_screen(notes)
        attribute = classify_attribute(question)
        answer_norm = normalize_text(answer)

        app_id = f"app:{app.lower().replace(' ', '_')}"
        screen_id = f"screen:{app.lower().replace(' ', '_')}:{screen.lower().replace(' ', '_')}"
        attribute_id = f"attr:{attribute}"
        answer_id = f"answer:{answer_norm.replace(' ', '_')[:60]}"

        _add_entity(app_id, "App", app)
        _add_entity(screen_id, "Screen", f"{app} / {screen}")
        _add_entity(attribute_id, "Attribute", attribute)
        _add_entity(answer_id, "AnswerValue", answer)

        relations.add((app_id, "has_screen", screen_id))
        relations.add((screen_id, "has_attribute", attribute_id))
        relations.add((attribute_id, "has_value", answer_id))
        if example_id:
            relations.add((screen_id, "grounds_example", f"example:{example_id}"))

    entity_list = sorted(entities.values(), key=lambda e: (e["type"], e["id"]))
    relation_list = [
        {"subject": s, "predicate": p, "object": o}
        for s, p, o in sorted(relations)
    ]
    return entity_list, relation_list


def region_of(row: dict[str, Any]) -> tuple[str, str]:
    """The (Screen, Attribute) KG region a dataset row belongs to.

    Used by KGGuidedSelector as its unit of "coverage" -- the same
    (App, Screen) parsing and Attribute classification used to build the
    committed kg/entities.json, so the strategy's notion of a KG region is
    identical to what's actually in the KG artifact, not a parallel
    approximation of it.
    """
    app, screen = parse_screen(str(row.get("notes", "")))
    attribute = classify_attribute(str(row.get("question", "")))
    return (f"{app}/{screen}", attribute)
