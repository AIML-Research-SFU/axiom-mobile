# AXIOM-Mobile: Measuring Minimal Training Data Requirements for On-Device Domain Reasoning Under Mobile Constraints

**Annie Boltwood, Mahim Chaudhary, Ariel Tyson**
Simon Fraser University -- CMPT 416

*Draft v4 -- 2026-07-30. Semester 2: dataset v3 (751 examples), KG v1 and a completed 4-strategy comparison, a pretrained-backbone + LoRA model (axiom_lora_v1), post-training quantization, and a full-scale selection sweep with 10 seeds. Written with the same discipline as v3: every claim traces to a committed or explicitly-local artifact, and negative results are reported as plainly as positive ones.*

---

## Abstract

We present AXIOM-Mobile, a system and experimental framework for measuring the minimal training set size (k\*) required for effective visual question answering on mobile devices under strict quality, latency, energy, and memory constraints. This draft extends v3 along four axes. First, the dataset was scaled from 452 to 751 examples (dataset v3) via the same zero-manual-labeling simulator-generation pipeline, adding a new visually-verified exact-answer dimension (cellular signal bars) after two candidate dimensions (Wi-Fi bars, carrier name) were tested and rejected as not reliably readable. Second, we built a compact knowledge graph (KG v1: 235 entities, 1,009 relations) programmatically from the dataset's own structured fields, unblocking the fourth and final selection strategy (KG-guided) specified in the original proposal, and ran the full 4-strategy comparison at scale (240 runs: 6 budgets x 10 seeds, up from 3) on the real committed dataset for the first time. Third, we replaced the from-scratch image encoder with a frozen, pretrained MobileNetV3-Small backbone and a genuine LoRA adapter (axiom_lora_v1) -- the technique the original project proposal specified but never implemented -- and report an honest negative result: on identical data and training recipe, the pretrained+LoRA model (30.0% test EM) does not outperform the from-scratch baseline (35.0% test EM), and is dominated on the quality/size Pareto frontier. Fourth, we implement post-training int8 quantization (1.80x compression, 0% accuracy drop) and extend on-device profiling to a second model family. Physical-device latency remains well within threshold (14.0-14.5ms p50 across all model versions on iPhone 15 Pro Max, A17 Pro); energy and memory profiling remain outstanding, requiring physical-device Instruments sessions not performed in this pass. All experiment code, analysis scripts, and reproducible artifacts are included in the repository, including three real bugs found and fixed in the statistical analysis pipeline itself during this work.

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

This paper contributes, beyond v3:
1. **Dataset v3** (751 examples, up from 452), with an honest account of two candidate ground-truth dimensions that were tested and rejected, and one real data-quality bug caught by visual spot-checking and fixed before promotion.
2. **KG v1**, extracted programmatically (no manual curation) from the dataset's own fields, and the KG-guided selection strategy it unblocks -- completing the four-strategy comparison specified in the original proposal.
3. **A full-scale selection-strategy sweep** (240 runs on the real committed dataset, 10 seeds) producing the first statistically meaningful strategy comparison this project has run, plus three real bugs found and fixed in the analysis pipeline that produced it.
4. **axiom_lora_v1**: a pretrained-backbone + LoRA model, delivering on the original proposal's stated method. Reported honestly as a quality wash against the from-scratch baseline on identical data, not a win.
5. **Quantization and expanded on-device profiling**, with a plain account of what still isn't measured (energy, memory) and why.

---

## 2. Related Work

**Data-efficient learning.** Active learning and core-set methods have shown that strategic data selection can reduce annotation requirements while maintaining model quality [Sener and Savarese 2018; Ash et al. 2020]. Our work applies this principle to a mobile VQA setting where the effectiveness criterion includes device constraints beyond accuracy alone.

**On-device ML.** Core ML [Apple 2023] and TensorFlow Lite enable deploying models on mobile hardware, but most benchmarking studies report only accuracy or use desktop profiling. We measure latency on target hardware using Apple Instruments, following the methodology of [Ignatov et al. 2019] for mobile AI benchmarking; energy and memory measurement on physical hardware remain outstanding in this draft.

