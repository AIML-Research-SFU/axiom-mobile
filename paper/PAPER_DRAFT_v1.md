# AXIOM-Mobile: Measuring Minimal Training Data Requirements for On-Device Domain Reasoning Under Mobile Constraints

**Annie Boltwood, Mahim Chaudhary, Ariel Tyson**
Simon Fraser University -- CMPT 416

*Draft v1 -- 2026-04-13. Numbers sourced from repo artifacts only. Simulator-only results are labeled throughout.*

---

## Abstract

We present AXIOM-Mobile, a system and experimental framework for measuring the minimal training set size (k\*) required for effective visual question answering on mobile devices under strict quality, latency, energy, and memory constraints. Our approach combines a SwiftUI + Core ML testbed app with a Python training/evaluation pipeline, enabling reproducible end-to-end experiments from dataset curation through on-device profiling. We compare three data selection strategies -- random sampling, uncertainty-based selection, and diversity-based selection -- across six label budgets using bootstrap confidence intervals and paired resampling. On our current 52-example dataset with a heuristic lookup baseline and a 40K-parameter multimodal model, no strategy achieves the 70% exact match target, establishing that substantially more training data and a stronger model architecture are needed. We report honest simulator-only latency profiles (p50 = 98 ms, p95 = 113 ms for the Core ML model) that validate the instrumentation pipeline, and identify physical-device profiling as the primary remaining blocker for publishable performance conclusions. All experiment code, analysis scripts, and reproducible artifacts are included in the repository.

---

## 1. Introduction

Mobile devices increasingly serve as primary computing platforms, yet deploying domain-specific reasoning models on-device faces a fundamental tension: achieving acceptable quality requires sufficient training data, while mobile deployment imposes hard constraints on latency, energy, memory, and model size that preclude large foundation models.

**Research question.** What is the minimal training set size k\* that achieves *effective* domain reasoning on mobile devices, where effectiveness is defined jointly over quality and device constraints?

**Operational definition of effective** (all must hold simultaneously):
- Exact Match (EM) >= 70% on held-out test set
- Latency: p50 <= 400 ms, p95 <= 600 ms per query (measured on physical device)
- Energy: < 5% battery drain per hour during continuous use
- Model size: < 100 MB total app footprint
- Memory: peak < 500 MB RAM during inference

This paper contributes:
1. An end-to-end iOS/macOS testbed app with real Core ML inference, benchmark mode, and structured CSV/metadata export for reproducible on-device evaluation.
2. A comparison of three selection strategies (random, uncertainty, diversity) across six label budgets with bootstrap confidence intervals.
3. A statistical analysis pipeline with an explicit status vocabulary that prevents accidental overstatement of results.
4. Honest reporting of current limitations: the 70% EM target is not met, all latency data is simulator-only, and physical-device profiling remains blocked.

---

## 2. Related Work

**Data-efficient learning.** Active learning and core-set methods have shown that strategic data selection can reduce annotation requirements while maintaining model quality [Sener and Savarese 2018; Ash et al. 2020]. Our work applies this principle to a mobile VQA setting where the effectiveness criterion includes device constraints beyond accuracy alone.

**On-device ML.** Core ML [Apple 2023] and TensorFlow Lite enable deploying models on mobile hardware, but most benchmarking studies report only accuracy or use desktop profiling. We measure latency, memory, and energy on the target hardware using Apple Instruments, following the methodology of [Ignatov et al. 2019] for mobile AI benchmarking.

**Visual question answering.** VQA tasks [Antol et al. 2015] typically assume server-side inference. Mobile VQA for domain-specific screenshots (app UIs, settings panels, notifications) is underexplored. Our dataset targets this niche with screenshot-question-answer triples grounded in real iOS content.

**Learning curves and scaling laws.** Power-law relationships between dataset size and performance are well-documented [Hestness et al. 2017; Kaplan et al. 2020]. We attempt power-law fits on our learning curves but report honestly when the data is too sparse or degenerate for meaningful extrapolation.

---

## 3. System Overview

AXIOM-Mobile consists of two components:

### 3.1 iOS/macOS App (SwiftUI + Core ML)

The app provides:
- **Screenshot import** from the photo library
- **Question input** for natural-language queries about the screenshot
- **Model picker** supporting multiple model backends
- **Real Core ML inference** via `CoreMLInferenceService` for models with bundled `.mlpackage` files
- **Benchmark mode** with configurable iterations (1-50), per-inference CSV logging, and structured metadata export
- **Auto-benchmark mode** (`--auto-benchmark`) for headless profiling workflows with deterministic benchmark input

