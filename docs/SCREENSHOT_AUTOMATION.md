# Screenshot Automation

Simulator-based screenshot capture harness for scaling the AXIOM-Mobile dataset beyond manually-collected examples.

## Current Status

- **Dataset v2**: 452 total examples (pool=382, val=30, test=40) — deterministic freeze with stratified splits
- **Auto-generated**: 400 exact-answer examples from 100 screenshots (batch `exact_v3_batch001`)
- **Manual examples**: 52 original hand-labeled entries preserved from v1
- **Available apps on iOS 26 simulator**: Settings, Maps only (Calculator, Clock, Weather, App Store not installed)
- **Exact-answer coverage**: status bar (time, battery%), charging indicator, Apple Account state, Maps search bar text
- **Status bar variants**: 50 unique time/battery/state combinations for visual diversity
- **iOS 26 note**: Settings main screen no longer shows Airplane Mode, Wi-Fi, or Bluetooth toggles (moved to sub-pages)
- **Dataset versioning**: v1 manifests archived in `data/manifests/v1/` with SHA256 fingerprints

## Why Simulator Automation

The dataset consists of iOS system app screenshots. Automating capture removes the manual bottleneck and enables:

- **Deterministic status bar** via `xcrun simctl status_bar` (fixed time, battery, signal)
- **Repeatable scenarios** with exact answers where state is controlled
- **Batch generation** of 100 screenshots per run with 400 QA pairs (50 status bar variants x 2 apps)
- **Auto-promotion** of deterministic entries directly to pool.jsonl
- **Dataset versioning** with SHA256 fingerprints and archived prior splits

What is NOT automated:
- Final answer labeling for non-deterministic content (human review required)
- Quality validation for ambiguous screenshots (human review required)
- Promotion to val/test splits (deliberate manual step)

## Architecture

```
scripts/
  generate_exact_scenarios.py  — Scenario generator (status bar variants × app screens)
  capture_scenarios.json       — Generated scenario definitions (do not edit by hand)
  capture_screenshots.sh       — Shell orchestrator (simctl-based, v0.2.0)

app/AXIOMMobile/AXIOMMobileUITests/
  ScreenshotCaptureTests.swift — XCUITest for fine-grained UI navigation

ml/scripts/
  index_generated_screenshots.py — Indexes, promotes, and auto-promotes candidates
```

### Two Capture Paths

| Path | Tool | Best For |
|------|------|----------|
| Shell script | `simctl launch` + `simctl io screenshot` | Batch captures with status bar variants |
| XCUITest | `XCUIApplication(bundleIdentifier:)` + `XCUIScreen.main.screenshot()` | Navigating within apps (tap rows, scroll, toggle) |

Both paths produce the same output format: PNG files + `capture_index.jsonl`.

## Exact-Answer System (v0.2.1)

### How It Works

The scenario generator (`generate_exact_scenarios.py`) produces scenarios where **every Q&A pair has an exact answer** grounded in deterministic state:

| Answer Source | Example Question | How Answer Is Known |
|---------------|-----------------|---------------------|
| Status bar time | "What time is shown?" | Set by `simctl status_bar --time` |
| Status bar battery | "What battery percentage is shown?" | Set by `simctl status_bar --batteryLevel` |
| Battery state indicator | "Is the battery charging?" | Set by `simctl status_bar --batteryState` |
| Simulator state | "Is the user signed into Apple Account?" | Fresh sim = not signed in |
| App default | "What text is shown in the search bar?" | Maps always shows "Apple Maps" |

### Label Status Classification

| Status | Meaning | Promotion Path |
|--------|---------|---------------|
| `auto_exact` | Answer is deterministic and visually verified | Auto-promoted to pool.jsonl |
| `needs_review` | Answer hint provided, needs human verification | Stays in generated_candidates.jsonl |
| `needs_labeling` | No answer provided | Stays in generated_candidates.jsonl |

### What Is NOT Auto-Exact