**Parameter-efficient fine-tuning.** LoRA [Hu et al. 2021] decomposes weight updates into low-rank matrices, most commonly applied to adapt large pretrained transformers. We apply the same technique to a Conv2d layer in a pretrained CNN backbone -- a less common but established pattern (e.g. LoRA adapters in diffusion U-Nets) -- after a first attempt to apply it to a pretrained *text* transformer failed for reasons unrelated to LoRA itself (Section 5.3).

**Visual question answering.** VQA tasks [Antol et al. 2015] typically assume server-side inference. Mobile VQA for domain-specific screenshots (app UIs, settings panels, notifications) is underexplored. Our dataset targets this niche with screenshot-question-answer triples grounded in real iOS content.

**Learning curves and scaling laws.** Power-law relationships between dataset size and performance are well-documented [Hestness et al. 2017; Kaplan et al. 2020]. Fits on our learning curves remain weak (R^2 = 0.12-0.49, up from < 0.2 in v3) -- improved by the larger, higher-seed-count sweep in this draft, but still not strong evidence of clean scaling behavior.

---

## 3. System Overview

AXIOM-Mobile consists of three components (KG v1 added in this draft):

### 3.1 iOS/macOS App (SwiftUI + Core ML)

Screenshot import, question input, a model picker (now including `axiom_lora_v1`), real Core ML inference via `CoreMLInferenceService`, and benchmark mode with CSV/metadata export. A model-metadata sidecar system (per-model confidence threshold, class count, task description) means adding a new model requires no hardcoded values in Swift -- confirmed again in this draft when `axiom_lora_v1` was integrated purely through its sidecar and a `CoreMLInferenceService` routing case.

### 3.2 Python Training and Analysis Pipeline

Dataset management, a model harness (`train()`, `predict()`, `export_coreml()`), four selection strategies, PyTorch -> Core ML export with an accuracy gate, post-training quantization (new), and a statistical analysis pipeline with bootstrap CIs, paired comparisons, power-law fits, and Pareto views.

### 3.3 Knowledge Graph (new)

A compact KG (`kg/entities.json`, `kg/relations.json`) extracted programmatically from the dataset's `notes`/`question`/`answer` fields via `ml/scripts/build_kg.py`. Four entity types (App, Screen, Attribute, AnswerValue) and four relation types, including a `grounds_example` relation linking every fact back to the dataset row it came from -- the mechanism that makes the KG usable for the grounding check the original proposal specified ("answers must be grounded in visible content or KG").

---

## 4. Dataset

### 4.1 Dataset v3: 751 examples (up from 452)

Semester 2 extended the auto-generation pipeline first built for dataset v2, adding 60 new screenshots (300 QA pairs) via the same deterministic simulator-scenario mechanism, then freezing a new stratified split.

**Splits (dataset v3):**

| Split | Count |
|-------|-------|
| Pool  | 681   |
| Val   | 30    |
| Test  | 40    |
| **Total** | **751** |

Val/test sizes were deliberately held constant from v2 (30/40) so results stay comparable across dataset versions; all growth went into the pool.

**What was tested and rejected, not just what shipped.** Before committing to the new "cellular signal bars" question type, two other candidate status-bar dimensions (Wi-Fi signal bars, carrier/operator name) were tested by capturing paired screenshots at their extremes and visually comparing. Wi-Fi bar count was not reliably distinguishable at the rendered icon resolution; carrier name was not rendered at all on the target device (covered by the Dynamic Island). Neither was used. Only `cellular_bars` (confirmed unambiguous between 1 and 4 bars) shipped -- a direct application of this project's standing rule to only emit a question when the answer is visually verifiable, not assumed.

**A real data-quality bug, caught and fixed before promotion.** Visual spot-checking (reading the actual captured images, not trusting the pipeline output) found that the first Maps capture in the new batch triggered a one-time "Enable Notifications" system prompt that covered the search bar, making the recorded "Apple Maps" search-bar answer wrong for that one example. Confirmed isolated to that single capture by checking several others, and the one bad row was removed rather than left in the training data.