The benchmark pipeline uses `BenchmarkInputProvider` for repeatable inputs: a persisted real screenshot from the app's Documents directory, or a deterministic 390x844 synthetic test pattern that exercises the full CVPixelBuffer resize/BGRA conversion pipeline.

### 3.2 Python Training and Analysis Pipeline

The Python side provides:
- **Dataset management** with JSONL manifests and split validation
- **Model harness** with a shared interface (`train()`, `predict()`, `export_coreml()`)
- **Selection strategies** (random, uncertainty, diversity) with a sweep runner
- **PyTorch -> Core ML export** with post-conversion accuracy gate (<= 3% drop)
- **Statistical analysis** with bootstrap CIs, paired comparisons, power-law fits, and Pareto views
- **Device-profile ingestion** with threshold evaluation against the effectiveness criteria

---

## 4. Dataset

### 4.1 Construction

We curated 52 screenshot-question-answer triples from real iOS app content. Each example consists of:
- A screenshot image (stored privately, not in the Git repository)
- A natural-language question about the screenshot content
- A ground-truth answer string

Screenshots were collected from diverse iOS apps and reviewed in two passes (v0 -> v1) with a shared Google Drive workflow.

### 4.2 Splits

The dataset is frozen at:

| Split | Count | Purpose |
|-------|-------|---------|
| Pool  | 37    | Available for selection/training |
| Val   | 5     | Held-out validation |
| Test  | 10    | Held-out evaluation |

There are 24 distinct answer classes across all examples.

### 4.3 Limitations

