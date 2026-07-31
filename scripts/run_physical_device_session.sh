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
XCODEPROJ="$REPO_ROOT/app/AXIOMMobile/AXIOMMobile.xcodeproj"
BUNDLE_ID="com.arieljtyson.AXIOMMobile"
ITERATIONS=50
MODEL_ID=""
DEVICE_UDID_OVERRIDE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model) MODEL_ID="$2"; shift 2 ;;
        --bundle-id) BUNDLE_ID="$2"; shift 2 ;;
        --udid) DEVICE_UDID_OVERRIDE="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 --model <model_id> [--bundle-id <id>] [--udid <device_udid>]"
            echo "  Ready-to-profile models (real CoreML app integration): tiny_multimodal_v1, axiom_lora_v1"
            echo "  --udid: disambiguate when multiple physical devices are known to Xcode"
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
# `xcodebuild -showdestinations` is the source of truth here, not
# `xctrace list devices`: it explicitly tags each destination with
# `platform:iOS,` (real device) vs `platform:iOS Simulator,`, and flags
# devices that can't actually build this scheme with an `error:` field
# (e.g. an iOS version below the deployment target) -- both distinctions
# `xctrace`'s plain device list doesn't reliably make (simulator entries
# don't all contain the word "Simulator" in their name, and it has no
# concept of build compatibility at all). Excludes the generic "Any iOS
# Device" placeholder destination, which has no real UDID.
echo -e "\n[1/7] Verifying physical device..."
if [[ -n "$DEVICE_UDID_OVERRIDE" ]]; then
    DEVICE_UDID="$DEVICE_UDID_OVERRIDE"
    echo "  Using --udid override: $DEVICE_UDID"
else
    CANDIDATES="$(xcodebuild -showdestinations -project "$XCODEPROJ" -scheme AXIOMMobile 2>&1 \
        | grep "platform:iOS," | grep -v "dvtdevice-" | grep -v "error:")"
    CANDIDATE_COUNT="$(echo "$CANDIDATES" | grep -c "id:" || true)"

    if [[ "$CANDIDATE_COUNT" -eq 0 ]]; then
        echo "ERROR: No compatible physical device found."
        echo "Full destination list (look for your device and any 'error:' explaining why it's excluded):"
        xcodebuild -showdestinations -project "$XCODEPROJ" -scheme AXIOMMobile 2>&1 | grep "platform:iOS,"
        exit 1
    elif [[ "$CANDIDATE_COUNT" -gt 1 ]]; then
        echo "ERROR: Multiple compatible devices found -- re-run with --udid to pick one:"
        echo "$CANDIDATES"
        exit 1
    fi

    DEVICE_UDID="$(echo "$CANDIDATES" | grep -oE "id:[0-9A-Fa-f-]+" | head -1 | cut -d: -f2)"
    echo "  Found: $(echo "$CANDIDATES" | grep -oE "name:[^,}]+" | head -1 | cut -d: -f2)"
fi
echo "  UDID: $DEVICE_UDID"

# ── 2. Build + install Release ───────────────────────────────────────
# -allowProvisioningUpdates: without this, a CLI build embeds whatever
# provisioning profile is already on disk even if it's expired (free/
# personal Apple ID profiles expire every ~7 days) -- Xcode's GUI Run
# button silently renews it first, but `xcodebuild` alone doesn't. This
# flag makes xcodebuild do the same renewal-via-developer-portal step
# CLI-only, which is what a real first run against this hardware needed
# (install failed with MIInstallerErrorDomain error 13, "provisioning
# profile has expired," without it).
echo -e "\n[2/7] Building Release and installing on device..."
xcodebuild -project "$REPO_ROOT/app/AXIOMMobile/AXIOMMobile.xcodeproj" \
    -scheme AXIOMMobile -sdk iphoneos -configuration Release \
    -destination "platform=iOS,id=$DEVICE_UDID" \
    -allowProvisioningUpdates \
    build 2>&1 | tail -15

# Do NOT assume the build output lives under the repo -- this project
# uses Xcode's default DerivedData location, not a custom build dir. A
# hardcoded "$REPO_ROOT/app/AXIOMMobile/build/..." guess silently found
# a real but *stale* (April) app bundle with a long-expired embedded
# profile sitting at that exact path on the first real run against this
# hardware, and devicectl happily installed that instead of the fresh
# build -- same error, wrong cause, wasted a retry. Ask xcodebuild
# itself where the real product is.
BUILT_PRODUCTS_DIR="$(xcodebuild -showBuildSettings \
    -project "$REPO_ROOT/app/AXIOMMobile/AXIOMMobile.xcodeproj" \
    -scheme AXIOMMobile -sdk iphoneos -configuration Release \
    2>&1 | grep -m1 "BUILT_PRODUCTS_DIR" | awk '{print $NF}')"
APP_PATH="$BUILT_PRODUCTS_DIR/AXIOMMobile.app"
echo "  Installing fresh build from: $APP_PATH"
xcrun devicectl device install app --device "$DEVICE_UDID" \
    "$APP_PATH" 2>&1 | tail -5

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
