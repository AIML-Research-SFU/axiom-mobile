# Device Profile Summary Report

Generated: 2026-04-12T21:21:36Z
Sessions: 1
Models: tiny_multimodal_v0
Devices: iPhone (26.4)
Placeholder sessions: 0
Real sessions: 1

## iphone17pro-sim_tiny_multimodal_v0_20260412T212027Z

- **Model:** tiny_multimodal_v0
- **Device:** iPhone (26.4)
- **Placeholder:** No
- **Records:** 20 total (20 benchmark, 0 single)
- **Latency:** min=185ms, mean=220.2ms, p50=199.5ms, p95=304.2ms, max=498ms

### Threshold Evaluation

| Metric | Threshold | Measured | Status | Reason |
|--------|-----------|----------|--------|--------|
| latency_p50 | <= 400 ms | 199.5 ms | **pass** | p50 latency meets threshold. |
| latency_p95 | <= 600 ms | 304.2 ms | **pass** | p95 latency meets threshold. |
| peak_memory | < 500 MB | — | **unavailable** | No trace_metrics.json with peak_memory_mb. Run Instruments Allocations template. |
| energy | < 5.0% battery/hr | — | **unavailable** | No trace_metrics.json with energy data. Run Instruments Energy Log on physical device. |
| exact_match | >= 70% EM | — | **unavailable** | Quality metrics (EM, BLEU, hallucination rate) are not captured in device benchmark sessions. These require offline evaluation against ground-truth labels from data/manifests/. |
| model_size | < 100 MB | — | **unavailable** | Model size is not captured in device benchmark sessions. Requires measuring .mlpackage size after Core ML conversion (Phase 4). |

