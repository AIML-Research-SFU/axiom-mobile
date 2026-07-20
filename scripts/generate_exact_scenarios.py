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

# ── v0.4.0 delta: cellular-signal-bars variants ───────────────────────
# (id, time, battery_level, battery_state, cellular_bars)
#
# Visually confirmed on iPhone 17 Pro / iOS 26.4 simulator: `--cellularBars`
# renders a distinguishable filled-bar-count icon (1 bar vs 4 bars is
# unambiguous at a glance). `--wifiBars` and `--operatorName` were checked
# the same way and rejected: the wifi icon does not render a visually
# distinguishable bar count at this resolution, and the carrier-name text
# is not shown at all on this device (covered by the Dynamic Island area),
# so neither is a visually-verifiable exact answer. Only cellular_bars is
# added here, per the "only emit exact answers when visually verified"
# rule this generator already follows for everything else.
NEW_VARIANTS: list[tuple[str, str, int, str, int]] = [
    ("sb51", "6:20",  55,  "discharging", 1),
    ("sb52", "9:05",  88,  "discharging", 2),
    ("sb53", "2:40",  12,  "discharging", 3),
    ("sb54", "11:55", 100, "charged",     4),
    ("sb55", "4:15",  67,  "discharging", 1),
    ("sb56", "7:30",  45,  "charging",    2),
    ("sb57", "1:50",  93,  "discharging", 3),
    ("sb58", "10:10", 28,  "discharging", 4),
    ("sb59", "5:25",  71,  "discharging", 1),
    ("sb60", "8:45",  39,  "discharging", 2),
    ("sb61", "12:05", 84,  "discharging", 3),
    ("sb62", "3:20",  16,  "discharging", 4),
    ("sb63", "6:55",  60,  "charging",    1),
    ("sb64", "9:40",  95,  "charged",     2),
    ("sb65", "2:15",  24,  "discharging", 3),
    ("sb66", "11:00", 77,  "discharging", 4),
    ("sb67", "4:50",  9,   "discharging", 1),
    ("sb68", "7:05",  52,  "discharging", 2),
    ("sb69", "1:20",  63,  "discharging", 3),
    ("sb70", "10:35", 91,  "discharging", 4),
    ("sb71", "5:00",  18,  "discharging", 1),
    ("sb72", "8:20",  47,  "charging",    2),
    ("sb73", "12:40", 100, "charged",     3),
    ("sb74", "3:05",  35,  "discharging", 4),
    ("sb75", "6:10",  79,  "discharging", 1),
    ("sb76", "9:25",  6,   "discharging", 2),
    ("sb77", "2:45",  58,  "discharging", 3),
    ("sb78", "11:35", 83,  "discharging", 4),
    ("sb79", "4:30",  41,  "discharging", 1),
    ("sb80", "7:50",  96,  "charged",     2),
]

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
    var_id: str, time: str, battery: int, state: str, cellular_bars: int | None = None
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

    `cellular_bars`, when provided (v0.4.0 delta), sets the cellular signal
    icon via `--cellularBars` and adds a matching exact-answer question.
    Visually confirmed distinguishable (1 vs 4 bars); wifi_bars and
    operator_name were checked the same way and are not used because they
    are not reliably readable on this device's status bar.
    """
    charging = "Yes" if state in ("charged", "charging") else "No"

    status_bar_override = {
        "time": time,
        "battery_level": battery,
        "battery_state": state,
    }
    qa_pairs = [
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
    ]
    if cellular_bars is not None:
        status_bar_override["cellular_bars"] = cellular_bars
        qa_pairs.append({
            "question": "How many cellular signal bars are shown?",
            "answer": str(cellular_bars),
            "difficulty": 2,
        })

    return {
        "id": f"settings_main_{var_id}",
        "app_bundle": "com.apple.Preferences",
        "deep_link": None,
        "wait_seconds": 3,
        "screen_family": "settings",
        "description": (
            f"Settings main — {var_id} "
            f"(time={time}, battery={battery}%, {state}"
            + (f", cellular_bars={cellular_bars}" if cellular_bars is not None else "")
            + ")"
        ),
        "status_bar_override": status_bar_override,
        "qa_pairs": qa_pairs,
        "notes": (
            f"Settings main — iOS 26 layout, "
            f"status bar {var_id}"
        ),
    }


def _make_maps_scenario(
    var_id: str, time: str, battery: int, state: str, cellular_bars: int | None = None
) -> dict:
    """Generate a Maps default view scenario with exact answers.

    Maps default view shows (verified by visual inspection):
      - Status bar: time, battery icon with percentage, charging indicator
      - "Apple Maps" search bar placeholder text
      - Map view centered on North America (3D globe)
      - "Places >" section with Home, Work, Add

    Only status-bar-controlled and visually verified answers are emitted.

    `cellular_bars`, when provided (v0.4.0 delta), mirrors the Settings
    scenario: visually confirmed distinguishable signal-bar icon.
    """
    charging = "Yes" if state in ("charged", "charging") else "No"

    status_bar_override = {
        "time": time,
        "battery_level": battery,
        "battery_state": state,
    }
    qa_pairs = [
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
    ]
    if cellular_bars is not None:
        status_bar_override["cellular_bars"] = cellular_bars
        qa_pairs.append({
            "question": "How many cellular signal bars are shown?",
            "answer": str(cellular_bars),
            "difficulty": 2,
        })

    return {
        "id": f"maps_default_{var_id}",
        "app_bundle": "com.apple.Maps",
        "deep_link": None,
        "wait_seconds": 4,
        "screen_family": "maps",
        "description": (
            f"Maps default — {var_id} "
            f"(time={time}, battery={battery}%, {state}"
            + (f", cellular_bars={cellular_bars}" if cellular_bars is not None else "")
            + ")"
        ),
        "status_bar_override": status_bar_override,
        "qa_pairs": qa_pairs,
        "notes": f"Maps default view — status bar {var_id}",
    }


def _base_scenarios() -> list[dict]:
    """The original v0.3.0 scenario set (50 variants x 2 apps, 4 QA each).

    Already captured and promoted into pool.jsonl as batch
    `exact_v3_batch001`. Kept unchanged so re-running the generator does
    not silently alter previously-promoted scenario definitions.
    """
    scenarios: list[dict] = []
    for var_id, time, battery, state in VARIANTS:
        scenarios.append(_make_settings_scenario(var_id, time, battery, state))
    for var_id, time, battery, state in VARIANTS[:MAPS_VARIANT_COUNT]:
        scenarios.append(_make_maps_scenario(var_id, time, battery, state))
    return scenarios


def _delta_scenarios() -> list[dict]:
    """The v0.4.0 delta: 30 new variants x 2 apps, 5 QA each (adds
    cellular_bars). Not yet captured or promoted — this is the set that
    should be passed to capture_screenshots.sh via --scenarios so the
    already-promoted base set is not re-captured/re-promoted as
    duplicates.
    """
    scenarios: list[dict] = []
    for var_id, time, battery, state, cellular_bars in NEW_VARIANTS:
        scenarios.append(
            _make_settings_scenario(var_id, time, battery, state, cellular_bars)
        )
    for var_id, time, battery, state, cellular_bars in NEW_VARIANTS:
        scenarios.append(
            _make_maps_scenario(var_id, time, battery, state, cellular_bars)
        )
    return scenarios


def generate(delta_only: bool = False) -> dict:
    """Generate the scenarios dictionary.

    delta_only=False (default): full canonical set (base + delta) — for
        documentation/reference. Do NOT capture this wholesale; it
        includes the already-promoted base scenarios.
    delta_only=True: only the new v0.4.0 scenarios — this is what
        capture_screenshots.sh should actually be pointed at.
    """
    scenarios = _delta_scenarios() if delta_only else (_base_scenarios() + _delta_scenarios())
    total_qa = sum(len(s["qa_pairs"]) for s in scenarios)

    if delta_only:
        description = (
            "v0.4.0 DELTA — new scenarios only (30 status bar/cellular-bars "
            "variants x 2 apps, 5 QA pairs each, adds 'How many cellular "
            "signal bars are shown?'). Generated by "
            "scripts/generate_exact_scenarios.py --delta-only. Pass this "
            "file to capture_screenshots.sh --scenarios so the already-"
            "promoted v0.3.0 base scenarios are not re-captured. "
            "Do not edit by hand — regenerate instead."
        )
    else:
        description = (
            "Full canonical scenario definitions, v0.3.0 base (50 status "
            "bar variants) + v0.4.0 delta (30 cellular_bars variants), "
            "full Maps coverage. Generated by "
            "scripts/generate_exact_scenarios.py. Reference only — the "
            "base scenarios here are already captured/promoted; use "
            "--delta-only output to capture just the new ones. "
            "All answers visually verified against iOS 26 simulator "
            "output. Do not edit by hand — regenerate instead."
        )

    return {
        "_version": "0.4.0-delta" if delta_only else "0.4.0",
        "_description": description,
        "_total_scenarios": len(scenarios),
        "_total_qa_pairs": total_qa,
        "_visual_verification_note": (
            "iOS 26 Settings main screen does NOT show Airplane Mode, "
            "Wi-Fi, or Bluetooth toggles (moved to sub-pages). Wifi signal "
            "bars and carrier name were checked and are not reliably "
            "readable on this device's status bar, so they are not used "
            "as exact answers. Only status bar time/battery/charging, "
            "cellular signal bars, Apple Account state, and Maps search "
            "bar text are used as exact answers."
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
    parser.add_argument(
        "--delta-only",
        action="store_true",
        help=(
            "Write only the new v0.4.0 scenarios to "
            "capture_scenarios_v04_delta.json, instead of the full "
            "canonical set. Use this file with capture_screenshots.sh "
            "to avoid re-capturing/re-promoting the already-promoted "
            "v0.3.0 base scenarios."
        ),
    )
    args = parser.parse_args()

    data = generate(delta_only=args.delta_only)

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
    if args.delta_only:
        print(f"    Per Settings:  5 (time, battery%, charging, signed-in, cellular bars)")
        print(f"    Per Maps:      5 (time, battery%, charging, search bar text, cellular bars)")
    else:
        print(f"    Per Settings:  4 or 5 (base scenarios lack cellular bars)")
        print(f"    Per Maps:      4 or 5 (base scenarios lack cellular bars)")
    print(f"  All answers:     exact (visually verified)")
    print()

    if args.dry_run:
        print("[dry-run] No files written.")
        print()
        print("Sample scenario:")
        print(json.dumps(data["scenarios"][0], indent=2))
        return

    filename = "capture_scenarios_v04_delta.json" if args.delta_only else "capture_scenarios.json"
    output_path = SCRIPT_DIR / filename
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"Output: {output_path}")
    print(f"  File size: {output_path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
