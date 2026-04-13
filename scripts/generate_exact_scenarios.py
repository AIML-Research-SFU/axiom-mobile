#!/usr/bin/env python3
"""Generate exact-answer scenario definitions for AXIOM-Mobile capture harness.

Outputs: scripts/capture_scenarios.json (v2 — exact answers, per-scenario status bar overrides)

Each scenario is deterministic: Q&A pairs have exact answers grounded in either:
  - Status bar state (time, battery%) — controlled via `xcrun simctl status_bar`
  - Visually verified screen content (Apple Account sign-in state, search bar text)

Only emits exact answers when the answer is visually verified on the captured screen.
Toggle questions (Airplane Mode, Wi-Fi, Bluetooth) are NOT emitted because iOS 26
relocated these to sub-pages not visible on the Settings main screen.

Usage:
    python3 scripts/generate_exact_scenarios.py
    python3 scripts/generate_exact_scenarios.py --dry-run   # print summary only
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# ── Status bar variant definitions ────────────────────────────────────
# (id, time, battery_level, battery_state)
# Chosen for visual diversity: different times-of-day, battery levels,
# and charging states to ensure the model learns to read actual content.

VARIANTS: list[tuple[str, str, int, str]] = [
    # ── Original 15 (v0.2.1) ─────────────────────────────────────────
    ("sb01", "9:41",  100, "charged"),
    ("sb02", "3:15",  46,  "discharging"),
    ("sb03", "11:30", 87,  "discharging"),
    ("sb04", "7:45",  23,  "discharging"),
    ("sb05", "12:00", 61,  "discharging"),
    ("sb06", "8:22",  8,   "discharging"),
    ("sb07", "5:47",  73,  "discharging"),
    ("sb08", "10:08", 55,  "charging"),
    ("sb09", "2:30",  34,  "discharging"),
    ("sb10", "6:15",  92,  "discharging"),
    ("sb11", "4:20",  15,  "charging"),
    ("sb12", "1:05",  67,  "discharging"),
    ("sb13", "9:15",  42,  "discharging"),
    ("sb14", "11:11", 78,  "discharging"),
    ("sb15", "7:00",  29,  "discharging"),
    # ── Extended batch (v0.3.0) ───────────────────────────────────────
    # More time-of-day variety, wider battery spread, additional states.
    ("sb16", "12:30", 3,   "discharging"),
    ("sb17", "8:00",  50,  "discharging"),
    ("sb18", "6:45",  97,  "charged"),
    ("sb19", "10:55", 11,  "discharging"),
    ("sb20", "1:30",  82,  "discharging"),
    ("sb21", "4:05",  38,  "discharging"),
    ("sb22", "9:00",  65,  "charging"),
    ("sb23", "11:45", 19,  "discharging"),
    ("sb24", "3:50",  88,  "discharging"),
    ("sb25", "7:20",  5,   "discharging"),
    ("sb26", "2:10",  71,  "discharging"),
    ("sb27", "5:30",  44,  "discharging"),
    ("sb28", "8:40",  95,  "charged"),
    ("sb29", "10:25", 26,  "discharging"),
    ("sb30", "12:15", 58,  "charging"),
    ("sb31", "6:00",  13,  "discharging"),
    ("sb32", "1:45",  76,  "discharging"),
    ("sb33", "9:30",  33,  "discharging"),
    ("sb34", "4:55",  90,  "discharging"),
    ("sb35", "11:05", 48,  "discharging"),
    ("sb36", "7:35",  7,   "discharging"),
    ("sb37", "3:00",  62,  "discharging"),
    ("sb38", "8:15",  84,  "discharging"),
    ("sb39", "10:40", 21,  "charging"),
    ("sb40", "5:10",  53,  "discharging"),
    ("sb41", "12:45", 99,  "charged"),
    ("sb42", "2:55",  17,  "discharging"),
    ("sb43", "6:30",  69,  "discharging"),
    ("sb44", "9:50",  40,  "discharging"),
    ("sb45", "11:20", 86,  "discharging"),
    ("sb46", "4:40",  2,   "discharging"),
    ("sb47", "7:55",  57,  "charging"),
    ("sb48", "1:15",  74,  "discharging"),
    ("sb49", "10:00", 31,  "discharging"),
    ("sb50", "3:35",  80,  "discharging"),
]

# How many variants to use for Maps (all variants in v0.3.0)
MAPS_VARIANT_COUNT = len(VARIANTS)

# ── Default status bar (applied when no per-scenario override) ────────
DEFAULT_STATUS_BAR = {
    "_doc": "Applied globally via `xcrun simctl status_bar` before capture begins.",
    "time": "9:41",
    "battery_state": "charged",
    "battery_level": 100,
    "wifi_bars": 3,
    "cellular_bars": 4,
    "cellular_mode": "active",
    "operator_name": "Carrier",
}


def _make_settings_scenario(
    var_id: str, time: str, battery: int, state: str
) -> dict:
    """Generate a Settings main screen scenario with exact answers.

    iOS 26 Settings main screen shows (verified by visual inspection):
      - Status bar: time, battery icon with percentage, charging indicator
      - Apple Account section: "Sign in to access your iCloud data..."
      - Categories: General, Accessibility, Action Button, etc.

    NOT visible on iOS 26 Settings main screen (moved to sub-pages):
      - Airplane Mode toggle
      - Wi-Fi toggle / status
      - Bluetooth toggle / status

    Only emits questions about content that is actually visible.
    """
    charging = "Yes" if state in ("charged", "charging") else "No"

    return {
        "id": f"settings_main_{var_id}",
        "app_bundle": "com.apple.Preferences",
        "deep_link": None,
        "wait_seconds": 3,
        "screen_family": "settings",
        "description": (
            f"Settings main — {var_id} "
            f"(time={time}, battery={battery}%, {state})"
        ),
        "status_bar_override": {
            "time": time,
            "battery_level": battery,
            "battery_state": state,
        },
        "qa_pairs": [
            {
                "question": "What time is shown?",
                "answer": time,
                "difficulty": 1,
            },
            {
                "question": "What battery percentage is shown?",
                "answer": f"{battery}%",
                "difficulty": 1,
            },
            {
                "question": "Is the battery charging?",
                "answer": charging,
                "difficulty": 1,
            },
            {
                "question": "Is the user signed into Apple Account?",
                "answer": "No",
                "difficulty": 1,
            },
        ],
        "notes": (
            f"Settings main — iOS 26 layout, "
            f"status bar {var_id}"
        ),
    }


def _make_maps_scenario(
    var_id: str, time: str, battery: int, state: str
) -> dict:
    """Generate a Maps default view scenario with exact answers.

    Maps default view shows (verified by visual inspection):
      - Status bar: time, battery icon with percentage, charging indicator
      - "Apple Maps" search bar placeholder text
      - Map view centered on North America (3D globe)
      - "Places >" section with Home, Work, Add

    Only status-bar-controlled and visually verified answers are emitted.
    """
    charging = "Yes" if state in ("charged", "charging") else "No"

    return {
        "id": f"maps_default_{var_id}",
        "app_bundle": "com.apple.Maps",
        "deep_link": None,
        "wait_seconds": 4,
        "screen_family": "maps",
        "description": (
            f"Maps default — {var_id} "
            f"(time={time}, battery={battery}%, {state})"
        ),
        "status_bar_override": {
            "time": time,
            "battery_level": battery,
            "battery_state": state,
        },
        "qa_pairs": [
            {
                "question": "What time is shown?",
                "answer": time,
                "difficulty": 1,
            },
            {
                "question": "What battery percentage is shown?",
                "answer": f"{battery}%",
                "difficulty": 1,
            },
            {
                "question": "Is the battery charging?",
                "answer": charging,
                "difficulty": 1,
            },
            {
                "question": "What text is shown in the search bar?",
                "answer": "Apple Maps",
                "difficulty": 1,
            },
        ],
        "notes": f"Maps default view — status bar {var_id}",
    }


def generate() -> dict:
    """Generate the full scenarios dictionary."""
    scenarios: list[dict] = []

    # Settings main with all variants
    for var_id, time, battery, state in VARIANTS:
        scenarios.append(_make_settings_scenario(var_id, time, battery, state))

    # Maps with first N variants
    for var_id, time, battery, state in VARIANTS[:MAPS_VARIANT_COUNT]:
        scenarios.append(_make_maps_scenario(var_id, time, battery, state))

    total_qa = sum(len(s["qa_pairs"]) for s in scenarios)

    return {
        "_version": "0.3.0",
        "_description": (
            "Exact-answer scenario definitions for deterministic dataset "
            "generation (v0.3.0 — 50 status bar variants, full Maps coverage). "
            "Generated by scripts/generate_exact_scenarios.py. "
            "All answers visually verified against iOS 26 simulator output. "
            "Do not edit by hand — regenerate instead."
        ),
        "_total_scenarios": len(scenarios),
        "_total_qa_pairs": total_qa,
        "_visual_verification_note": (
            "iOS 26 Settings main screen does NOT show Airplane Mode, "
            "Wi-Fi, or Bluetooth toggles (moved to sub-pages). "
            "Only status bar content, Apple Account state, and Maps "
            "search bar text are used as exact answers."
        ),
        "default_status_bar": DEFAULT_STATUS_BAR,
        "scenarios": scenarios,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate exact-answer capture scenarios"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary without writing files",
    )
    args = parser.parse_args()

    data = generate()

    settings_count = sum(
        1 for s in data["scenarios"] if s["screen_family"] == "settings"
    )
    maps_count = sum(
        1 for s in data["scenarios"] if s["screen_family"] == "maps"
    )

    print(f"Scenario generation summary")
    print(f"{'=' * 50}")
    print(f"  Total scenarios: {data['_total_scenarios']}")
    print(f"    Settings main: {settings_count}")
    print(f"    Maps default:  {maps_count}")
    print(f"  Total QA pairs:  {data['_total_qa_pairs']}")
    print(f"    Per Settings:  4 (time, battery%, charging, signed-in)")
    print(f"    Per Maps:      4 (time, battery%, charging, search bar text)")
    print(f"  All answers:     exact (visually verified)")
    print()

    if args.dry_run:
        print("[dry-run] No files written.")
        print()
        print("Sample scenario:")
        print(json.dumps(data["scenarios"][0], indent=2))
        return

    output_path = SCRIPT_DIR / "capture_scenarios.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"Output: {output_path}")
    print(f"  File size: {output_path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
