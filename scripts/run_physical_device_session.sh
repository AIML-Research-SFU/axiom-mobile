#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# AXIOM-Mobile — Physical-Device Profiling Session Driver
#
# Consolidates docs/INSTRUMENTS_RUNBOOK.md's Time Profiler / Allocations /
# Energy Log workflow into one script, run per model. Energy and memory
# have never been measured for any model in any semester (see
# paper/PAPER_DRAFT_v4.md Section 7.3) -- this is the one step in the
# whole correction plan that genuinely requires a physical device in
# someone's hands, so the goal here is to make that hands-on time as
# short as possible: one script per model, three short traces, done.
#
# Usage (device connected via USB, unlocked, trusted):
#   ./scripts/run_physical_device_session.sh --model tiny_multimodal_v1
#   ./scripts/run_physical_device_session.sh --model axiom_lora_v1
#
# Before running, complete the pre-run checklist in
# docs/INSTRUMENTS_RUNBOOK.md Section 3 (battery >=50%, unplugged 2+ min,
# airplane mode on, background apps closed) -- this script does not (and
# cannot) verify physical device state.
#
# Templates are run in separate traces deliberately (combining them adds
# overhead that distorts measurements -- see runbook Section 5).
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUNDLE_ID="com.arieljtyson.AXIOMMobile"
ITERATIONS=50
MODEL_ID=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model) MODEL_ID="$2"; shift 2 ;;
        --bundle-id) BUNDLE_ID="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 --model <model_id> [--bundle-id <id>]"
            echo "  Ready-to-profile models (real CoreML app integration): tiny_multimodal_v1, axiom_lora_v1"
            exit 0
            ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

if [[ -z "$MODEL_ID" ]]; then
    echo "ERROR: --model is required (e.g. tiny_multimodal_v1 or axiom_lora_v1)"
    exit 1
fi

echo "================================================================"
echo "  Physical-Device Profiling Session — $MODEL_ID"
echo "================================================================"

# ── 1. Verify device ─────────────────────────────────────────────────
echo -e "\n[1/7] Verifying physical device..."
DEVICE_LINE="$(xcrun xctrace list devices 2>&1 | grep -v "Simulator" | grep -iE "iPhone|iPad" | head -1 || true)"
if [[ -z "$DEVICE_LINE" ]]; then
    echo "ERROR: No physical device found. Connect via USB, unlock it, and trust this Mac."
    echo "  xcrun xctrace list devices"
    exit 1
fi
DEVICE_UDID="$(echo "$DEVICE_LINE" | grep -oE "\([0-9A-Fa-f-]{25,}\)" | tr -d '()')"
echo "  Found: $DEVICE_LINE"
echo "  UDID: $DEVICE_UDID"

# ── 2. Build + install Release ───────────────────────────────────────
echo -e "\n[2/7] Building Release and installing on device..."
xcodebuild -project "$REPO_ROOT/app/AXIOMMobile/AXIOMMobile.xcodeproj" \
    -scheme AXIOMMobile -sdk iphoneos -configuration Release \
    -destination "platform=iOS,id=$DEVICE_UDID" \
    build 2>&1 | tail -10
xcrun devicectl device install app --device "$DEVICE_UDID" \
    "$REPO_ROOT/app/AXIOMMobile/build/Release-iphoneos/AXIOMMobile.app" 2>&1 | tail -5

SESSION_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SESSION_NAME="atx-${MODEL_ID}-${SESSION_STAMP}"
TRACE_DIR="$HOME/axiom-local-data/device_traces/$SESSION_NAME"
mkdir -p "$TRACE_DIR"

run_traced_benchmark() {
    local template="$1"
    local output="$2"
    local time_limit="$3"

    echo "  Launching --auto-benchmark --model $MODEL_ID ..."
    xcrun devicectl device process launch --device "$DEVICE_UDID" \
        "$BUNDLE_ID" -- --auto-benchmark --model "$MODEL_ID" \
        > "$TRACE_DIR/launch_${template// /_}.log" 2>&1 &
    LAUNCH_PID=$!
    sleep 2  # let the process actually start before attaching

    # Find the running process id on-device for xctrace --attach
    PID="$(xcrun devicectl device info processes --device "$DEVICE_UDID" 2>/dev/null \
        | grep "$BUNDLE_ID" | awk '{print $1}' | head -1 || true)"
    if [[ -z "$PID" ]]; then
        echo "  WARNING: could not resolve on-device PID for $BUNDLE_ID -- attach manually in Instruments if this fails."
    fi

    echo "  Recording $template for ${time_limit}..."
    xcrun xctrace record --template "$template" --device "$DEVICE_UDID" \
        ${PID:+--attach "$PID"} --output "$TRACE_DIR/$output" --time-limit "$time_limit" \
        || echo "  WARNING: xctrace record failed for $template -- capture manually via Instruments GUI (Product > Profile) as a fallback."

    wait "$LAUNCH_PID" 2>/dev/null || true
}

# ── 3. Time Profiler ─────────────────────────────────────────────────
echo -e "\n[3/7] Time Profiler trace (~50 iterations, ~30-45s)..."
run_traced_benchmark "Time Profiler" "time_profiler.trace" "45s"

# ── 4. Allocations ───────────────────────────────────────────────────
echo -e "\n[4/7] Allocations trace..."
run_traced_benchmark "Allocations" "allocations.trace" "45s"

# ── 5. Energy Log (physical device only) ─────────────────────────────
echo -e "\n[5/7] Energy Log trace (physical device only -- the one number that has never been measured)..."
run_traced_benchmark "Energy Log" "energy_log.trace" "45s"

# ── 6. Pull the app's CSV/meta export ────────────────────────────────
echo -e "\n[6/7] Pulling exported CSV + metadata from device..."
echo "  If AirDrop/Share was used instead, copy the CSV + _meta.json into:"
echo "  $TRACE_DIR"
echo "  (automatic pull via devicectl requires the app's Documents container path,"
echo "   which varies by iOS version -- doing this by hand via Xcode's Devices"
echo "   window (Window > Devices and Simulators > Installed Apps > gear icon >"
echo "   Download Container) is the reliable fallback in the runbook)."

# ── 7. Stage + summarize ─────────────────────────────────────────────
echo -e "\n[7/7] Once CSV/meta + trace_metrics.json (see runbook Section 5) are in $TRACE_DIR:"
echo ""
echo "  python3 ml/scripts/stage_device_profile_session.py \\"
echo "      --source-dir $TRACE_DIR \\"
echo "      --device-name atx-iphone-$MODEL_ID"
echo ""
echo "  python3 ml/scripts/summarize_device_profiles.py"
echo ""
echo "================================================================"
echo "  Session traces: $TRACE_DIR"
echo "  Next: open each .trace in Instruments, note peak_memory_mb"
echo "  (Allocations) and cpu/gpu energy levels (Energy Log) into a"
echo "  trace_metrics.json sidecar per docs/INSTRUMENTS_RUNBOOK.md Section 5."
echo "================================================================"