- Toggle states (Airplane Mode, Wi-Fi, Bluetooth) unless the test explicitly sets them
- Dynamic content (weather, live map data, network names)
- Content that requires scrolling to verify

## Quick Start

### Prerequisites

- Xcode CLI tools (`xcode-select --install`)
- `jq` (`brew install jq`)
- A booted iOS Simulator

### Full Pipeline (Recommended)

```bash
# 1. Generate scenarios with exact answers
python3 scripts/generate_exact_scenarios.py

# 2. Boot a simulator if none is running
xcrun simctl boot "iPhone 17 Pro"

# 3. Run the capture harness
./scripts/capture_screenshots.sh --batch-id my_batch

# 4. Preview candidates (dry run)
python3 ml/scripts/index_generated_screenshots.py \
  --input ~/Datasets/axiom-mobile/generated_screenshots \
  --promote --start-id 53 --dry-run

# 5. Auto-promote exact entries to pool.jsonl
python3 ml/scripts/index_generated_screenshots.py \
  --input ~/Datasets/axiom-mobile/generated_screenshots \
  --promote --start-id 53 --auto-promote

# 6. Validate
python3 ml/scripts/inspect_dataset.py
python3 ml/scripts/annotation_qc.py
```

### Shell Script Options

```bash
./scripts/capture_screenshots.sh \
  --device "iPhone 17 Pro" \
  --output ~/Datasets/axiom-mobile/batch_001 \
  --batch-id batch_001 \
  --scenarios scripts/capture_scenarios.json \
  --dry-run
```

### XCUITest

```bash
xcodebuild test \
  -project app/AXIOMMobile/AXIOMMobile.xcodeproj \
  -scheme AXIOMMobileUITests \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:AXIOMMobileUITests/ScreenshotCaptureTests
```

## Output Contract

### Screenshot Files

Generated PNGs are written to a local directory (default: `~/Datasets/axiom-mobile/generated_screenshots/`). These are **never committed to git**.

Naming: `gen_XXXX_<scenario_id>.png`

### Capture Index (`capture_index.jsonl`)

One JSON object per captured screenshot:

```json
{
  "id": "gen_0001",
  "image_filename": "gen_0001_settings_main_sb01.png",
  "scenario_id": "settings_main_sb01",
  "screen_family": "settings",
  "description": "Settings main — sb01 (time=9:41, battery=100%, charged)",
  "notes": "Settings main — iOS 26 layout, status bar sb01",
  "source": "simulator_generated",
  "device_name": "iPhone 17 Pro",
  "device_udid": "5C24F7D6-...",
  "batch_id": "exact_v2_batch002",
  "timestamp": "2026-04-13T12:00:00Z",
  "generator_version": "0.2.0",
  "app_bundle": "com.apple.Preferences",
  "qa_pairs": [
    {"question": "What time is shown?", "answer": "9:41", "difficulty": 1},
    {"question": "What battery percentage is shown?", "answer": "100%", "difficulty": 1},
    {"question": "Is the battery charging?", "answer": "Yes", "difficulty": 1},
    {"question": "Is the user signed into Apple Account?", "answer": "No", "difficulty": 1}
  ],
  "status_bar_override": {"time": "9:41", "battery_level": 100, "battery_state": "charged"},
  "file_size_bytes": 383635
}
```

### Promotion Artifacts

After `--auto-promote`, the indexer writes:

| File | Contents |
|------|----------|
| `data/manifests/generated_candidates.jsonl` | All candidates with `_status` metadata |
| `data/manifests/rename_map.json` | Screenshot rename mapping (gen_XXXX → img_NNN) |
| `data/manifests/pool.jsonl` | Auto_exact entries appended (manifest-ready) |

## Status Bar Normalization

Before each scenario, the script applies a deterministic status bar via `xcrun simctl status_bar`:

Per-scenario overrides are supported (v0.2.0+). The generator creates 15 status bar variants with different times and battery levels for visual diversity.

To clear: `xcrun simctl status_bar <UDID> clear`

## Scenario Generation

