# Device Profiles — Ingestion and Summary Pipeline

Last updated: 2026-04-13

## Purpose

This pipeline consumes exported app benchmark sessions (CSV + `_meta.json`), optionally merges manual Instruments trace metrics, computes stable per-session and aggregate performance summaries, and writes reusable analysis artifacts.

**Current state (as of 2026-04-13):** `tiny_multimodal_v0` runs through `CoreMLInferenceService` with real Core ML inference. Sessions are marked `is_placeholder: false` and thresholds evaluate as real pass/fail. Two simulator sessions captured: 20-iter Debug (p50=199.5ms) and 50-iter Release with hardened input (p50=98.0ms, `image_loaded=true`). Two physical-device sessions captured on AT-X (iPhone 15 Pro Max, A17 Pro, iOS 26.4.1): Session 1 (cold, 50 iterations, p50=14.0ms, p95=26.2ms, mean=18.0ms) and Session 2 (warm, with Time Profiler attached, 50 iterations, p50=14.5ms, p95=22.0ms, mean=16.8ms). All sessions PASS latency thresholds with wide margin. Physical device is ~7x faster than simulator (14ms vs 98ms). A 3.6MB Time Profiler trace was captured. Benchmark-input hardening via `BenchmarkInputProvider` ensures the full image preprocessing pipeline is exercised. Energy and memory Instruments traces (Allocations, Energy Log) are still outstanding -- no `trace_metrics.json` sidecar exists for the physical sessions.

Other models (`question_lookup_v0`, VLM candidates) still use `PlaceholderInferenceService` and are marked `is_placeholder: true`.

## Session Folder Contract

Each profiling session lives in a directory under `results/device_profiles/`:

```
results/device_profiles/{device}_{model_id}_{YYYYMMDD}T{HHMMSS}Z/
├── axiom_benchmark_{stamp}.csv              # REQUIRED — app CSV export
├── axiom_benchmark_{stamp}_meta.json        # REQUIRED — app metadata export
├── trace_metrics.json                       # OPTIONAL — manually extracted Instruments summary
├── notes.md                                 # OPTIONAL — manual observations
├── time_profiler.trace                      # OPTIONAL — raw Instruments trace (not parsed)
├── allocations.trace                        # OPTIONAL — raw Instruments trace (not parsed)
└── energy_log.trace                         # OPTIONAL — raw Instruments trace (not parsed)
```

### Required files

**Benchmark CSV** (`axiom_benchmark_*.csv`)

Columns (from the app export contract):

```
timestamp,model_id,image_loaded,question_length,latency_ms,is_placeholder,run_kind,iteration_index
```

**Session metadata** (`axiom_benchmark_*_meta.json`)

Fields:

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Unique UUID per export |
| `export_timestamp` | string | ISO 8601 export time |
| `device_name` | string | UIDevice.current.name |
| `device_model` | string | UIDevice.current.model |
| `system_name` | string | OS name |
| `system_version` | string | OS version |
| `app_version` | string | Bundle short version string |
| `app_build` | string | Bundle build number |
| `model_id` | string | Model used for the benchmark |
| `is_placeholder` | bool | Whether inference was simulated |
| `benchmark_iterations` | int | Number of benchmark-mode runs |
| `record_count` | int | Total records in the CSV |

### Optional files

**Trace metrics sidecar** (`trace_metrics.json`)

This file is filled in manually after running Instruments templates. The Python pipeline never parses `.trace` binaries directly.

Schema:

```json
{
  "peak_memory_mb": 45.2,
  "cpu_energy_level": 2,
  "gpu_energy_level": 0,
  "overhead_energy_level": null,
  "cpu_time_user_s": 1.8,
  "cpu_time_system_s": 0.4,
  "notes": "Optional free-text observations."
}
```

All fields are optional. Omit or set to `null` for unavailable metrics.

| Field | Type | Source |
|-------|------|--------|
| `peak_memory_mb` | float | Instruments Allocations template — "All Heap Allocations" peak |
| `cpu_energy_level` | float | Instruments Energy Log — CPU column (0–20 scale) |
| `gpu_energy_level` | float | Instruments Energy Log — GPU column (0–20 scale) |
| `overhead_energy_level` | float | Instruments Energy Log — Overhead column |
| `cpu_time_user_s` | float | Instruments Time Profiler — user CPU time |
| `cpu_time_system_s` | float | Instruments Time Profiler — system CPU time |
| `notes` | string | Free-text notes about the trace session |

