#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# AXIOM-Mobile — Simulator Screenshot Capture Harness
#
# Usage:
#   ./scripts/capture_screenshots.sh                     # default: booted device
#   ./scripts/capture_screenshots.sh --device "iPhone 17 Pro"
#   ./scripts/capture_screenshots.sh --output ~/Datasets/axiom-mobile/batch_001
#   ./scripts/capture_screenshots.sh --scenarios scripts/capture_scenarios.json
#
# Requires: Xcode CLI tools, jq, a booted iOS Simulator
#
# Outputs to {output_dir}/:
#   gen_XXXX.png        — captured screenshots
#   capture_index.jsonl — one JSON object per capture with full metadata
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCENARIOS_FILE="$REPO_ROOT/scripts/capture_scenarios.json"
OUTPUT_DIR="$HOME/Datasets/axiom-mobile/generated_screenshots"
DEVICE_NAME=""
DEVICE_UDID=""
BATCH_ID=""
DRY_RUN=false

# ── Parse Arguments ───────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --device)     DEVICE_NAME="$2"; shift 2 ;;
        --output)     OUTPUT_DIR="$2"; shift 2 ;;
        --scenarios)  SCENARIOS_FILE="$2"; shift 2 ;;
        --batch-id)   BATCH_ID="$2"; shift 2 ;;
        --dry-run)    DRY_RUN=true; shift ;;
        -h|--help)
            echo "Usage: $0 [--device NAME] [--output DIR] [--scenarios FILE] [--batch-id ID] [--dry-run]"
            exit 0
            ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

# ── Validate Dependencies ─────────────────────────────────────────────
for cmd in xcrun jq; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: Required command '$cmd' not found."
        echo "  Install jq: brew install jq"
        exit 1
    fi
done

# ── Resolve Simulator ─────────────────────────────────────────────────
resolve_device() {
    if [[ -n "$DEVICE_NAME" ]]; then
        # Find UDID for named device
        DEVICE_UDID=$(xcrun simctl list devices available -j \
            | jq -r --arg name "$DEVICE_NAME" \
              '[.devices[][] | select(.name == $name and .state == "Booted")] | first | .udid // empty')

        if [[ -z "$DEVICE_UDID" ]]; then
            echo "Device '$DEVICE_NAME' is not booted. Attempting to boot..."
            DEVICE_UDID=$(xcrun simctl list devices available -j \
                | jq -r --arg name "$DEVICE_NAME" \
                  '[.devices[][] | select(.name == $name)] | first | .udid // empty')
            if [[ -z "$DEVICE_UDID" ]]; then
                echo "ERROR: No simulator found with name '$DEVICE_NAME'."
                echo "Available devices:"
                xcrun simctl list devices available | grep -E "^\s+(iPhone|iPad)"
                exit 1
            fi
            xcrun simctl boot "$DEVICE_UDID" 2>/dev/null || true
            echo "Booted $DEVICE_NAME ($DEVICE_UDID). Waiting for startup..."
            sleep 5
        fi
    else
        # Use the currently booted device
        DEVICE_UDID=$(xcrun simctl list devices booted -j \
            | jq -r '[.devices[][] | select(.state == "Booted")] | first | .udid // empty')

        if [[ -z "$DEVICE_UDID" ]]; then
            echo "ERROR: No simulator is currently booted."
            echo "Boot one with: xcrun simctl boot <UDID>"
            echo "Available devices:"
            xcrun simctl list devices available | grep -E "^\s+(iPhone|iPad)"
            exit 1
        fi

        DEVICE_NAME=$(xcrun simctl list devices booted -j \
            | jq -r '[.devices[][] | select(.state == "Booted")] | first | .name // "Unknown"')
    fi

    echo "Using simulator: $DEVICE_NAME ($DEVICE_UDID)"
}

