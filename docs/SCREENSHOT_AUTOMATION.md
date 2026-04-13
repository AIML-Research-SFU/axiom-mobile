# Screenshot Automation

Simulator-based screenshot capture harness for scaling the AXIOM-Mobile dataset beyond the current 52 manually-collected examples.

## Why Simulator Automation

The dataset consists entirely of iOS system app screenshots (Settings, Weather, Calculator, Clock, Maps, App Store, Control Center). These apps are available on every iOS Simulator instance. Automating capture removes the manual bottleneck (screenshot → upload → manifest entry) and enables:

- **Deterministic status bar** via `xcrun simctl status_bar` (fixed time, battery, signal)
- **Repeatable scenarios** via deep links and XCUITest navigation
- **Batch generation** of 10–100+ screenshots per run
- **Pre-labeled candidates** with Q&A templates from scenario definitions

What is NOT automated:
- Final answer labeling (human review required)
- Quality validation (human review required)
- Promotion to frozen manifests (deliberate manual step)
- Control Center / Lock Screen captures (require physical interaction)

## Architecture

```
scripts/
  capture_screenshots.sh     — Shell orchestrator (simctl-based)
  capture_scenarios.json     — Scenario definitions (apps, deep links, Q&A templates)

app/AXIOMMobile/AXIOMMobileUITests/
  ScreenshotCaptureTests.swift — XCUITest for fine-grained UI navigation

ml/scripts/
  index_generated_screenshots.py — Creates candidate manifests from captures
```

### Two Capture Paths

| Path | Tool | Best For |
|------|------|----------|
| Shell script | `simctl launch` + `simctl io screenshot` | Quick batch captures, deep-link scenarios |
| XCUITest | `XCUIApplication(bundleIdentifier:)` + `XCUIScreen.main.screenshot()` | Navigating within apps (tap Settings rows, scroll) |

Both paths produce the same output format: PNG files + `capture_index.jsonl`.

## Quick Start

### Prerequisites

- Xcode CLI tools (`xcode-select --install`)
- `jq` (`brew install jq`)
- A booted iOS Simulator

### Shell Script (Recommended for First Run)

```bash
# Boot a simulator if none is running
xcrun simctl boot "iPhone 17 Pro"

# Run the capture harness
chmod +x scripts/capture_screenshots.sh
./scripts/capture_screenshots.sh

# Or with options
./scripts/capture_screenshots.sh \
  --device "iPhone 17 Pro" \
  --output ~/Datasets/axiom-mobile/batch_001 \
  --batch-id batch_001
```

### XCUITest

```bash
# Build and run capture tests
xcodebuild test \
  -project app/AXIOMMobile/AXIOMMobile.xcodeproj \
  -scheme AXIOMMobileUITests \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:AXIOMMobileUITests/ScreenshotCaptureTests

# Screenshots are saved to ~/Datasets/axiom-mobile/xctest_captures/
```

## Output Contract

### Screenshot Files

Generated PNGs are written to a local directory (default: `~/Datasets/axiom-mobile/generated_screenshots/`). These are **never committed to git**.

Naming: `gen_XXXX_<scenario_id>.png` (shell) or `<scenario_id>.png` (XCUITest)

### Capture Index (`capture_index.jsonl`)

One JSON object per captured screenshot:

```json
{
  "id": "gen_0001",
  "image_filename": "gen_0001_settings_main.png",
  "scenario_id": "settings_main",
  "screen_family": "settings",
  "description": "Settings app main screen",
  "notes": "iOS Settings main screen",
  "source": "simulator_generated",
  "device_name": "iPhone 17 Pro",
  "device_udid": "5C24F7D6-...",
  "batch_id": "batch_20260413_120000",
  "timestamp": "2026-04-13T12:00:00Z",
  "generator_version": "0.1.0",
  "app_bundle": "com.apple.Preferences",
  "deep_link": null,
  "qa_templates": [
    {"question": "Is Airplane Mode on or off?", "answer_hint": "Check toggle", "difficulty": 1}
  ],
  "file_size_bytes": 245760
}
```

## Status Bar Normalization

