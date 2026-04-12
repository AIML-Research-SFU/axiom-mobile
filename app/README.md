# AXIOM-Mobile iOS App

## Testbed Shell (Phase 2)

The app currently provides a **testbed shell** for exercising the screenshot QA flow before real model inference is available.

### What it does

1. **Screenshot import** — pick any image from the photo library.
2. **Question input** — type a natural-language question about the screenshot.
3. **Model picker** — choose from the four model IDs defined in `ml/configs/models/`:
   - `question_lookup_v0` (executable baseline)
   - `florence_2_base` (VLM candidate)
   - `llava_mobile` (VLM candidate)
   - `qwen_vl_chat_int4` (VLM candidate)
4. **Run** — triggers a placeholder inference pass with simulated latency.
5. **Answer card** — displays the demo result.
6. **Debug metrics card** — shows model ID, image status, question length, and latency.

### Architecture

```
AXIOMMobile/
├── AXIOMMobileApp.swift          App entry point
├── ContentView.swift             Root view (routes to TestbedView)
├── Models/
│   ├── ModelCatalog.swift        Model metadata matching repo configs
│   ├── InferenceResult.swift     Inference result value type
│   ├── BenchmarkRecord.swift     Structured benchmark log record
│   └── SessionMetadata.swift     Device/session metadata for reproducibility
├── Services/
│   ├── InferenceService.swift    Protocol + placeholder implementation
│   └── BenchmarkExporter.swift   CSV export to Documents directory
└── Features/
    └── Testbed/
        ├── TestbedView.swift     Main testbed screen
        ├── TestbedViewModel.swift  @Observable view model
        └── Views/
            ├── ScreenshotSection.swift
            ├── QuestionInputSection.swift
            ├── ModelPickerSection.swift
            ├── AnswerCard.swift
            ├── DebugMetricsCard.swift
            ├── BenchmarkConfigSection.swift
            └── BenchmarkSummaryCard.swift
```

### Extending with real inference

When Core ML models are available, create a new conformance to `InferenceServiceProtocol` (e.g., `CoreMLInferenceService`) and swap it into `TestbedViewModel`. The view layer and benchmark infrastructure require no changes.

## Benchmark Mode (Phase 5 Instrumentation)

The testbed includes a benchmark mode for repeated inference runs and structured logging.

### How it works

1. Toggle **Benchmark Mode** in the config section.
2. Set the iteration count (1-50) with the stepper.
3. Tap **Run Benchmark** — the app runs inference N times and logs each result.
4. View aggregate statistics in the **Benchmark Summary** card (runs, avg/min/max latency, model ID, export status).
5. Tap **Export CSV** to save results to the app's Documents directory.
6. Use **Share** to send the CSV via AirDrop, email, or other share targets.
7. Tap **Clear** to reset the session.

Single-run inference (benchmark mode off) also logs records with `run_kind: single`.

### CSV schema

```csv
timestamp,model_id,image_loaded,question_length,latency_ms,is_placeholder,run_kind,iteration_index
```

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO 8601 | When the inference completed |
| `model_id` | string | Model identifier from `ModelCatalog` |
| `image_loaded` | bool | Whether a screenshot was loaded |
| `question_length` | int | Character count of the question |
| `latency_ms` | int | Inference latency in milliseconds |
| `is_placeholder` | bool | Whether the result came from placeholder service |
| `run_kind` | string | `single` or `benchmark` |
| `iteration_index` | int | 0 for single runs; 0..N-1 for benchmark iterations |

### Export location

CSV files are written to the app's Documents directory with filenames like:

```
axiom_benchmark_20260412T101500Z.csv
```

A companion metadata JSON is exported alongside each CSV:

```
axiom_benchmark_20260412T101500Z_meta.json
```

The metadata file captures device and session context for reproducibility:

| Field | Description |
|-------|-------------|
| `session_id` | Unique UUID per export |
| `export_timestamp` | ISO 8601 export time |
| `device_name` | `UIDevice.current.name` |
| `device_model` | `UIDevice.current.model` (iPhone, iPad) |
| `system_name` / `system_version` | OS name and version |
| `app_version` / `app_build` | Bundle short version and build number |
| `model_id` | Model used for the benchmark |
| `is_placeholder` | Whether inference was simulated |
| `benchmark_iterations` | Number of benchmark-mode runs |
| `record_count` | Total records in the CSV |

The **Share** button (appears after export) sends both the CSV and metadata JSON via the system share sheet.

### What is still placeholder

All inference currently runs through `PlaceholderInferenceService`, which simulates latency (150ms for baseline, 600ms for VLM candidates) without real model computation. The benchmark infrastructure is real — when Core ML models are connected, the same logging and export flow captures actual on-device performance metrics.

### Preparing for Core ML evaluation

When real `.mlpackage` models are available:

1. Create `CoreMLInferenceService` conforming to `InferenceServiceProtocol`.
2. Swap it into `TestbedViewModel`.
3. The benchmark mode, CSV logging, and export flow work unchanged.
4. Logged latencies will reflect real on-device inference time.
5. The `is_placeholder` field will flip to `false`, clearly distinguishing real from simulated results.

## Requirements

- Xcode 26.0+
- iOS 26.0+
- No third-party dependencies