# ── Status Bar Override ───────────────────────────────────────────────
apply_status_bar() {
    local time battery_level battery_state wifi_bars cellular_bars operator_name

    time=$(jq -r '.status_bar.time' "$SCENARIOS_FILE")
    battery_level=$(jq -r '.status_bar.battery_level' "$SCENARIOS_FILE")
    battery_state=$(jq -r '.status_bar.battery_state' "$SCENARIOS_FILE")
    wifi_bars=$(jq -r '.status_bar.wifi_bars' "$SCENARIOS_FILE")
    cellular_bars=$(jq -r '.status_bar.cellular_bars' "$SCENARIOS_FILE")
    operator_name=$(jq -r '.status_bar.operator_name' "$SCENARIOS_FILE")

    echo "Applying deterministic status bar..."
    xcrun simctl status_bar "$DEVICE_UDID" override \
        --time "$time" \
        --batteryState "$battery_state" \
        --batteryLevel "$battery_level" \
        --wifiBars "$wifi_bars" \
        --cellularBars "$cellular_bars" \
        --operatorName "$operator_name" \
        2>/dev/null || echo "  [warn] status_bar override may not be fully supported on this runtime"

    echo "  time=$time battery=$battery_level% wifi=$wifi_bars bars"
}

clear_status_bar() {
    xcrun simctl status_bar "$DEVICE_UDID" clear 2>/dev/null || true
}

# ── Capture One Scenario ──────────────────────────────────────────────
capture_scenario() {
    local scenario_json="$1"
    local index="$2"

    local scenario_id app_bundle deep_link wait_seconds description screen_family notes
    scenario_id=$(echo "$scenario_json" | jq -r '.id')
    app_bundle=$(echo "$scenario_json" | jq -r '.app_bundle')
    deep_link=$(echo "$scenario_json" | jq -r '.deep_link // empty')
    wait_seconds=$(echo "$scenario_json" | jq -r '.wait_seconds // 2')
    description=$(echo "$scenario_json" | jq -r '.description')
    screen_family=$(echo "$scenario_json" | jq -r '.screen_family')
    notes=$(echo "$scenario_json" | jq -r '.notes')

    local padded_index
    padded_index=$(printf "%04d" "$index")
    local filename="gen_${padded_index}_${scenario_id}.png"
    local filepath="$OUTPUT_DIR/$filename"

    echo "  [$padded_index] $scenario_id — $description"

    if $DRY_RUN; then
        echo "    [dry-run] Would capture $filename"
        return 0
    fi

    # Launch app or open deep link
    if [[ -n "$deep_link" ]]; then
        xcrun simctl openurl "$DEVICE_UDID" "$deep_link" 2>/dev/null || {
            echo "    [warn] Deep link failed: $deep_link — falling back to app launch"
            xcrun simctl launch "$DEVICE_UDID" "$app_bundle" 2>/dev/null || {
                echo "    [skip] Could not launch $app_bundle"
                return 1
            }
        }
    else
        xcrun simctl launch "$DEVICE_UDID" "$app_bundle" 2>/dev/null || {
            echo "    [skip] Could not launch $app_bundle"
            return 1
        }
    fi

    # Wait for the screen to settle
    sleep "$wait_seconds"

    # Capture screenshot
    xcrun simctl io "$DEVICE_UDID" screenshot --type png "$filepath" 2>/dev/null
    if [[ ! -f "$filepath" ]]; then
        echo "    [fail] Screenshot not captured"
        return 1
    fi

    local file_size
    file_size=$(stat -f%z "$filepath" 2>/dev/null || echo "0")
    echo "    [ok] $filename ($file_size bytes)"

    # Extract Q&A templates
    local qa_templates
    qa_templates=$(echo "$scenario_json" | jq -c '.qa_templates // []')

    # Write index entry (JSONL)
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    jq -cn \
        --arg id "gen_${padded_index}" \
        --arg filename "$filename" \
        --arg scenario_id "$scenario_id" \
        --arg screen_family "$screen_family" \
        --arg description "$description" \
        --arg notes "$notes" \
        --arg source "simulator_generated" \
        --arg device_name "$DEVICE_NAME" \
        --arg device_udid "$DEVICE_UDID" \
        --arg batch_id "$BATCH_ID" \
        --arg timestamp "$timestamp" \
        --arg generator_version "0.1.0" \
        --arg app_bundle "$app_bundle" \
        --arg deep_link "$deep_link" \
        --argjson qa_templates "$qa_templates" \
        --argjson file_size "$file_size" \
        '{
            id: $id,
            image_filename: $filename,
            scenario_id: $scenario_id,
            screen_family: $screen_family,
            description: $description,
            notes: $notes,
            source: $source,
            device_name: $device_name,
            device_udid: $device_udid,
            batch_id: $batch_id,
            timestamp: $timestamp,
            generator_version: $generator_version,
            app_bundle: $app_bundle,
            deep_link: $deep_link,
            qa_templates: $qa_templates,
            file_size_bytes: $file_size
        }' >> "$OUTPUT_DIR/capture_index.jsonl"

    return 0
}

