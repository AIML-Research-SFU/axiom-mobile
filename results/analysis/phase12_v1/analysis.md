# AXIOM-Mobile Phase 6 Statistical Analysis Report

Generated: 2026-07-30T20:07:33Z
Version: 0.1.0
Overall status: **partial**

## Key Notes

- Learning-curve analysis is based on a small dataset (52 examples) with a heuristic lookup baseline. Results validate the pipeline but are not yet publication-ready.
- This analysis package is designed to absorb future physical-device data and larger-dataset runs with no code changes.

## 1. Learning-Curve / Scaling Analysis

**Status:** partial
**Reason:** 4 strategies analyzed across 6 budgets. Dataset is small (pool=681, test=40, val=30); results validate the pipeline but are not publication-ready.

Dataset: pool=681, val=30, test=40

### Strategy: diversity

| Budget | Test EM (mean) | 95% CI | Val EM |
|--------|---------------|--------|--------|
| 10 | 0.0425 | [0.010, 0.083] | 0.0767 |
| 25 | 0.3300 | [0.287, 0.367] | 0.3000 |
| 50 | 0.3275 | [0.310, 0.347] | 0.3533 |
| 100 | 0.3125 | [0.300, 0.325] | 0.3667 |
| 250 | 0.3500 | [0.325, 0.375] | 0.3333 |
| 500 | 0.3525 | [0.350, 0.357] | 0.3100 |

**Power-law fit:** complete — Power-law fit on 6 points. R^2=0.4859 (log-space).
  - y = 0.0417 * x^0.4044, R^2 = 0.4859

### Strategy: kg_guided

| Budget | Test EM (mean) | 95% CI | Val EM |
|--------|---------------|--------|--------|
| 10 | 0.1025 | [0.055, 0.150] | 0.0767 |
| 25 | 0.3025 | [0.258, 0.347] | 0.2533 |
| 50 | 0.3950 | [0.383, 0.407] | 0.2933 |
| 100 | 0.3850 | [0.372, 0.400] | 0.2967 |
| 250 | 0.3650 | [0.357, 0.372] | 0.3100 |
| 500 | 0.3500 | [0.350, 0.350] | 0.3000 |

**Power-law fit:** complete — Power-law fit on 6 points. R^2=0.4896 (log-space).
  - y = 0.0993 * x^0.2499, R^2 = 0.4896

### Strategy: random

| Budget | Test EM (mean) | 95% CI | Val EM |
|--------|---------------|--------|--------|
| 10 | 0.3150 | [0.273, 0.355] | 0.2633 |
| 25 | 0.3625 | [0.338, 0.385] | 0.2967 |
| 50 | 0.3700 | [0.357, 0.385] | 0.2933 |
| 100 | 0.3625 | [0.352, 0.372] | 0.3033 |
| 250 | 0.3625 | [0.352, 0.372] | 0.3100 |
| 500 | 0.3600 | [0.350, 0.370] | 0.3100 |

**Power-law fit:** complete — Power-law fit on 6 points. R^2=0.3623 (log-space).
  - y = 0.3194 * x^0.0245, R^2 = 0.3623

### Strategy: uncertainty

| Budget | Test EM (mean) | 95% CI | Val EM |
|--------|---------------|--------|--------|
| 10 | 0.0500 | [0.050, 0.050] | 0.0000 |
| 25 | 0.0500 | [0.050, 0.050] | 0.0000 |
| 50 | 0.0000 | [0.000, 0.000] | 0.0667 |
| 100 | 0.0250 | [0.025, 0.025] | 0.0333 |
| 250 | 0.0250 | [0.025, 0.025] | 0.0333 |
| 500 | 0.2750 | [0.275, 0.275] | 0.3667 |

**Power-law fit:** complete — Power-law fit on 5 points. R^2=0.1193 (log-space).
  - y = 0.0213 * x^0.2102, R^2 = 0.1193


## 2. Model and Strategy Comparisons

**Status:** partial

### Pairwise Strategy Comparisons (full-pool budget)

| Strategy A | Strategy B | Mean diff (A-B) | 95% CI | Seeds | Status |
|-----------|-----------|----------------|--------|-------|--------|
| diversity | kg_guided | 0.0025 | [0.0000, 0.0075] | 10 | complete |
| diversity | random | -0.0075 | [-0.0200, 0.0025] | 10 | complete |
| diversity | uncertainty | 0.0775 | [0.0750, 0.0825] | 10 | complete |
| kg_guided | random | -0.0100 | [-0.0225, 0.0000] | 10 | complete |
| kg_guided | uncertainty | 0.0750 | [0.0750, 0.0750] | 10 | complete |
| random | uncertainty | 0.0850 | [0.0750, 0.0975] | 10 | complete |


## 3. Device-Profile Performance

**Status:** complete
**Reason:** 3 simulator session(s), 3 physical-device session(s).

### Simulator Sessions (not publishable)

| Model | Records | p50 (ms) | p95 (ms) | Mean (ms) | Status |
|-------|---------|----------|----------|-----------|--------|
| tiny_multimodal_v0 | 20 | 199.5 | 304.2 | 220.2 | simulator_only |
| tiny_multimodal_v0 | 50 | 98.0 | 112.8 | 103.3 | simulator_only |
| tiny_multimodal_v1 | 50 | 125.0 | 229.5 | 148.1 | simulator_only |

### Physical-Device Sessions

| Model | Records | p50 (ms) | p95 (ms) | Mean (ms) | Status |
|-------|---------|----------|----------|-----------|--------|
| tiny_multimodal_v0 | 50 | 14.0 | 26.2 | 18.0 | complete |
| tiny_multimodal_v0 | 50 | 14.5 | 22.0 | 16.8 | complete |
| tiny_multimodal_v1 | 50 | 14.5 | 24.6 | 21.3 | complete |

**Memory:** physical_device_required — No physical-device Instruments Allocations trace with peak_memory_mb captured yet.
**Energy:** physical_device_required — Energy Log requires physical device. Instruments reports relative levels (0-20 scale), not battery %/hr. Not available from Simulator.


## 4. Pareto Analysis (Quality vs Efficiency)

**Status:** partial

| Model | Test EM | Latency p50 (ms) | Lat. Env | Size (MB) | Pareto? |
|-------|---------|------------------|----------|-----------|---------|
| question_lookup_v0 | 0.3500 | — | unavailable | 0.1 | Yes |
| axiom_lora_v1 | 0.3000 | — | unavailable | 2.04 | No |
| tiny_multimodal_v1 | 0.3500 | 14.5 | physical_device | 0.106 | Yes |


## Caveats and Limitations

1. **Physical-device latency measured.** 3 physical-device session(s) captured. Simulator data is retained for pipeline-validation context but is not used for conclusions.
2. **No statistical significance claims.** With 3 seeds and tiny test/val sets, bootstrap CIs are provided for honesty but should not be over-interpreted.
3. **No quality conclusions.** The 70% EM target from the research proposal is not met. The current heuristic baseline and tiny multimodal model both achieve ~10% test EM.
4. **No energy conclusions.** Energy Log data requires physical-device Instruments traces not yet captured.
5. **No memory conclusions.** Allocations trace data not yet captured on physical device.

