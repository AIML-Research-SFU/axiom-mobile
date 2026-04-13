# Instruments Profiling Runbook — Phase 5

Last updated: 2026-04-13

## 1. Purpose

This runbook defines a reproducible protocol for profiling AXIOM-Mobile on physical Apple devices using Xcode Instruments and the app's built-in benchmark mode.

**What this runbook measures now:**

- Wall-clock inference latency (from the app's benchmark CSV export)
- CPU utilization, memory footprint, and energy impact (from Instruments traces)
- Session-level device metadata (from the app's companion `_meta.json` export)

**Current status (as of 2026-04-12):**

- `tiny_multimodal_v0` now runs through `CoreMLInferenceService` with real Core ML inference (`is_placeholder: false`).
- First real profiling session captured on iPhone 17 Pro Simulator: p50=199.5ms, p95=304.2ms (both PASS thresholds).
- Simulator results validate the full pipeline but are **not publishable** (no NPU, no real thermal/energy behavior).
- Physical-device profiling is unblocked and is the next step for publishable results.
- The `--auto-benchmark` launch argument enables headless profiling without manual UI interaction.

## 2. Supported Environments

| Environment | Status | Notes |
|-------------|--------|-------|
| iPhone 14 Pro (physical) | Primary target | Required for publishable results |
| iPhone 14+ (physical) | Supported | Any A16+ device with iOS 26 |
| M1/M2 MacBook (Designed for iPad) | Secondary | Useful for development profiling |
| iOS Simulator | Development only | **Not valid for performance measurement** — no NPU, no real thermal behavior, no energy data |

**Build configuration:**

- **Release builds** for all publishable profiling. Debug builds include extra assertions and unoptimized code paths that distort measurements.
- Profile via **Product > Profile** (Cmd+I) in Xcode, which builds in Release by default.
- Ensure the scheme's Run action uses **Release** configuration if profiling via the Run action instead.

## 3. Pre-Run Checklist

Complete every item before starting a profiling session.

### Device preparation

- [ ] Battery level >= 50% (energy measurements are unreliable below 20%)
- [ ] Device unplugged from charger (charging introduces thermal and power noise)
- [ ] Device at ambient temperature (not hot from prior use or direct sunlight)
- [ ] Wait 2 minutes after unplugging before starting (let thermals settle)

### Connectivity and background state

- [ ] Airplane mode ON (eliminates radio power noise and network interrupts)
- [ ] Wi-Fi and Bluetooth OFF (via Control Center after enabling Airplane mode)
- [ ] Close all background apps (swipe up from app switcher)
- [ ] Disable Do Not Disturb or Focus mode notifications that might interrupt

### App preparation

- [ ] App is installed via Release build (Product > Profile or Archive > Install)
- [ ] Open the app and confirm testbed loads
- [ ] Confirm the model picker shows expected model IDs
- [ ] Confirm `is_placeholder` shows in Debug Metrics card (or will show `false` when real model is loaded)
- [ ] If using a screenshot for the benchmark, load it before starting
- [ ] Type the benchmark question before starting

### Export validation

- [ ] Run a single inference and tap Export CSV
- [ ] Verify the CSV and `_meta.json` files appear in the share sheet
- [ ] Confirm the metadata JSON shows correct device name, OS version, and app build
- [ ] Clear the session before the real profiling run

## 4. Benchmark Protocol

### Model selection

Run each model ID that is currently executable:

| Model ID | Backend | Status |
|----------|---------|--------|
| `tiny_multimodal_v0` | Core ML | **Real inference** — first priority for profiling |
| `question_lookup_v0` | heuristic | Executable (placeholder latency) |
| `florence_2_base` | transformers | Config only — skip until Core ML ready |
| `llava_mobile` | transformers | Config only — skip until Core ML ready |
| `qwen_vl_chat_int4` | transformers | Config only — skip until Core ML ready |

### Run sequence

For each model:

1. **Warmup**: Run 3 single inferences (benchmark mode OFF). Discard these — they warm caches and JIT paths.
2. **Clear session**: Tap Clear in the Benchmark Summary card.
3. **Configure benchmark**: Toggle Benchmark Mode ON. Set iterations to **20** for placeholder, **50** for real Core ML models.
4. **Run benchmark**: Tap "Run Benchmark." Wait for completion.
5. **Export**: Tap Export CSV. Verify the `_meta.json` appears alongside the CSV.
6. **Share**: Use the Share button to AirDrop or save both files.

### Iteration count guidance

| Scenario | Iterations | Rationale |
|----------|-----------|-----------|
| Placeholder (current) | 20 | Sufficient to validate the pipeline; simulated latency has low variance |
| Real Core ML model | 50 | Enough samples for meaningful p50/p95 computation |
| Quick sanity check | 5 | Fast validation that the pipeline works |

### Naming convention for collected sessions

Use this pattern for organizing exported files:

```
{device}_{model_id}_{YYYYMMDD}T{HHMMSS}Z
```

Example: `iphone14pro_question_lookup_v0_20260415T143000Z`

The app's export timestamp in the filename (`axiom_benchmark_20260415T143000Z.csv`) already encodes the time. Add a device prefix when copying files to the repo or shared storage.

## 5. Instruments Workflow

### Which templates to use

Run these Instruments templates **in separate traces** (combining them adds overhead that distorts measurements):

| Template | What it measures | When to use |
|----------|-----------------|-------------|
| **Time Profiler** | CPU time per function, thread utilization | Every session — primary latency analysis |
| **Allocations** | Memory allocations, peak heap size, leaks | Every session — validates < 500MB constraint |
| **Energy Log** | CPU/GPU/networking energy impact | Physical device only — validates < 5% battery/hr |
| **System Trace** | Thread scheduling, IPC, syscalls | Only when investigating unexpected latency spikes |

### Step-by-step: Time Profiler session

1. Connect the physical device via USB.
2. In Xcode: **Product > Profile** (Cmd+I). This builds Release and opens Instruments.
3. Select **Time Profiler** template.
4. In Instruments, select your device as the target.
5. Press the red Record button in Instruments.
6. In the app on device: run the full benchmark sequence from Section 4.
7. When the benchmark completes, press Stop in Instruments.
8. In Instruments: use the **Call Tree** view, check **Separate by Thread** and **Invert Call Tree**.
9. Look for the inference service's `run()` method to isolate model inference time.
10. Save the trace: **File > Save** as `{session_name}.trace`.

### Step-by-step: Allocations session

1. Same setup as Time Profiler, but select **Allocations** template.
2. Record during the full benchmark run.
3. After stopping, check:
   - **All Heap Allocations** column for peak memory
   - **Persistent Bytes** at the end of the run (should be stable, no growth)
   - Filter by "AXIOM" to find app-specific allocations
4. Save the trace.

### Step-by-step: Energy Log session

1. **Physical device only** — Energy Log does not work in the simulator.
2. Select **Energy Log** template.
3. Record during a 50-iteration benchmark (longer runs give more stable energy estimates).
4. After stopping, check:
   - **CPU** energy level (0-20 scale)
   - **GPU** energy level
   - **Overhead** category
5. Note: with placeholder inference, energy usage will be minimal. Real Core ML inference will show meaningful GPU/NPU energy.
6. Save the trace.

### Correlating Instruments traces with CSV exports

The app's exported CSV and metadata JSON share a timestamp with the Instruments trace:

1. Note the Instruments trace start/stop time (visible in the trace header).
2. Open the companion `_meta.json` — the `session_id` and `export_timestamp` identify the app session.
3. The CSV `timestamp` column shows per-inference wall-clock times.
4. Align Instruments timeline regions with CSV iteration timestamps to correlate CPU/memory spikes with specific inference calls.

### Extracting trace metrics for the summary pipeline

After running each Instruments template, create a `trace_metrics.json` sidecar in the session folder with the key metrics. The Python pipeline (`ml/scripts/summarize_device_profiles.py`) merges this file into per-session summaries. See `docs/DEVICE_PROFILES.md` for the full schema.

Example after running Allocations + Energy Log:

```json
{
  "peak_memory_mb": 45.2,
  "cpu_energy_level": 2,
  "gpu_energy_level": 0,
  "cpu_time_user_s": 1.8,
  "cpu_time_system_s": 0.4,
  "notes": "Placeholder inference — minimal resource usage."
}
```

The Python pipeline **never** parses `.trace` binaries directly. This structured sidecar is the supported path for getting Instruments data into the analysis pipeline.

### What to save after each Instruments session

- [ ] The `.trace` file (Instruments save) — stored for reference, not parsed by Python
- [ ] A `trace_metrics.json` with key metrics extracted from the trace (see above)
- [ ] A screenshot of the Instruments summary view
- [ ] The CSV + `_meta.json` from the app (via Share/AirDrop)

## 6. Output Contract

After a complete profiling session for one model on one device, you should have:

```
results/device_profiles/{device}_{model_id}_{timestamp}/
├── axiom_benchmark_{stamp}.csv              # Per-inference records from app
├── axiom_benchmark_{stamp}_meta.json        # Device/session metadata from app
├── time_profiler.trace                      # Instruments CPU trace
├── allocations.trace                        # Instruments memory trace
├── energy_log.trace                         # Instruments energy trace (device only)
├── instruments_summary.png                  # Screenshot of key Instruments view
└── notes.md                                 # Manual observations, anomalies, conditions
```

### Example `notes.md` template

```markdown
# Profiling Session Notes

- Date: 2026-04-15
- Device: iPhone 14 Pro, iOS 26.0
- Model: question_lookup_v0
- Build: AXIOMMobile 1.0 (1)
- Conditions: ambient temp ~22C, battery 78%, airplane mode ON
- Iterations: 20
- Observations:
  - [note any anomalies, thermal throttling, unexpected latency spikes]
- Placeholder: YES (all inference is simulated)
```

### Folder structure for the repo

Profiling results are stored under `results/device_profiles/`. This directory should be added to `.gitignore` for raw traces (which are large), but summary CSVs and metadata JSONs may be committed for reproducibility.

```
results/
├── baselines/                  # Phase 2 baseline results
├── selection_sweeps/           # Phase 3 sweep results
└── device_profiles/            # Phase 5 profiling sessions
    ├── _fixtures/              # Synthetic test sessions (not production data)
    ├── analysis/               # Generated summaries (from summarize_device_profiles.py)
    │   ├── session_*.json      # Per-session summary
    │   ├── summary.json        # Aggregate summary
    │   ├── summary.csv         # Flat aggregate CSV
    │   └── summary.md          # Human-readable report
    └── {session_folders}/      # One per (device, model, timestamp)
```

### Running the summary pipeline

After collecting sessions, run:

```bash
python3 ml/scripts/summarize_device_profiles.py
```

This validates session folders, computes latency stats and threshold evaluations, merges optional `trace_metrics.json` sidecars, and writes analysis artifacts. See `docs/DEVICE_PROFILES.md` for full documentation.

## 7. Known Limitations

1. **Placeholder inference**: All current profiling measures simulated latency (~150ms baseline, ~600ms VLM). These numbers validate the pipeline but are not publishable performance data.

2. **No real Core ML model**: The `question_lookup_v0` baseline is a Python-side heuristic with a placeholder Swift service. There is no `.mlpackage` to profile. Phase 4 (Core ML conversion) is blocked until a real multimodal model is trained and exported.

3. **Energy measurement requires physical device**: The Energy Log Instruments template does not work in the iOS Simulator. Battery drain estimates (< 5% per hour target from the proposal) can only be measured on hardware.

4. **NPU utilization not visible**: Until a real Core ML model uses the Neural Engine, there is no NPU activity to profile. The ANE (Apple Neural Engine) columns in Instruments will show zero.

5. **Limited model coverage**: Only `question_lookup_v0` is executable. The three VLM candidates (`florence_2_base`, `llava_mobile`, `qwen_vl_chat_int4`) are config-only placeholders in the app.

6. **Device name privacy**: On iOS 16+, `UIDevice.current.name` returns the generic model name ("iPhone") unless the app has the device-name entitlement. The `device_model` field in metadata distinguishes iPhone vs iPad, but the exact hardware model (e.g., "iPhone 14 Pro") should be noted manually in `notes.md`.

### When this runbook produces publishable results

- [x] A real Core ML model (`.mlpackage`) is integrated via `CoreMLInferenceService` — `tiny_multimodal_v0` (96KB, 24 classes)
- [x] `is_placeholder` flips to `false` in CSV and metadata exports — confirmed in simulator session
- [x] Auto-benchmark mode (`--auto-benchmark`) enables repeatable headless profiling
- [ ] Profiling is run on the target hardware (iPhone 14 Pro + M2 MacBook)
- [ ] At least 50 iterations per model per device are collected (simulator session used 20)
- [ ] Energy Log traces confirm < 5% battery drain per hour
- [ ] Allocations traces confirm < 500MB peak memory