- **Scale.** 52 examples is far below the 500-example target in the original proposal. Learning curves and strategy comparisons on this dataset validate the pipeline but are not publication-ready.
- **Annotator agreement.** Dual-annotator agreement (Cohen's kappa >= 0.75) was planned but not implemented. Current labels reflect single-annotator judgments.
- **Answer granularity.** With 24 answer classes and 10 test examples, the random baseline for exact match is approximately 4%. The effective ceiling depends on answer distribution overlap between pool and test splits.

---

## 5. Models

### 5.1 Heuristic Baseline: question_lookup_v0

A zero-dependency lookup that memorizes the most common answer for each normalized training question, falling back to the global majority answer for unseen questions. This validates the experiment pipeline but has no visual understanding.

**Performance:**
- Pool EM: 72.97% (memorization, not generalization)
- Test EM: 10.00% (1/10 correct)
- Val EM: 0.00%

### 5.2 Trainable Baseline: tiny_multimodal_v0

A deliberately small (~40K parameters) multimodal model:
- **Image encoder:** 3-layer CNN (conv2d -> relu x3, adaptive avg pool) on 128x128 RGB -> 64-dim
- **Text encoder:** character-level embedding (ASCII, 128-vocab) + mean pool -> linear -> 64-dim
- **Fusion:** concatenation -> 128-dim
- **Head:** linear -> relu -> linear -> 24 classes

**Performance:**
- Pool EM: 16.22%
- Test EM: 10.00% (1/10 correct)
- Val EM: 0.00%
- Core ML artifact: 96 KB (well under 100 MB target)
- Parameters: ~40K (0.05M)

This model is designed to unblock the Core ML deployment pipeline, not to serve as the final research model. Its accuracy is low because it trains from scratch on 37 examples with no pretrained weights or transfer learning.

---

## 6. Selection Strategies

We compare three strategies for selecting training subsets from the pool:

| Strategy | Method | Implementation |
|----------|--------|----------------|
| Random (RAND) | Uniform random sampling | `random.sample(pool, k)` |
| Uncertainty (UNC) | Highest-entropy examples under current model | Prediction entropy ranking |
| Diversity (DIV) | Maximum feature-space coverage | k-center greedy selection |

A fourth strategy (KG-guided) is specified in the proposal but blocked pending knowledge graph infrastructure.

### 6.1 Sweep Configuration

- **Budgets:** k = {5, 10, 15, 20, 25, 37}
- **Seeds:** 3 per strategy-budget combination
- **Model:** question_lookup_v0 (heuristic, used as the baseline for the sweep)
- **Total runs:** 3 strategies x 6 budgets x 3 seeds = 54

---

## 7. Experiments

### 7.1 Offline Evaluation (Learning Curves)

Each sweep run trains on the selected subset and evaluates test EM. Results are averaged across 3 seeds with bootstrap 95% confidence intervals (10,000 resamples, percentile method).

**Table 1: Learning curves by strategy (test EM, mean +/- 95% CI)**

| Budget | Random | Diversity | Uncertainty |
|--------|--------|-----------|-------------|
| 5      | 0.100 [0.000, 0.200] | 0.067 [0.000, 0.100] | 0.000 [0.000, 0.000] |
| 10     | 0.033 [0.000, 0.100] | 0.067 [0.000, 0.100] | 0.000 [0.000, 0.000] |
| 15     | 0.067 [0.000, 0.100] | 0.133 [0.000, 0.200] | 0.000 [0.000, 0.000] |
| 20     | 0.067 [0.000, 0.100] | 0.133 [0.000, 0.200] | 0.000 [0.000, 0.000] |
| 25     | 0.067 [0.000, 0.100] | 0.067 [0.000, 0.100] | 0.000 [0.000, 0.000] |
| 37     | 0.100 [0.100, 0.100] | 0.100 [0.100, 0.100] | 0.100 [0.100, 0.100] |

All strategies converge to identical test EM (10%) at the full pool budget (k=37). The uncertainty strategy is degenerate at sub-pool budgets, producing zero test EM.

**Power-law fits** (y = a * x^b, log-log OLS):
- Diversity: a=0.052, b=0.201, R^2=0.172
- Random: a=0.055, b=0.078, R^2=0.019
- Uncertainty: degenerate (only 1 non-zero y value; fit not attempted)

The low R^2 values indicate that power-law scaling is not a good fit for this data, which is expected given the tiny dataset and the heuristic baseline's limited capacity for learning from additional examples.

### 7.2 Strategy Comparisons

Paired bootstrap comparison (matched by seed) at full-pool budget (k=37):

| Comparison | Mean diff | 95% CI | Seeds |
|-----------|-----------|--------|-------|
| Diversity - Random | 0.000 | [0.000, 0.000] | 3 |
| Diversity - Uncertainty | 0.000 | [0.000, 0.000] | 3 |
| Random - Uncertainty | 0.000 | [0.000, 0.000] | 3 |

No strategy differences are detectable. All comparisons are based on only 3 paired seeds and should not be interpreted as evidence of equivalence.

### 7.3 On-Device Latency

> **All latency measurements below are from iOS Simulator only. They validate the instrumentation pipeline but are NOT publishable on-device evidence. The Simulator has no Neural Processing Unit (NPU), no real thermal behavior, and no meaningful energy data.**

**Table 2: Simulator latency for tiny_multimodal_v0**

| Session | Iterations | Build | Input | p50 (ms) | p95 (ms) | Mean (ms) |
|---------|-----------|-------|-------|----------|----------|-----------|
| Session 1 | 20 | Debug | Blank | 199.5 | 304.2 | 220.2 |
| Session 2 | 50 | Release | Synthetic | 98.0 | 112.8 | 103.3 |

Session 2 (Release build, synthetic benchmark input exercising full preprocessing) is the more representative measurement. Both sessions pass the latency thresholds (p50 <= 400 ms, p95 <= 600 ms) on Simulator, but these results cannot be extrapolated to physical hardware.

### 7.4 Model Comparison (Pareto View)

**Table 3: Quality vs efficiency (preliminary)**

| Model | Test EM | Latency p50 (ms) | Lat. Env | Size (MB) | Pareto? |
|-------|---------|------------------|----------|-----------|---------|
| question_lookup_v0 | 0.100 | -- | N/A | 0.1 | Yes |
| tiny_multimodal_v0 | 0.100 | 199.5 | Simulator | 0.5 | Yes |

Both models are trivially Pareto-optimal because only two points exist and they have equal quality. The Pareto frontier will become meaningful once models with different quality-latency trade-offs are added.

---

## 8. Limitations and Threats to Validity

### 8.1 Quality Gap

The 70% EM target from the research proposal is not met. Both models achieve approximately 10% test EM. The primary causes are:
1. **Dataset scale:** 52 examples (37 pool) is insufficient for meaningful learning, especially for a model trained from scratch.
2. **Model capacity:** `tiny_multimodal_v0` (40K params, no pretrained weights) cannot learn visual patterns from 37 examples. It serves as pipeline validation, not a research model.
3. **Heuristic ceiling:** `question_lookup_v0` memorizes training questions but cannot generalize to unseen test questions, capping its test EM at the overlap between training and test question distributions.

### 8.2 Physical-Device Evidence

All latency data is from iOS Simulator. The following conclusions require physical-device profiling (currently blocked on iPhone USB connection):
- **Latency on real hardware** (Simulator has no NPU, different CPU scheduling)
- **Peak memory** (requires Instruments Allocations template on physical device)
- **Energy consumption** (requires Instruments Energy Log, not available on Simulator)
- **Thermal throttling effects** (no thermal management on Simulator)

### 8.3 Statistical Limitations

- **3 seeds per condition:** Bootstrap CIs are computed honestly but are unreliable with only 3 observations.
- **No dual-annotator agreement:** Labels are single-annotator; potential noise in ground truth.
- **No KG-guided strategy:** The fourth selection strategy is blocked on knowledge graph infrastructure.
- **Power-law fits are poor:** Low R^2 values indicate the current data does not support scaling law extrapolation.

### 8.4 Scope

- No ablation studies (single model architecture per category)
- No cross-validation (fixed splits only)
- No comparison to production VLMs (Florence, LLaVA, Qwen-VL remain config-only candidates)

---

## 9. Discussion

The primary contribution of this work at its current stage is **infrastructure validation**, not empirical results. We have demonstrated:

1. **An end-to-end reproducible pipeline** from dataset curation through Core ML deployment and on-device benchmarking, with structured exports and automated analysis.
2. **Honest status tracking** via an explicit vocabulary (complete, partial, blocked, simulator_only, degenerate, etc.) that propagates through all analysis outputs, preventing accidental overstatement.
3. **A statistical analysis framework** (bootstrap CIs, paired comparisons, power-law fitting with degenerate-data guards) that will absorb stronger results as the dataset and models scale.

The path to publishable empirical results requires:
- Scaling the dataset to 200+ screenshots / 500+ QA pairs
- Training a stronger model (LoRA-adapted VLM or similar)
- Physical-device profiling on iPhone hardware
- Instruments traces for memory and energy evaluation

---

## 10. Conclusion

We presented AXIOM-Mobile, a system for studying minimal training data requirements for on-device domain reasoning. The current implementation provides a fully functional iOS testbed with Core ML inference, a Python experiment pipeline with three selection strategies, and a statistical analysis package that honestly tracks what the data supports. While the 70% EM quality target and physical-device performance evidence remain outstanding, the infrastructure is complete and designed to absorb future improvements with no code changes.

---

## References

- Antol, S., et al. "VQA: Visual Question Answering." ICCV 2015.
- Apple. "Core ML Documentation." developer.apple.com/documentation/coreml, 2023.
- Ash, J. T., et al. "Deep Batch Active Learning by Diverse, Uncertain Gradient Lower Bounds." ICLR 2020.
- Hestness, J., et al. "Deep Learning Scaling is Predictable, Empirically." arXiv:1712.00409, 2017.
- Ignatov, A., et al. "AI Benchmark: All About Deep Learning on Smartphones." ICCV Workshop 2019.
- Kaplan, J., et al. "Scaling Laws for Neural Language Models." arXiv:2001.08361, 2020.
- Sener, O. and Savarese, S. "Active Learning for Convolutional Neural Networks: A Core-Set Approach." ICLR 2018.

---

## Appendix A: Reproduction

All results in this paper can be reproduced from the repository:

```bash
# 1. Run baseline experiments
python3 ml/scripts/run_baseline.py
python3 ml/scripts/run_trainable_baseline.py --image-root /path/to/screenshots_v1

# 2. Run selection sweep
python3 ml/scripts/run_selection_sweep.py

# 3. Export Core ML model
python3 ml/scripts/export_coreml.py \
    --checkpoint-dir results/trainable_baselines/tiny_multimodal_v0_seed0/checkpoint \
    --image-root /path/to/screenshots_v1

# 4. Run device profiling (requires iOS Simulator or physical device)
xcrun simctl launch booted com.arieljtyson.AXIOMMobile --auto-benchmark

# 5. Stage and summarize device profiles
python3 ml/scripts/stage_device_profile_session.py --from-simulator --device-name "iphone17pro-sim"
python3 ml/scripts/summarize_device_profiles.py

# 6. Run statistical analysis
python3 ml/scripts/run_statistical_analysis.py

# 7. Generate paper assets
python3 ml/scripts/build_paper_assets.py
```

## Appendix B: Dataset Fingerprint

```
Combined SHA-256: bcd03f5e07337b475b28fea85ca01b0a3bb05db3e2dd3657554834ef5231446f
Pool SHA-256:     3c0cdf8dee3aa3f490c703fd1d1be5815b5351e3d0a3d39140ac171101c3b069
Test SHA-256:     08ce04944cda6a707ce4cdce3f723d33cfa884a05820af44e1c4fdbc91971b48
Val SHA-256:      6274769fa8fb0b137fe00aa167a404b726d96a1c6a8e45e2dae9e0835b2a16dd
```
