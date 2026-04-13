# AXIOM-Mobile Phase 6 Statistical Analysis Report

Generated: 2026-04-13T04:12:04Z
Version: 0.1.0
Overall status: **partial**

## Key Notes

- All device profiling is simulator-only. Physical-device evidence is required before publishing performance conclusions.
- Learning-curve analysis is based on a small dataset (52 examples) with a heuristic lookup baseline. Results validate the pipeline but are not yet publication-ready.
- This analysis package is designed to absorb future physical-device data and larger-dataset runs with no code changes.

## 1. Learning-Curve / Scaling Analysis

**Status:** partial
**Reason:** 3 strategies analyzed across 6 budgets. Dataset is small (pool=37, test=10, val=5); results validate the pipeline but are not publication-ready.

Dataset: pool=37, val=5, test=10

### Strategy: diversity

| Budget | Test EM (mean) | 95% CI | Val EM |
|--------|---------------|--------|--------|
| 5 | 0.0667 | [0.000, 0.100] | 0.0000 |
| 10 | 0.0667 | [0.000, 0.100] | 0.0000 |
| 15 | 0.1333 | [0.000, 0.200] | 0.0000 |
| 20 | 0.1333 | [0.000, 0.200] | 0.0000 |
| 25 | 0.0667 | [0.000, 0.100] | 0.0000 |
| 37 | 0.1000 | [0.100, 0.100] | 0.0000 |

**Power-law fit:** complete — Power-law fit on 6 points. R^2=0.1723 (log-space).
  - y = 0.0518 * x^0.2007, R^2 = 0.1723

### Strategy: random

| Budget | Test EM (mean) | 95% CI | Val EM |
|--------|---------------|--------|--------|
| 5 | 0.1000 | [0.000, 0.200] | 0.0000 |
| 10 | 0.0333 | [0.000, 0.100] | 0.0000 |
| 15 | 0.0667 | [0.000, 0.100] | 0.0000 |
| 20 | 0.0667 | [0.000, 0.100] | 0.0000 |
| 25 | 0.0667 | [0.000, 0.100] | 0.0000 |
| 37 | 0.1000 | [0.100, 0.100] | 0.0000 |

**Power-law fit:** complete — Power-law fit on 6 points. R^2=0.0192 (log-space).
  - y = 0.0548 * x^0.0784, R^2 = 0.0192

### Strategy: uncertainty

| Budget | Test EM (mean) | 95% CI | Val EM |
|--------|---------------|--------|--------|
| 5 | 0.0000 | [0.000, 0.000] | 0.0000 |
| 10 | 0.0000 | [0.000, 0.000] | 0.0000 |
| 15 | 0.0000 | [0.000, 0.000] | 0.0000 |
| 20 | 0.0000 | [0.000, 0.000] | 0.0000 |
| 25 | 0.0000 | [0.000, 0.000] | 0.0000 |
| 37 | 0.1000 | [0.100, 0.100] | 0.0000 |

**Power-law fit:** degenerate — Only 1 non-zero y values out of 6; power-law fit is meaningless on a degenerate curve.

> Strategy 'diversity': all validation EM values are 0.0. This is expected with the heuristic baseline on a small dataset where val examples don't overlap with memorized mappings.
> Strategy 'random': all validation EM values are 0.0. This is expected with the heuristic baseline on a small dataset where val examples don't overlap with memorized mappings.
> Strategy 'uncertainty': all validation EM values are 0.0. This is expected with the heuristic baseline on a small dataset where val examples don't overlap with memorized mappings.
> Skipped strategies: kg_guided. See selection sweep docs for reasons.

## 2. Model and Strategy Comparisons

**Status:** partial

### Baseline Comparison

| Model | Pool EM | Test EM | Val EM |
|-------|---------|---------|--------|
| question_lookup_v0 (heuristic) | 0.7297 | 0.1000 | 0.0000 |
| tiny_multimodal_v0 (trainable) | 0.1622 | 0.1000 | 0.0000 |

> Both models achieve 10% test EM (1/10 correct) and 0% val EM.
> The heuristic baseline's high pool EM (73%) reflects memorization, not generalization.
> Paired comparison is not applicable: different model architectures with a single run each.

### Pairwise Strategy Comparisons (full-pool budget)

| Strategy A | Strategy B | Mean diff (A-B) | 95% CI | Seeds | Status |
|-----------|-----------|----------------|--------|-------|--------|
| diversity | random | 0.0000 | [0.0000, 0.0000] | 3 | partial |
| diversity | uncertainty | 0.0000 | [0.0000, 0.0000] | 3 | partial |
| random | uncertainty | 0.0000 | [0.0000, 0.0000] | 3 | partial |


## 3. Device-Profile Performance

**Status:** simulator_only
**Reason:** 2 simulator session(s), 0 physical-device session(s).

### Simulator Sessions (not publishable)

| Model | Records | p50 (ms) | p95 (ms) | Mean (ms) | Status |
|-------|---------|----------|----------|-----------|--------|
| tiny_multimodal_v0 | 20 | 199.5 | 304.2 | 220.2 | simulator_only |
| tiny_multimodal_v0 | 50 | 98.0 | 112.8 | 103.3 | simulator_only |

### Physical-Device Sessions

**No physical-device sessions captured yet.** This is the primary remaining blocker for publishable results.

**Memory:** physical_device_required — No physical-device Instruments Allocations trace captured yet.
**Energy:** physical_device_required — Energy Log requires physical device. Instruments reports relative levels (0-20 scale), not battery %/hr. Not available from Simulator.

> All latency data is from Simulator only. These validate the instrumentation pipeline but are NOT publishable on-device evidence.

## 4. Pareto Analysis (Quality vs Efficiency)

**Status:** partial

| Model | Test EM | Latency p50 (ms) | Lat. Env | Size (MB) | Pareto? |
|-------|---------|------------------|----------|-----------|---------|
| question_lookup_v0 | 0.1000 | — | unavailable | 0.1 | Yes |
| tiny_multimodal_v0 | 0.1000 | 199.5 | simulator | 0.5 | Yes |

> All latency data is from Simulator. Pareto conclusions are preliminary and not publishable.

## What This Report Does NOT Prove

1. **No physical-device latency evidence.** All latency data is from iOS Simulator. Simulator has no NPU, no real thermal behavior, no meaningful energy data.
2. **No statistical significance claims.** With 3 seeds and tiny test/val sets, bootstrap CIs are provided for honesty but should not be over-interpreted.
3. **No quality conclusions.** The 70% EM target from the research proposal is not met. The current heuristic baseline and tiny multimodal model both achieve ~10% test EM.
4. **No energy/memory conclusions.** These require physical-device Instruments traces (Energy Log, Allocations).