Before capture, the script applies a deterministic status bar via `xcrun simctl status_bar`:

| Property | Value |
|----------|-------|
| Time | 9:41 |
| Battery | 100%, charged |
| Wi-Fi | 3 bars |
| Cellular | 4 bars |
| Operator | "Carrier" |

This ensures status bar content is consistent across captures and doesn't leak real device state.

To clear: `xcrun simctl status_bar <UDID> clear`

## Scenario Definitions

Scenarios are defined in `scripts/capture_scenarios.json`. Each entry specifies:

| Field | Description |
|-------|-------------|
| `id` | Unique scenario identifier |
| `app_bundle` | Bundle ID of the app to launch |
| `deep_link` | Optional URL to open a specific screen |
| `wait_seconds` | Time to wait after launch before capture |
| `screen_family` | Category for grouping (settings, calculator, etc.) |
| `qa_templates` | Pre-defined question/answer pairs for this screen |

### Adding New Scenarios

1. Add an entry to `scripts/capture_scenarios.json`
2. Test with `--dry-run` to verify parsing
3. Run the capture to generate the screenshot
4. Review the output and refine the Q&A templates

For scenarios that require UI navigation (tapping rows, scrolling), add a test method to `ScreenshotCaptureTests.swift` instead.

## Review and Promotion Workflow

```
capture_screenshots.sh
        │
        ▼
~/Datasets/axiom-mobile/generated_screenshots/
  ├── gen_0001_settings_main.png
  ├── gen_0002_settings_wifi.png
  ├── ...
  └── capture_index.jsonl
        │
        ▼  (index + summarize)
python3 ml/scripts/index_generated_screenshots.py \
  --input ~/Datasets/axiom-mobile/generated_screenshots
        │
        ▼  (promote to staging)
python3 ml/scripts/index_generated_screenshots.py \
  --input ~/Datasets/axiom-mobile/generated_screenshots \
  --promote --start-id 53
        │
        ▼
data/manifests/generated_candidates.jsonl
        │
        ▼  (human review: fix answers, remove bad captures)
        │
        ▼  (move approved rows to pool.jsonl / val.jsonl / test.jsonl)
        │
        ▼  (copy approved PNGs to screenshots_v1/ in Drive)
        │
        ▼  (validate)
python3 ml/scripts/inspect_dataset.py
python3 ml/scripts/annotation_qc.py
```

### Review Checklist

For each generated candidate:
1. Open the PNG — does the screenshot show the expected screen?
2. Does the question make sense for this screenshot?
3. Is the answer exact and correct? (Replace `answer_hint` with the actual answer)
4. Remove the `_status`, `_source`, `_scenario_id` metadata fields
5. Ensure the `image_filename` matches the file in screenshots_v1/

### Promoting to Final Manifests

After review, manually move approved entries from `generated_candidates.jsonl` to the appropriate split manifest (`pool.jsonl`, `val.jsonl`, or `test.jsonl`). Only include the standard schema fields:

```json
{"id": "ex_053", "image_filename": "img_053.png", "question": "Is Bluetooth on or off?", "answer": "On", "difficulty": 1, "notes": "iOS Bluetooth settings"}
```

## Extending the Harness

### New System Apps

Add a scenario to `capture_scenarios.json` with the app's bundle ID. Find bundle IDs:
```bash
xcrun simctl listapps booted | grep CFBundleIdentifier
```

### Stateful Captures

For screenshots that require specific UI state (e.g., Bluetooth OFF):
1. Add an XCUITest method that navigates to the setting and toggles it
2. Capture after the state change
3. Include the expected state in the Q&A template

### Multiple Devices

Run the shell script with different `--device` flags to capture on iPhone, iPad, etc.:
```bash
./scripts/capture_screenshots.sh --device "iPhone 17 Pro" --batch-id iphone_batch
./scripts/capture_screenshots.sh --device "iPad Air 11-inch (M4)" --batch-id ipad_batch
```

### Battery/Time Variations

For dataset diversity, vary the status bar between batches:
```bash
xcrun simctl status_bar <UDID> override --batteryLevel 23 --time "11:30"
```
