# Results Snapshot

Generated from: `results/analysis/phase6_v0/summary.json`
Analysis version: 0.1.0
Overall status: **partial**

## Dataset

- Pool: 37
- Val: 5
- Test: 10
- Fingerprint: `bcd03f5e07337b47...`

## Model Comparison

| Model | Pool EM | Test EM | Val EM |
|-------|---------|---------|--------|
| question_lookup_v0 | 0.7297 | 0.1000 | 0.0000 |
| tiny_multimodal_v0 | 0.1622 | 0.1000 | 0.0000 |

## Learning Curves (Test EM at Full Pool)

| Strategy | Full-Pool EM | Power-Law R^2 | Fit Status |
|----------|-------------|---------------|------------|
| diversity | 0.1000 | 0.1723 | complete |
| random | 0.1000 | 0.0192 | complete |
| uncertainty | 0.1000 | — | degenerate |

## Device Profiles

- Simulator sessions: 2
- Physical-device sessions: 0
- Best simulator p50: 98.0 ms (50 iterations, Release)
- **Physical-device data: NOT YET AVAILABLE**

## Pareto Summary

- Points: 2
- Status: partial
- question_lookup_v0: EM=0.100, latency=unavailable, size=0.1 MB
- tiny_multimodal_v0: EM=0.100, latency=199.5 ms (simulator), size=0.5 MB

## Caveats

- All device profiling is simulator-only. Physical-device evidence is required before publishing performance conclusions.
- Learning-curve analysis is based on a small dataset (52 examples) with a heuristic lookup baseline. Results validate the pipeline but are not yet publication-ready.
- This analysis package is designed to absorb future physical-device data and larger-dataset runs with no code changes.