# ── Main ──────────────────────────────────────────────────────────────
main() {
    echo "═══════════════════════════════════════════════════════════"
    echo "  AXIOM-Mobile Screenshot Capture Harness v0.1.0"
    echo "═══════════════════════════════════════════════════════════"
    echo ""

    # Validate scenarios file
    if [[ ! -f "$SCENARIOS_FILE" ]]; then
        echo "ERROR: Scenarios file not found: $SCENARIOS_FILE"
        exit 1
    fi

    # Generate batch ID if not provided
    if [[ -z "$BATCH_ID" ]]; then
        BATCH_ID="batch_$(date +%Y%m%d_%H%M%S)"
    fi

    resolve_device

    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    echo "Output directory: $OUTPUT_DIR"
    echo "Batch ID: $BATCH_ID"
    echo ""

    # Apply deterministic status bar
    apply_status_bar
    echo ""

    # Return to home screen before starting
    xcrun simctl spawn "$DEVICE_UDID" launchctl kickstart -k system/com.apple.SpringBoard 2>/dev/null || true
    sleep 2

    # Read and execute scenarios
    local scenario_count
    scenario_count=$(jq '.scenarios | length' "$SCENARIOS_FILE")
    echo "Capturing $scenario_count scenarios..."
    echo ""

    local ok=0
    local skip=0

    for i in $(seq 0 $((scenario_count - 1))); do
        local scenario_json
        scenario_json=$(jq -c ".scenarios[$i]" "$SCENARIOS_FILE")

        if capture_scenario "$scenario_json" "$((i + 1))"; then
            ok=$((ok + 1))
        else
            skip=$((skip + 1))
        fi

        # Brief pause between scenarios to let animations settle
        sleep 1
    done

    echo ""

    # Restore status bar
    clear_status_bar
    echo "Status bar restored."

    # Summary
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  Capture complete: $ok captured, $skip skipped"
    echo "  Output: $OUTPUT_DIR"
    echo "  Index:  $OUTPUT_DIR/capture_index.jsonl"
    echo "  Batch:  $BATCH_ID"
    echo "═══════════════════════════════════════════════════════════"

    if [[ -f "$OUTPUT_DIR/capture_index.jsonl" ]]; then
        local index_lines
        index_lines=$(wc -l < "$OUTPUT_DIR/capture_index.jsonl" | tr -d ' ')
        echo "  Index entries: $index_lines"
    fi

    echo ""
    echo "Next steps:"
    echo "  1. Review screenshots in $OUTPUT_DIR"
    echo "  2. Run: python3 ml/scripts/index_generated_screenshots.py --input $OUTPUT_DIR"
    echo "  3. Review candidates and promote to data/manifests/"
}

main "$@"