**Raw `.trace` files** are stored for reference but are never parsed by the Python pipeline. They are gitignored due to large size.

**`notes.md`** is a free-text file for manual observations (thermal throttling, anomalies, ambient conditions). See `docs/INSTRUMENTS_RUNBOOK.md` for a template.

## Running the Summarizer

```bash
python3 ml/scripts/summarize_device_profiles.py
```

By default, scans `results/device_profiles/` for valid session directories (those containing at least one `*.csv` and one `*_meta.json`). Directories starting with `_` are skipped (used for fixtures).

Custom profiles directory:

```bash
python3 ml/scripts/summarize_device_profiles.py --profiles-dir results/device_profiles/_fixtures
```

### Outputs

Written to `{profiles_dir}/analysis/`:

| File | Description |
|------|-------------|
| `session_{session_id}.json` | Per-session detailed summary |
| `summary.json` | Aggregate summary across all sessions |
| `summary.csv` | Flat CSV of per-session metrics |
| `summary.md` | Human-readable markdown report |

## Threshold Evaluation

The pipeline evaluates effectiveness thresholds from `docs/SPEC.md` honestly:

| Threshold | Source | Evaluated from |
|-----------|--------|----------------|
| Latency p50 <= 400ms | Benchmark CSV | Always available |
| Latency p95 <= 600ms | Benchmark CSV | Always available |
| Peak memory < 500MB | `trace_metrics.json` | Only if present |
| Energy < 5% battery/hr | `trace_metrics.json` | Partial — Instruments reports relative scale, not %/hr |
| Exact Match >= 70% | Offline eval | **Never** from device profiles |
| Model size < 100MB | Core ML export | **Never** from device profiles |

### Status values

Each threshold evaluation includes an explicit status:

- **`pass`** — metric meets threshold (real measurement)
- **`fail`** — metric does not meet threshold (real measurement)
- **`placeholder`** — data exists but comes from simulated inference; not valid for conclusions
- **`unavailable`** — data required for evaluation is missing; reason explains what to do

### Honest limitations

- Placeholder sessions are always marked `status: "placeholder"` for latency thresholds. The pipeline never claims pass/fail for simulated data.
- Quality metrics (EM, BLEU, hallucination rate) cannot be evaluated from device profiles. They require offline evaluation against ground-truth labels.
- Model size cannot be evaluated until `.mlpackage` files exist (Phase 4).
- Energy drain (`< 5% battery/hr`) cannot be directly computed from Instruments data, which reports relative levels (0–20 scale). The pipeline records the raw level for manual interpretation.

## Placeholder vs Real Sessions

The `is_placeholder` field propagates from the app through the entire pipeline:

1. **App** — `PlaceholderInferenceService` sets `is_placeholder: true` in both CSV and `_meta.json`
2. **Pipeline** — reads `is_placeholder` from metadata and tags all summaries accordingly
3. **Thresholds** — latency evaluations get `status: "placeholder"` instead of pass/fail
4. **Aggregate** — reports placeholder vs real session counts with explicit notes

When `CoreMLInferenceService` replaces the placeholder, `is_placeholder` flips to `false` automatically. No pipeline changes needed.

## Schema Types

Typed dataclasses are defined in `ml/src/axiom/results/device_profiles.py`:

- `BenchmarkCSVRow` — one parsed row from CSV
- `SessionMetadata` — parsed `_meta.json`
- `TraceMetrics` — optional Instruments sidecar
- `LatencyStats` — computed latency statistics (min/max/mean/p50/p95)
- `ThresholdEvaluation` — one threshold check with status + reason
- `SessionSummary` — complete per-session output
- `AggregateSummary` — cross-session aggregate

## Test Fixtures

Synthetic fixture sessions for pipeline verification live in `results/device_profiles/_fixtures/`. These are clearly marked test data, not production profiling results. The summarizer skips `_`-prefixed directories by default; pass `--profiles-dir results/device_profiles/_fixtures` to exercise them.