Scenarios are generated by `scripts/generate_exact_scenarios.py` (not hand-written):

```bash
python3 scripts/generate_exact_scenarios.py          # generate
python3 scripts/generate_exact_scenarios.py --dry-run # preview
```

Current scenario set (v0.3.0):
- **50 Settings main variants** x 4 QA pairs = 200 exact entries
- **50 Maps default variants** x 4 QA pairs = 200 exact entries
- **Total: 400 exact QA pairs from 100 screenshots**

Previous scenario set (v0.2.1):
- 15 Settings main variants x 4 QA pairs = 60 exact entries
- 5 Maps default variants x 3 QA pairs = 15 exact entries
- Total: 75 exact QA pairs from 20 screenshots

### Adding New Scenarios

To add new scenario types, modify `generate_exact_scenarios.py`:

1. Add a new `_make_<app>_scenario()` function
2. Add scenarios to the `generate()` function
3. Run `python3 scripts/generate_exact_scenarios.py` to regenerate
4. Test with `--dry-run` on the shell script
5. Capture and verify visually before promoting

## Review and Promotion Workflow

```
generate_exact_scenarios.py
        │
        ▼
capture_scenarios.json (generated — do not hand-edit)
        │
        ▼
capture_screenshots.sh
        │
        ▼
~/Datasets/axiom-mobile/generated_screenshots/
  ├── gen_0001_settings_main_sb01.png
  ├── gen_0002_settings_main_sb02.png
  ├── ...
  └── capture_index.jsonl
        │
        ▼  (index + auto-promote)
python3 ml/scripts/index_generated_screenshots.py \
  --input ~/Datasets/axiom-mobile/generated_screenshots \
  --promote --start-id 53 --auto-promote
        │
        ├── auto_exact entries → pool.jsonl (appended)
        ├── rename_map.json (gen_XXXX → img_NNN mapping)
        └── generated_candidates.jsonl (full staging manifest)
        │
        ▼  (copy screenshots to Drive)
        │   Use rename_map.json to copy gen_XXXX.png → img_NNN.png
        │   into screenshots_v1/ in Drive
        │
        ▼  (validate)
python3 ml/scripts/inspect_dataset.py
python3 ml/scripts/annotation_qc.py
```

### What Remains Manual

1. **Visual spot-check**: verify a sample of auto-promoted screenshots look correct
2. **Screenshot file copies**: copy PNGs to Drive using rename_map.json
3. **Val/test promotion**: auto-promote only targets pool.jsonl; moving entries to val/test is manual
4. **Non-deterministic scenarios**: any scenario where the answer isn't controlled requires human review

## Extending the Harness

### iOS 26 Settings Layout

iOS 26 reorganized the Settings main screen. Connectivity settings (Wi-Fi, Bluetooth, Airplane Mode, Cellular) are no longer visible on the main screen. To capture these:

1. Use XCUITest to navigate to specific sub-pages
2. Add test methods that tap the relevant rows
3. Emit exact answers based on what the test navigated to

### New System Apps

If new apps become available on the simulator runtime:

```bash
# Check available apps
for bundle in com.apple.calculator com.apple.mobiletimer com.apple.weather; do
    xcrun simctl launch booted "$bundle" 2>&1 | head -1
done
```

### Multiple Devices

```bash
./scripts/capture_screenshots.sh --device "iPhone 17 Pro" --batch-id iphone_batch
./scripts/capture_screenshots.sh --device "iPad Air 11-inch (M4)" --batch-id ipad_batch
```

## Limitations

- **iOS 26 simulator**: Only Settings and Maps are available (Calculator, Clock, Weather, App Store not installed)
- **Deep links**: `App-prefs:` URLs do not navigate to sub-pages on iOS 26 — all open Settings main
- **First-launch artifacts**: Maps may show location permission dialog on first launch; script pre-grants permission
- **Status bar warnings**: Some `simctl status_bar` calls emit `[warn]` on iOS 26 runtime but still apply correctly