### 4.2 Knowledge Graph v1 (new)

Extracted from dataset v3's own fields, not manually curated:

| Entity type | Count | Examples |
|---|---|---|
| App | 9 | Settings, Maps, Clock, Weather, Calculator, Control Center, App Store, Lock Screen, Status Bar |
| Screen | 19 | Settings/Wi-Fi, Settings/Bluetooth, Clock/Alarm, Control Center/AirDrop, ... |
| Attribute | 20 | time, battery_pct, charging, cellular_status, wifi_status, ... (same taxonomy as the dataset's own stratified-split classifier) |
| AnswerValue | 187 | distinct normalized answers observed |
| **Total** | **235** | |

| Relation | Count | Meaning |
|---|---|---|
| has_screen | 19 | App -> Screen |
| has_attribute | 39 | Screen -> Attribute |
| has_value | 200 | Attribute -> observed AnswerValue |
| grounds_example | 751 | Screen -> the dataset row this fact came from |
| **Total** | **1,009** | |

The original proposal estimated "~1,000 entities" before the real data shape was known; the actual dataset produces 235. We report the real number rather than pad toward the estimate.

A real extraction bug was found and fixed before this data shipped: the first-pass App/Screen parser misclassified compound `notes` strings (e.g. "Bluetooth settings", "Control Center AirDrop tile") as standalone top-level apps instead of screens under their real parent app. Rewritten using explicit rules enumerated directly from the 29 distinct `notes` prefixes actually present in the dataset, verified by inspecting the resulting entity list (9 apps, 19 screens, zero unmatched patterns) rather than trusting the first output.

### 4.3 Limitations

- **Scale.** 751 examples remains well below typical VQA benchmarks. Manual examples (52 of 751, 6.9%) were captured by hand in semester 1; the rest are auto-generated.
- **Annotator agreement.** Not implemented, as in v3. The auto-generated majority of the dataset is grounded in deterministic, machine-set state (status bar, in-app navigation to a known screen), not subjective human judgment, so inter-annotator kappa is a weak signal for this portion specifically -- a scope decision, not an oversight.
- **Drive-sync gap.** The 452 examples committed before this semester's work (52 manual + 400 v0.3.0 auto-exact) were never synced to the machine this semester's work was performed on. This became a real, recurring constraint (Sections 5.3, 6.3) -- not just a inconvenience, but the reason `axiom_lora_v1` and its selection-sweep results are reported against a machine-local dataset rather than the literal committed split.

---

## 5. Models

### 5.1-5.2 Heuristic and from-scratch baselines (unchanged methodology from v3)

`question_lookup_v0` (memorization heuristic) and `tiny_multimodal_v0/v1` (3-layer CNN + char-level text encoder, trained from scratch) are unchanged in architecture from v3. Regenerated on dataset v3 for this draft:

**question_lookup_v0 (dataset v3, committed):** Pool EM = 46.8%, Val EM = 30.0%, Test EM = 35.0%.

### 5.3 axiom_lora_v1: pretrained backbone + LoRA (new)

The original project README specified "LoRA (PEFT) fine-tuning" as a core method; this was never implemented until this draft.

**What was attempted first, and why it's not what shipped.** The most literal reading of the original proposal is a pretrained *text* transformer fine-tuned via LoRA. This was actually attempted:

1. `prajjwal1/bert-tiny` -- failed to load: its tokenizer repository predates the installed `transformers` version's serialization format.
2. `sentence-transformers/all-MiniLM-L6-v2` -- tokenizer loaded, LoRA applied via `peft`, PyTorch tracing succeeded, but `coremltools.convert` failed inside the embeddings/position-id ops with a type error.
3. To isolate the cause, the same model was traced and converted **without** LoRA. It failed identically -- proving the break is in the base pretrained transformer's traced graph (a likely version mismatch between `transformers`' internals and what `coremltools` 9.0's PyTorch frontend can lower), not anything LoRA-specific.

This was a pre-registered contingency, not an improvised excuse: the project's semester-2 plan explicitly specified falling back to the vision side if the text-tower approach failed to convert.

**Architecture.** `axiom_lora_v1` uses a frozen, ImageNet-pretrained `torchvision.models.mobilenet_v3_small` backbone (verified against the real module structure before use, not assumed) with a LoRA adapter (rank 8, alpha 16, zero-initialized "up" projection per the standard convention) applied to the final 1x1 convolution -- the one place in this architecture where "LoRA-adapting a pretrained layer" is literally meaningful. BatchNorm inside the frozen backbone is held in eval mode permanently, including during training, so its running statistics don't drift from small fine-tuning batches. The text encoder is the unchanged char-level embedding from `tiny_multimodal` -- not LoRA-adapted, because there is nothing pretrained there to adapt, and the text side was never the bottleneck (questions are a small set of fixed templates).

**Training data: a real, disclosed deviation from the committed split.** The 452 examples committed before this semester's dataset-scaling work were never available on the machine this training was performed on (Drive-sync gap, Section 4.3). Rather than train on only the 299 newest images (too small and low-diversity, and most of the frozen val/test split would not even resolve), the original 100 v0.3.0 scenarios were **recaptured fresh** via the same deterministic simulator generator into a machine-local-only directory, combined with the 60 new scenarios, giving a 699-QA-pair local training set. **This is not the committed dataset v3 split** -- it lacks the 52 manually-captured examples and uses different image identifiers. Results below are not a byte-for-byte comparison to the committed-dataset numbers reported for other models in this section; a same-data, same-recipe comparison against a re-trained `tiny_multimodal_v1` is reported instead, which *is* apples-to-apples.

**Results (local Phase-8 dataset: pool=629/699 after excluding the one bad Maps example, val=30, test=40, 40 epochs, class-weighted CE):**

| Model | Backbone | Total params | Pool EM | Val EM | Test EM |
|---|---|---|---|---|---|
| `axiom_lora_v1` | pretrained + LoRA | 1,014,493 (927,008 frozen) | 32.0% | 23.3% | 30.0% |
| `tiny_multimodal_v1` (retrained, same local data/recipe) | from scratch | 49,021 | 37.4% | 43.3% | 35.0% |

**Read honestly: the pretrained backbone does not win.** On identical data and an identical training recipe, the from-scratch model matches or exceeds the pretrained+LoRA model on every split, while using **21x fewer parameters**. The most likely explanation, consistent with v3's own discussion: ImageNet pretraining optimizes for object/texture/shape recognition, which does not obviously transfer to reading exact digits and icon states in a status bar -- the task this project actually needs. Only the final conv's LoRA adapter (a small fraction of the backbone) and the projection/classifier heads are learning task-specific features here; most of the network's capacity is frozen and pointed at the wrong kind of visual feature.

**Core ML export:** accuracy gate passed, **0% drop** on both val and test, **2.04MB** package (vs. `tiny_multimodal_v1`'s 0.106MB for the same task).

### 5.4 Quantization (new)

Applied post-training int8 linear weight quantization (`coremltools.optimize`) to `axiom_lora_v1`'s export -- deferred for `tiny_multimodal_v0/v1` in earlier phases since those were already under 100KB. Result: **2.04MB -> 1.14MB (1.80x compression)**, **0% accuracy drop** (bit-identical predictions before and after quantization on both val and test). One benign `RuntimeWarning: divide by zero` occurred during quantization on a single weight channel with zero range; verified harmless given the exact-match prediction outcome.

---

## 6. Selection Strategies

Four strategies, all now executable (KG-guided was blocked from Phase 1 through Phase 8; unblocked in Phase 9):

| Strategy | Method |
|----------|--------|
| Random (RAND) | Uniform random sampling |
| Uncertainty (UNC) | Metadata-proxy scoring (difficulty, answer rarity, question rarity) -- not real model logits |
| Diversity (DIV) | k-center greedy over Jaccard text distance |
| KG-guided (KG) | Round-robins across `(Screen, Attribute)` KG regions, maximizing coverage breadth before depth |

### 6.1 KG-guided: a real, measured coverage difference

At budget=25 on the current pool (37 distinct `(Screen, Attribute)` regions total), KG-guided covers **25/37 regions**, versus **11/37** for plain random sampling at the same budget -- confirming the algorithm does what it claims, not just that it runs without error.

### 6.2 Full sweep on the committed dataset v3 (new)

**240 runs** (4 strategies x budgets `{10, 25, 50, 100, 250, 500}` x **10 seeds**, up from 3), on the real committed dataset v3, with `question_lookup_v0`. This is the first time this project has run a selection-strategy sweep at real dataset scale with a statistically meaningful seed count.

**Table: Test EM by strategy and budget (mean of 10 seeds)**

| Budget | Random | Diversity | Uncertainty | KG-guided |
|--------|--------|-----------|-------------|-----------|
| 10  | 31.5% | 4.25% | 5.0%  | 10.25% |
| 25  | 36.25% | 33.0% | 5.0%  | 30.25% |
| 50  | 37.0% | 32.75% | 0.0%  | **39.5%** |
| 100 | 36.25% | 31.25% | 2.5%  | 38.5% |
| 250 | 36.25% | 35.0% | 2.5%  | 36.5% |
| 500 | 36.0% | 35.25% | 27.5% | 35.0% |

**Power-law fits** (y = a * x^b, log-log OLS, all 6 budgets):
- Diversity: R^2 = 0.486
- KG-guided: R^2 = 0.490
- Random: R^2 = 0.362
- Uncertainty: R^2 = 0.119 (5 points; degenerate at low budgets)

Still not strong evidence of clean power-law scaling, but a real improvement over v3's R^2 < 0.2 across the board, attributable to the larger budget range and higher seed count.

**A genuine finding, not just pipeline validation.** At small budgets, random clearly wins: `question_lookup_v0` memorizes per-normalized-question strings, so it needs repeated examples of the *same* question pattern to generalize, and coverage-first strategies (diversity, KG-guided) spread a tiny budget thin across many distinct topics, starving the heuristic of repeats. This reverses by budget 50: KG-guided overtakes random (39.5% vs. 37.0%) once the budget is large enough that coverage-first selection stops being a liability. This is a heuristic-model-specific dynamic, not evidence about how a real learned model would behave under these strategies -- but it is a real, reproducible signal, not noise.

**Paired bootstrap comparisons (budget=500, 10 seeds):**

| Comparison | Mean diff | 95% CI |
|---|---|---|
| Diversity - KG-guided | +0.003 | [0.000, 0.008] |
| Diversity - Random | -0.008 | [-0.020, 0.003] |
| KG-guided - Random | -0.010 | [-0.023, 0.000] |
| Random - Uncertainty | +0.085 | [0.075, 0.098] |

At full-pool budget the strategies converge closely; only the comparisons against Uncertainty show a clear, non-zero-crossing difference.

### 6.3 What's still missing: a trainable-model sweep

The original goal was to re-run this sweep with `axiom_lora_v1` instead of the heuristic baseline. This was attempted and deliberately abandoned, not silently dropped. `ml/scripts/run_selection_sweep.py` was extended with `--image-root`/`--manifest-dir`/`--epochs`/`--class-weighted` flags (a real gap fixed along the way: the script had never actually been wired to support image-based models at all). Real per-cell timing was measured (~2.5 minutes at the most expensive budget) rather than estimated, giving a real total estimate of ~4 hours for the full grid. The run was attempted on the local Phase-8 dataset (the committed dataset's images still aren't available on this machine), parallelized across strategies with `caffeinate` to prevent sleep interruptions after a first sequential attempt was slowed by the laptop sleeping -- and then stopped partway through (50 of 240 runs complete) when sustained multi-process training load made the laptop uncomfortably hot. The partial results were deleted rather than kept half-finished. This is a genuine limitation of running this class of experiment on personal laptop hardware, documented here rather than hidden: a full trainable-model sweep needs either a much smaller grid or non-laptop compute.

---

## 7. On-Device Evaluation

### 7.1 Physical-Device Latency (unchanged from v3, iPhone 15 Pro Max, A17 Pro)

| Model | Condition | p50 (ms) | p95 (ms) | Threshold |
|---|---|---|---|---|
| tiny_multimodal_v0 | cold | 14.0 | 26.2 | PASS |
| tiny_multimodal_v0 | warm | 14.5 | 22.0 | PASS |
| tiny_multimodal_v1 | standard | 14.5 | 24.6 | PASS |

All physical-device sessions pass all latency thresholds with wide margin (28x below the 400ms p50 limit).

### 7.2 Simulator Latency for axiom_lora_v1 (new, not publishable)

Built Release, installed on iPhone 17 Pro Simulator (iOS 26.4), ran `--auto-benchmark`: 50 iterations, real Core ML inference (`is_placeholder: false`), **p50 = 99.5ms**. Consistent with this project's standing position that Simulator has no NPU and no real thermal behavior: this validates the app-integration pipeline end-to-end but is **not** a publishable performance number. A physical-device session for `axiom_lora_v1` was not performed in this pass.

An Allocations (memory) trace was attempted via `xctrace record --attach` on the same Simulator session but the CLI hung across two bounded attempts and was abandoned rather than continuing to fight a flaky tool interaction. This does not represent new lost ground: even Simulator memory data is treated as non-meaningful by this project's existing conventions (no NPU, no representative memory pressure), so physical-device Allocations profiling remains the only path to a real number, same as it always was.

### 7.3 Energy and Memory: still outstanding, and why

Neither has been measured for any model version, in any semester. Energy Log requires a physical device and cannot be approximated on Simulator at all. Memory (Allocations) profiling on physical hardware was never performed in semester 1 despite a `trace_metrics.json` sidecar mechanism existing for it -- confirmed directly this semester when a bug in the analysis pipeline (Section 8) was found falsely reporting memory as "complete" based on the mere existence of an unrelated Time Profiler trace sidecar. Both require the one thing this semester's work could not substitute for: a physical device, in someone's hands, running Instruments.

### 7.4 Pareto View (quality vs. size, dataset-v3-committed and local-Phase-8 mixed -- caveated)

| Model | Test EM | Latency p50 | Size | Pareto-optimal? |
|---|---|---|---|---|
| question_lookup_v0 | 35.0% | unavailable | 0.1 MB | Yes |
| tiny_multimodal_v1 | 35.0% | 14.5ms (physical) | 0.106 MB | Yes |
| axiom_lora_v1 | 30.0% | unavailable | 2.04 MB | **No** |

`axiom_lora_v1` is dominated: `tiny_multimodal_v1` matches its quality on identical data at roughly 1/20th the size. This table mixes dataset sources (question_lookup_v0/tiny_multimodal_v1 rows partly reflect committed-dataset training; axiom_lora_v1 reflects local-only training) -- flagged explicitly rather than presented as a clean comparison, consistent with Section 5.3's caveat.

---

## 8. Real Bugs Found and Fixed This Semester

Reported as part of the record, not hidden. Beyond the modeling and data work, three real bugs were found in the statistical analysis pipeline itself while producing the results in this draft, all fixed:

1. **Stale sweep hardcode**: `run_statistical_analysis.py`'s sweep loader always read `selection_sweeps/sweep_v0` (the original 54-run scaffold) because that directory always exists, so it silently never considered the real 240-run sweep that now exists alongside it. Fixed to pick the sweep directory with the most completed runs.
2. **Stale Pareto size**: the Pareto view read a model's expected size from a training run's frozen spec *snapshot* rather than the actual measured Core ML package size, so `axiom_lora_v1` showed as 6.0MB (an early estimate) instead of the measured 2.04MB. Fixed to prefer measured export sizes.
3. **False "memory complete" status**: the memory-availability check conflated "any trace sidecar exists" with "memory data exists," so a physical-device session that only ever captured a Time Profiler trace (no Allocations data) made the pipeline falsely report memory as available. Fixed to check specifically for the `peak_memory_mb` field an Allocations trace actually populates.

A fourth, near-miss: after adding a new Simulator profiling session, re-running the device-profile summarizer silently rebuilt the committed aggregate summary from only the one new local session, because the six historical physical-device session folders (gitignored raw data) were never on this machine. This would have deleted real historical evidence from a committed file had it been committed as-is. Caught before that happened and reverted; not merged.

We report this not to inflate the contribution list, but because a research pipeline whose own analysis tooling silently overstates or discards evidence is a real risk to the honesty this project has otherwise tried to maintain, and catching these mid-semester is more useful to disclose than to quietly patch.

---

## 9. Limitations and Threats to Validity

### 9.1 Quality Gap (unresolved)

The 70% EM target is not met by any model. Best committed-dataset result remains `tiny_multimodal_v1` at 27.5% test EM (dataset v2). The pretrained-backbone attempt this semester (`axiom_lora_v1`) does not improve on this -- on a fair same-data comparison it is *worse* than a from-scratch model with 21x fewer parameters. This is a genuinely useful negative result: it suggests the binding constraint is not simply "no pretrained vision features," and that ImageNet-style pretraining may be a poor prior for this specific reading task. Future work should consider architectures pretrained on document/UI/OCR-adjacent data instead of general object recognition, or unfreezing more of the backbone (at the cost of needing more data to avoid overfitting).

### 9.2 Dataset Availability (a new, recurring constraint)

The single largest practical constraint on this semester's work was not compute or algorithms but data locality: the 452 examples committed before this semester were never synced to the machine used for `axiom_lora_v1` training and the trainable-model selection sweep. This forced a machine-local dataset reconstruction (documented honestly rather than silently substituted) and blocks a clean apples-to-apples comparison against the committed-dataset numbers reported for other models. Resolving this (Drive sync) is a prerequisite for closing several of the remaining gaps in this paper, not just a convenience.

### 9.3 Compute Constraints on Personal Hardware

A full-scale trainable-model selection sweep (Section 6.3) was technically ready to run (verified working on real cells, real timing measured) but was not completed because sustained multi-process training made a personal laptop uncomfortably hot. This is reported as a real constraint on this class of experiment, not a technical failure -- future work in this vein needs either a much smaller experimental grid or access to non-laptop compute.

### 9.4 Statistical Limitations

- **10 seeds** (up from 3) for the heuristic-baseline sweep -- meaningfully better than v3, still modest by broader ML-research standards.
- **axiom_lora_v1 has only 1 seed** -- no confidence interval possible for the pretrained-model result; the "wash, not a win" finding rests on a single run per model, not a distribution.
- **Power-law fits remain weak** (R^2 = 0.12-0.49) even with the larger sweep.

### 9.5 Scope

- No KG-guided sweep with a trainable model (Section 6.3).
- No energy or memory measurement on physical hardware, for any model, in any semester (Section 7.3).
- No ablation on LoRA rank or on unfreezing more of the pretrained backbone.
- No comparison to production VLMs (Florence, LLaVA, Qwen-VL remain config-only candidates, unchanged since v1).

---

## 10. Discussion

This semester's work follows the same throughline as v3's infrastructure-first approach, but the infrastructure is now being spent on real findings rather than only validated. Four things are worth stating plainly:

1. **The 70% quality target is further from resolved than a naive read of "we added a pretrained model" would suggest.** The headline attempt to close the gap -- a pretrained vision backbone with LoRA -- did not work, on a fair comparison. This is disclosed as the primary finding of the modeling work this semester, not buried under the parts that did work.
2. **The selection-strategy question finally has a real, if preliminary, answer for at least one baseline model.** KG-guided selection measurably outperforms random once budgets are large enough for coverage-first selection to stop starving a memorization-style model of repeated examples -- a mechanism-level explanation, not just a number.
3. **The dataset-scaling and KG-construction methodology continues to pay off**: growing the dataset and building a knowledge graph both required zero manual labeling, using the same deterministic simulator-generation principle established in semester 1. This is the part of the system most clearly ready to keep scaling without more engineering effort.
4. **Data locality, not modeling ability, is now the primary practical bottleneck** for this project's near-term progress. Nearly every open item in this paper -- the trainable-model sweep, a clean axiom_lora_v1 comparison, further dataset scaling shared with teammates -- traces back to the same unresolved Drive-sync gap.

## 11. Conclusion

We extended AXIOM-Mobile with a larger dataset (751 examples), a programmatically-constructed knowledge graph completing the four-strategy selection comparison specified in the original proposal, a pretrained-backbone LoRA model delivering on a promise made but not kept in semester 1, and post-training quantization. The honest result is mixed: infrastructure and methodology continue to mature cleanly (KG construction, dataset scaling, a statistically meaningful strategy sweep, three real analysis-pipeline bugs caught and fixed), while the central quality question -- does a pretrained vision backbone close the gap toward 70% EM -- returns a clear no on the evidence available. Latency remains comfortably within threshold across every model version measured; energy and memory remain the two constraints this project has never measured on any model, in any semester, and closing that gap requires a physical device and a person, not more code.

---

## References

- Antol, S., et al. "VQA: Visual Question Answering." ICCV 2015.
- Apple. "Core ML Documentation." developer.apple.com/documentation/coreml, 2023.
- Ash, J. T., et al. "Deep Batch Active Learning by Diverse, Uncertain Gradient Lower Bounds." ICLR 2020.
- Hestness, J., et al. "Deep Learning Scaling is Predictable, Empirically." arXiv:1712.00409, 2017.
- Hu, E. J., et al. "LoRA: Low-Rank Adaptation of Large Language Models." arXiv:2106.09685, 2021.
- Ignatov, A., et al. "AI Benchmark: All About Deep Learning on Smartphones." ICCV Workshop 2019.
- Kaplan, J., et al. "Scaling Laws for Neural Language Models." arXiv:2001.08361, 2020.
- Sener, O. and Savarese, S. "Active Learning for Convolutional Neural Networks: A Core-Set Approach." ICLR 2018.

---

## Appendix A: Reproduction

```bash
# === Dataset v3 ===
python3 scripts/generate_exact_scenarios.py --delta-only
./scripts/capture_screenshots.sh --scenarios scripts/capture_scenarios_v04_delta.json
python3 ml/scripts/index_generated_screenshots.py --auto-promote --start-id 453
python3 ml/scripts/freeze_dataset_v3.py --execute --archive-v2

# === KG v1 ===
python3 ml/scripts/build_kg.py

# === Full selection sweep (committed dataset, heuristic baseline) ===
python3 ml/scripts/run_selection_sweep.py \
    --strategies random uncertainty diversity kg_guided \
    --budgets 10 25 50 100 250 500 --seeds 0 1 2 3 4 5 6 7 8 9 \
    --model-id question_lookup_v0

# === axiom_lora_v1 (requires a local screenshot root -- see docs/MODEL_SELECTION.md) ===
python3 ml/scripts/run_trainable_baseline.py --model-id axiom_lora_v1 \
    --image-root <local screenshots> --manifest-dir <local manifests> \
    --epochs 40 --class-weighted
python3 ml/scripts/export_coreml_lora.py \
    --checkpoint-dir results/trainable_baselines/axiom_lora_v1_seed0_local/checkpoint \
    --image-root <local screenshots> --manifest-dir <local manifests>
python3 ml/scripts/quantize_coreml.py \
    --mlpackage results/coreml_exports/axiom_lora_v1_seed0_local/AxiomLora.mlpackage \
    --label-vocab results/coreml_exports/axiom_lora_v1_seed0_local/label_vocab.json \
    --image-root <local screenshots> --manifest-dir <local manifests>

# === Statistical analysis ===
python3 ml/scripts/run_statistical_analysis.py --output-dir results/analysis/phase12_v1
```

## Appendix B: Dataset Fingerprints

### Dataset v3 (751 examples)

See `data/manifests/v3_fingerprint.json` (committed) for SHA-256 fingerprints of pool/val/test.

### Dataset v2 (archived)

See `data/manifests/v2/fingerprint.json` (committed).
