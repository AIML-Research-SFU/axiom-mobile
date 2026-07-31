#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# AXIOM-Mobile — v0.5.0 New-App Capture Wrapper
#
# Wraps capture_screenshots.sh for the v0.5.0 scenarios (Safari synthetic
# pages, Reminders, Contacts), which need extra setup capture_screenshots.sh
# doesn't handle on its own:
#   1. Render the synthetic HTML pages the Safari scenarios point at.
#   2. Start a local HTTP server to serve them (Simulator shares the host
#      Mac's network namespace, so http://127.0.0.1:<port> just works).
#   3. Run the real capture batch, which itself includes two throwaway
#      warmup scenarios (Safari, Reminders) ahead of the promoted ones --
#      see generate_exact_scenarios.py's `warmup=True` docstrings. An
#      out-of-band pre-launch (terminate/open/wait/terminate via plain
#      xcrun calls, tried first, even with two full cycles) was measured
#      NOT to reliably clear these two apps' first-launch onboarding
#      screens; only a real capture-batch entry ahead of the promoted
#      ones does. Same gotcha class as the v0.3.0 Maps "Enable
#      Notifications" sheet -- capture around it, verified by visual
#      spot-check, not assumed away.
#   4. Stop the HTTP server.
#
# Usage:
#   ./scripts/capture_new_apps_v05.sh --device "iPhone 17 Pro Max"
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WEB_PORT=8765
DEVICE_NAME=""
OUTPUT_DIR="$HOME/axiom-local-data/raw_v05"
BATCH_ID="v05_new_apps_batch001"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --device) DEVICE_NAME="$2"; shift 2 ;;
        --output) OUTPUT_DIR="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 --device NAME [--output DIR]"
            exit 0
            ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

if [[ -z "$DEVICE_NAME" ]]; then
    echo "ERROR: --device is required (e.g. \"iPhone 17 Pro Max\")"
    exit 1
fi

DEVICE_UDID=$(xcrun simctl list devices available -j \
    | jq -r --arg name "$DEVICE_NAME" \
      '[.devices[][] | select(.name == $name and .state == "Booted")] | first | .udid // empty')
if [[ -z "$DEVICE_UDID" ]]; then
    DEVICE_UDID=$(xcrun simctl list devices available -j \
        | jq -r --arg name "$DEVICE_NAME" '[.devices[][] | select(.name == $name)] | first | .udid // empty')
    if [[ -z "$DEVICE_UDID" ]]; then
        echo "ERROR: No simulator found with name '$DEVICE_NAME'."
        exit 1
    fi
    xcrun simctl boot "$DEVICE_UDID" 2>/dev/null || true
    sleep 5
fi
echo "Using simulator: $DEVICE_NAME ($DEVICE_UDID)"

echo -e "\n[1/5] Rendering synthetic web pages..."
python3 "$SCRIPT_DIR/generate_synthetic_web_pages.py"
PAGES_DIR="$SCRIPT_DIR/synthetic_web_pages"

echo -e "\n[2/5] Starting local HTTP server on port $WEB_PORT..."
python3 -m http.server "$WEB_PORT" --directory "$PAGES_DIR" > /tmp/axiom_web_server.log 2>&1 &
SERVER_PID=$!
trap 'echo "Stopping HTTP server ($SERVER_PID)..."; kill $SERVER_PID 2>/dev/null || true' EXIT
sleep 1

echo -e "\n[3/4] Generating v0.5.0 scenario definitions (includes 2 unpromoted warmup entries)..."
python3 "$SCRIPT_DIR/generate_exact_scenarios.py" --v05-only

echo -e "\n[4/4] Capturing v0.5.0 scenarios (20 captured, 17 promoted)..."
"$SCRIPT_DIR/capture_screenshots.sh" \
    --device "$DEVICE_NAME" \
    --output "$OUTPUT_DIR" \
    --scenarios "$SCRIPT_DIR/capture_scenarios_v05_delta.json" \
    --batch-id "$BATCH_ID"

echo -e "\nDone. Raw captures + capture_index.jsonl: $OUTPUT_DIR"
