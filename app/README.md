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
│   └── InferenceResult.swift     Inference result value type
├── Services/
│   └── InferenceService.swift    Protocol + placeholder implementation
└── Features/
    └── Testbed/
        ├── TestbedView.swift     Main testbed screen
        ├── TestbedViewModel.swift  @Observable view model
        └── Views/
            ├── ScreenshotSection.swift
            ├── QuestionInputSection.swift
            ├── ModelPickerSection.swift
            ├── AnswerCard.swift
            └── DebugMetricsCard.swift
```

### Extending with real inference

When Core ML models are available, create a new conformance to `InferenceServiceProtocol` (e.g., `CoreMLInferenceService`) and swap it into `TestbedViewModel`. The view layer requires no changes.

### Requirements

- Xcode 26.0+
- iOS 26.0+
- No third-party dependencies
