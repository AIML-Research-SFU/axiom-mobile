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
├── AXIOMMobileApp.swift            App entry point
├── ContentView.swift               Root view (routes to TestbedView)
├── Models/
│   ├── ModelCatalog.swift          Model metadata matching repo configs
│   ├── InferenceResult.swift       Inference result value type
│   ├── BenchmarkRecord.swift       Structured benchmark log record
│   └── SessionMetadata.swift       Device/session metadata for reproducibility
├── Services/
│   ├── InferenceService.swift      Protocol + placeholder implementation
│   ├── CoreMLInferenceService.swift  Real Core ML inference for tiny_multimodal_v0
│   └── BenchmarkExporter.swift     CSV export to Documents directory
├── Resources/
│   ├── TinyMultimodal.mlpackage    Exported Core ML model (96KB, 24 classes)
│   └── tiny_multimodal_v0_labels.json  Label vocabulary (idx → answer mapping)
└── Features/
    └── Testbed/
        ├── TestbedView.swift       Main testbed screen
        ├── TestbedViewModel.swift  @Observable view model (routes real vs placeholder)
        └── Views/
            ├── ScreenshotSection.swift
            ├── QuestionInputSection.swift
            ├── ModelPickerSection.swift
            ├── AnswerCard.swift
            ├── DebugMetricsCard.swift
            ├── BenchmarkConfigSection.swift
            └── BenchmarkSummaryCard.swift
```

### Real Core ML inference

The app now includes a real Core ML inference path for `tiny_multimodal_v0`:

1. **`CoreMLInferenceService`** loads the bundled `TinyMultimodal.mlpackage` and `tiny_multimodal_v0_labels.json`.
2. It preprocesses the screenshot (resize to 128×128, BGRA pixel buffer) and question (ASCII character-level encoding, padded to 128 chars).
3. It runs Core ML prediction and decodes the argmax of the 24-class logit output into an answer string.
4. `TestbedViewModel` routes to `CoreMLInferenceService` when `isCoreMLReady` is true, otherwise falls back to `PlaceholderInferenceService`.
5. The `isPlaceholder` field is `false` for real Core ML runs, so benchmark exports accurately distinguish real from simulated inference.

### Refreshing the model

To update the bundled model after re-training/re-exporting:

```bash
# 1. Train on real data
python3 ml/scripts/run_trainable_baseline.py --image-root /path/to/screenshots_v1

# 2. Export to Core ML
python3 ml/scripts/export_coreml.py \
    --checkpoint-dir results/trainable_baselines/tiny_multimodal_v0_seed0/checkpoint \
    --image-root /path/to/screenshots_v1

# 3. Copy artifacts into app
cp -R results/coreml_exports/tiny_multimodal_v0_seed0/TinyMultimodal.mlpackage \
    app/AXIOMMobile/AXIOMMobile/Resources/TinyMultimodal.mlpackage
cp results/coreml_exports/tiny_multimodal_v0_seed0/label_vocab.json \
    app/AXIOMMobile/AXIOMMobile/Resources/tiny_multimodal_v0_labels.json

# 4. Rebuild in Xcode
```

### Extending with additional models

To add another Core ML model, create a new `InferenceServiceProtocol` conformance (or extend `CoreMLInferenceService` to dispatch by model ID), add the model entry to `ModelCatalog`, and set `isCoreMLReady: true`.

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

### Real vs placeholder inference

| Model | Service | `isPlaceholder` |
|-------|---------|-----------------|
| `tiny_multimodal_v0` | `CoreMLInferenceService` | `false` |
| `question_lookup_v0` | `PlaceholderInferenceService` | `true` |
| `florence_2_base` | `PlaceholderInferenceService` | `true` |
| `llava_mobile` | `PlaceholderInferenceService` | `true` |
| `qwen_vl_chat_int4` | `PlaceholderInferenceService` | `true` |

The routing is automatic: `TestbedViewModel` checks `selectedModel.isCoreMLReady` and dispatches to the appropriate service. Benchmark CSV exports and `_meta.json` accurately record which service was used via the `is_placeholder` field.

## Requirements

- Xcode 26.0+
- iOS 26.0+
- No third-party dependencies
