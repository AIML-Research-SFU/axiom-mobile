---
marp: true
theme: default
paginate: true
---

# AXIOM-Mobile

## Minimal Data for On-Device Domain Reasoning

Annie Boltwood, Mahim Chaudhary, Ariel Tyson

Simon Fraser University -- CMPT 416

---

## Problem / Motivation

- Mobile devices are the primary computing platform for most users
- Domain-specific reasoning (e.g., answering questions about UI screenshots) requires training data
- Mobile deployment imposes hard constraints: latency, energy, memory, model size
- Core tension: high quality demands large datasets, but deployment demands small, fast models

---

## Research Question

**What is k\* -- the minimal training set size for effective on-device domain reasoning?**

"Effective" is defined jointly across all six thresholds:

| Metric | Threshold |
|--------|-----------|
| Exact Match (EM) | >= 70% |
| Latency p50 | <= 400 ms |
| Latency p95 | <= 600 ms |
| Energy | < 5% battery / hr |
| RAM | < 500 MB |
| Model size | < 100 MB |

---

## System Architecture

- **Two-component system**: iOS testbed app + Python ML pipeline
- **iOS app**: SwiftUI + Core ML, benchmark mode with CSV export
- **Python pipeline**: data curation, training, active-learning selection, CoreML export, statistical analysis
- **Automation**: auto-benchmark via launch arguments, demo-mode flag

---

## Dataset

- **52** screenshot-question-answer triples from real iOS applications
- **24** distinct answer classes
- Frozen split: 37 pool / 5 validation / 10 test
- Single-annotator labels (dual-annotator agreement with Cohen's kappa planned)
- Private screenshots stored off-repo (Google Drive)

---

## Models

| Model | Params | Core ML Size | Description |
|-------|--------|-------------|-------------|
| `question_lookup_v0` | -- | 0.1 MB | Heuristic memorization baseline |
| `tiny_multimodal_v0` | 40K | 96 KB | CNN + embedding, trained from scratch |

- Both achieve ~10% test EM
- Purpose: validate the end-to-end pipeline, not final accuracy

---

## Selection Strategies

- **Random (RAND)**: uniform sampling from the pool
- **Uncertainty (UNC)**: select examples with highest prediction entropy
- **Diversity (DIV)**: k-center greedy for maximum feature coverage
- **KG-guided**: blocked pending Knowledge Graph v1

**Sweep design**: 3 strategies x 6 budgets x 3 seeds = 54 runs

---

## Learning Curves

![Learning curves](assets/generated/learning_curves.svg)

- All strategies converge to ~10% test EM at full pool size
- Power-law fits: low R-squared (0.17 diversity, 0.02 random)
- Uncertainty: degenerate -- all-zero predictions except at budget = 37
- **Conclusion**: 52 examples are insufficient for quality differentiation

---

## On-Device Latency Results

**Device**: iPhone 15 Pro Max (A17 Pro, iOS 26.4.1)

| Session | p50 | p95 | Mean |
|---------|-----|-----|------|
| Cold start | 14.0 ms | 26.2 ms | 18.0 ms |
| Warm cache | 14.5 ms | 22.0 ms | 16.8 ms |

- Physical device is **7x faster** than simulator (14 ms vs 98 ms)
- All latency thresholds **PASS** with 28x margin

---

## Simulator vs Physical Device

| Environment | p50 | p95 | Mean | Status |
|-------------|-----|-----|------|--------|
| Simulator Debug | 199.5 ms | 304.2 ms | 220.2 ms | pipeline validation |
| Simulator Release | 98.0 ms | 112.8 ms | 103.3 ms | pipeline validation |
| Physical Cold | 14.0 ms | 26.2 ms | 18.0 ms | PASS |
| Physical Warm | 14.5 ms | 22.0 ms | 16.8 ms | PASS |

Simulator numbers are useful only for pipeline validation -- never for threshold evaluation.

---

## Effectiveness Threshold Scorecard

| Metric | Target | Measured | Status |
|--------|--------|----------|--------|
| EM >= 70% | 70% | 10% | FAIL |
| Latency p50 <= 400 ms | 400 ms | 14.0 ms | PASS |
| Latency p95 <= 600 ms | 600 ms | 26.2 ms | PASS |
| Energy < 5%/hr | 5%/hr | -- | UNAVAILABLE |
| Memory < 500 MB | 500 MB | -- | UNAVAILABLE |
| Size < 100 MB | 100 MB | 96 KB | PASS |

3/6 thresholds pass. 2/6 not yet measured. 1/6 fails (quality).

---

## Pareto View

| Model | EM | Latency (p50) | Size |
|-------|-----|---------------|------|
| `question_lookup_v0` | 10% | N/A | 0.1 MB |
| `tiny_multimodal_v0` | 10% | 14.0 ms | 0.5 MB |

- Both points are trivially Pareto-optimal (only two models)
- The frontier becomes meaningful once stronger models are added

---

## App Demo

- Screenshot import from Photos or camera
- Free-text question input with Core ML inference
- Real-time answer display with per-query latency
- Benchmark mode: batch evaluation with CSV export
- Design system: glass-morphism cards, staggered animations, haptic feedback, TipKit onboarding

---

## Statistical Methods

- **Bootstrap confidence intervals**: 10K resamples, percentile method
- **Paired bootstrap**: strategy-vs-strategy comparisons at each budget
- **Power-law scaling fits**: log-log OLS regression
- **Honest status vocabulary**: complete, partial, blocked, degenerate
- All outputs carry explicit status labels -- no silent failures

---

## Limitations

- **Quality gap**: 10% EM vs 70% target
- **Small dataset**: 52 examples (target: 500)
- **Model capacity**: 40K parameters, no pretrained backbone
- **Single annotator**: no inter-annotator agreement (Cohen's kappa)
- **Energy / memory**: not yet measured via Instruments
- **KG-guided strategy**: blocked on KG v1
- **Statistical power**: 3 seeds per condition (bootstrap CIs unreliable at this scale)

---

## Key Contributions

1. **End-to-end reproducible pipeline**: data curation through training, export, deployment, benchmarking, and analysis
2. **Physical-device latency evidence**: 14 ms p50 on A17 Pro -- 28x below threshold
3. **Honest status tracking**: explicit vocabulary prevents overstatement of partial results
4. **Infrastructure ready**: pipeline supports stronger models and larger datasets without architectural changes

---

## Next Steps

- Scale dataset to 200+ screenshots / 500+ QA pairs
- Train a stronger model (LoRA-adapted VLM or equivalent)
- Collect Instruments traces for memory and energy thresholds
- Build KG v1 infrastructure for KG-guided selection strategy
- Format and submit paper to target venue

---

## Thank You

**Repository**: [axiom-mobile on GitHub](https://github.com/arieltyson/axiom-mobile)

Annie Boltwood, Mahim Chaudhary, Ariel Tyson

Simon Fraser University -- CMPT 416

Questions?
