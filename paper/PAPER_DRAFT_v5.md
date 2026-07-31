# AXIOM-Mobile: Measuring Minimal Training Data Requirements for On-Device Domain Reasoning Under Mobile Constraints

**Annie Boltwood, Mahim Chaudhary, Ariel Tyson**
Simon Fraser University -- CMPT 496

*Draft v5 -- 2026-07-31. This draft corrects, not just extends, v4. Three of v4's conclusions turned out to rest on incomplete investigation rather than a real dead end, and this draft documents both the correction and the process failure that produced the original conclusion, on the view that the second is as important to a reader as the first.*

---

## A Note on Why This Draft Exists

v4 closed with three claims that did not survive a second look, each examined here in the section it belongs to, not buried in a changelog:

1. **"The text-transformer + LoRA path wasn't going to convert."** It was never actually root-caused -- the coremltools failure was hit once, attributed to "a likely version mismatch," and abandoned in favor of a different architecture within the same afternoon. Section 5.3 shows the actual cause (a fixable, well-understood tracing limitation) and a working fix.
2. **"axiom_lora_v1 is a wash, not a win" against the from-scratch baseline.** This rested on one training run per model -- no seed variance, no confidence interval. Section 5.4 reports the same comparison with five seeds per model and a real significance test; the finding reverses.
3. **The trainable-model selection sweep was abandoned because "sustained multi-process training made a personal laptop uncomfortably hot."** The training code never used this machine's GPU at all -- every run in v4 was CPU-only. Section 6.2 reports the sweep completed after fixing that, not a smaller substitute for it.

None of these were fabrications; v4's authors disclosed each limitation plainly, which is exactly what made re-examining them possible. But disclosure of a shortcut is not the same as not taking one, and by v4 the pattern had become: hit friction, document the friction honestly, move on. This draft's discipline is the same as v3 and v4's -- every claim traces to a committed or explicitly-local artifact -- applied one level deeper: before accepting a limitation as real, verify it's not actually a bug.

---

## Abstract

We present AXIOM-Mobile, a system and experimental framework for measuring the minimal training set size (k\*) required for effective visual question answering on mobile devices under strict quality, latency, energy, and memory constraints. This draft makes four corrections and additions to v4. First, we root-cause and fix the coremltools conversion failure that caused v4 to abandon a pretrained-*text*-transformer LoRA approach: BERT-family models compute `position_ids` dynamically at trace time, which coremltools 9.0 cannot lower regardless of `torch`/`transformers` version (verified across three separate version pairings); passing `position_ids` as a static tensor -- exact, not approximate, given this project's fixed-length input contract -- resolves it, and the resulting model (`axiom_lora_text_v1`) converts and predicts with 0% PyTorch/CoreML drift. Second, we replace v4's single-run "wash, not a win" verdict on `axiom_lora_v1` with a five-seed comparison: both the vision-LoRA and text-LoRA pretrained-backbone models significantly outperform the from-scratch baseline (+4.6pp and +5.1pp test EM respectively, 95% bootstrap CI excluding zero), reversing v4's conclusion. Third, we identify that v4's trainable-model selection sweep was abandoned due to a CPU-saturation problem the code never tried to avoid -- no `torch.device` was ever constructed anywhere in the training path -- and, having fixed it, report the completed 80-run sweep in Section 6.2: Uncertainty and Diversity selection catastrophically fail to produce a learnable subset below budget 600 (test EM near 0%, including on their own training subsets), a failure mode invisible to v4's heuristic-only sweep, while KG-guided is the strongest strategy at practical budgets (29.7% vs. Random's 21.1% at budget 150). Fourth, we scale the dataset to v4 (797 examples) with genuinely new content (Safari-rendered synthetic pages, a Contacts fixture) rather than another status-bar variant, after discovering the "Settings and Maps only" simulator-app assumption was stale, and close the Drive-sync gap that blocked reproducibility across machines for two semesters. Fifth, we report energy and memory measurements for the first time in this project's history, any model, any semester: both models clear the memory threshold comfortably (65.89 MiB and 58.49 MiB peak against a 500MB limit), while energy is a narrow split -- `tiny_multimodal_v1` fails the 5%/hr threshold at 5.2%/hr, `axiom_lora_v1` passes at 4.8%/hr, a gap small enough to reflect measurement conditions as much as a real difference between the models. Physical-device latency remains well within threshold from prior sessions.

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

This paper contributes, beyond v4:
1. **A working pretrained-text-transformer + LoRA model** (`axiom_lora_text_v1`), delivering on the literal reading of the original proposal's method, via a root-caused and fixed CoreML conversion path.
2. **A statistically grounded architecture comparison** (5 seeds/model, bootstrap significance testing) replacing v4's single-run verdict, showing pretrained backbones significantly outperform from-scratch training on this task -- the opposite of v4's headline finding.
3. **A real trainable-model selection-strategy sweep**, unblocked by fixing the actual cause of the compute problem that stalled it in v4 (an MPS/device-management bug, not a hardware ceiling).
4. **Dataset v4** (797 examples, up from 751), scaled via genuinely new content sources (Safari synthetic pages, Contacts) discovered by re-checking a stale assumption about simulator app availability, plus a Drive-sync-free local reproduction path for the auto-generated majority of the dataset.

---

## 2. Related Work

**Data-efficient learning.** Active learning and core-set methods have shown that strategic data selection can reduce annotation requirements while maintaining model quality [Sener and Savarese 2018; Ash et al. 2020]. Our work applies this principle to a mobile VQA setting where the effectiveness criterion includes device constraints beyond accuracy alone.

**On-device ML.** Core ML [Apple 2023] and TensorFlow Lite enable deploying models on mobile hardware, but most benchmarking studies report only accuracy or use desktop profiling. We measure latency, energy, and memory on target hardware using Apple Instruments, following the methodology of [Ignatov et al. 2019] for mobile AI benchmarking -- the energy and memory measurements (Section 7.2) are new in this draft, the first time this project has measured either.

**Parameter-efficient fine-tuning.** LoRA [Hu et al. 2021] decomposes weight updates into low-rank matrices, most commonly applied to adapt large pretrained transformers. We apply it to both a pretrained CNN backbone's Conv2d layer (`axiom_lora_v1`, v4) and, new in this draft, a pretrained BERT-family text transformer's attention projections (`axiom_lora_text_v1`) -- the more conventional LoRA application, and the one the original project proposal specified most literally, unblocked here after root-causing why it failed to convert to CoreML in v4.

**Visual question answering.** VQA tasks [Antol et al. 2015] typically assume server-side inference. Mobile VQA for domain-specific screenshots (app UIs, settings panels, notifications) is underexplored. Our dataset targets this niche with screenshot-question-answer triples grounded in real iOS content.

**Learning curves and scaling laws.** Power-law relationships between dataset size and performance are well-documented [Hestness et al. 2017; Kaplan et al. 2020]. v4's fits remained weak (R^2 = 0.12-0.49) on a heuristic memorization baseline; Section 6.2 reports fits against a real trainable model for the first time.

---

## 3. System Overview

AXIOM-Mobile consists of three components, unchanged in shape from v4:

### 3.1 iOS/macOS App (SwiftUI + Core ML)

Screenshot import, question input, a model picker, real Core ML inference via `CoreMLInferenceService`, and benchmark mode with CSV/metadata export. New in this draft: the app accepts a `--model <model_id>` launch argument so a physical-device profiling session can select a model without a manual picker tap, needed to make `scripts/run_physical_device_session.sh`'s per-model Instruments workflow scriptable end-to-end.

### 3.2 Python Training and Analysis Pipeline

Dataset management, a model harness (`train()`, `predict()`, `export_coreml()`), four selection strategies, PyTorch -> Core ML export with an accuracy gate, and a statistical analysis pipeline with bootstrap CIs, paired comparisons, and power-law fits. New in this draft: MPS (Apple Silicon GPU) device support across the full train/predict/save/load/export path -- previously absent entirely, which is the actual reason v4's trainable-model sweep overheated a laptop (Section 6.2).

### 3.3 Knowledge Graph

A compact KG (`kg/entities.json`, `kg/relations.json`) extracted programmatically from the dataset's own fields -- a single command (`ml/scripts/build_kg.py`), no manual curation, re-run after every dataset version rather than left stale. Rebuilt against dataset v4 for this draft: 264 entities (11 App, 21 Screen, 20 Attribute, 212 AnswerValue; up from v3's 235/9/19/20/187), 1,087 relations (up from 1,009) -- the new Safari and Contacts apps/screens from Section 4.1 are correctly reflected, verified by re-running the KG-guided selector against the full v4 pool.

---

## 4. Dataset

### 4.1 Dataset v4: 797 examples (up from 751)

v4 (this project's naming, not to be confused with the paper draft version) adds 46 new QA pairs from 16 new screenshots via a v0.5.0 scenario batch, following the same zero-manual-labeling principle as every prior dataset version.

**Splits:**

| Split | v3 | v4 |
|-------|-----|-----|
| Pool  | 681 | 727 |
| Val   | 30  | 30  |
| Test  | 40  | 40  |
| **Total** | **751** | **797** |

Val/test held constant, as in every prior version; all growth into the pool.

**A stale assumption, re-checked rather than inherited.** Every dataset version through v3 operated under the belief that "the iOS Simulator only ships with Settings and Maps installed," documented in `docs/SCREENSHOT_AUTOMATION.md` and never re-verified across three semesters of dataset growth. Directly checking `xcrun simctl listapps` on this machine's current Xcode/iOS runtime (Xcode 26.6, iOS 26.4/26.5) shows this is false for this environment: Calendar, Reminders, Contacts, Files, Safari, Photos, Health, News, and Weather Wallpaper are all present alongside Settings/Maps. Three semesters of growth had been mining an increasingly narrow seam (status-bar variants on two apps) while unused capacity sat unexamined.

**What shipped from the expanded app list, and what didn't.**
- **Safari + locally-served synthetic HTML pages: shipped.** `simctl openurl` with an `http://127.0.0.1:<port>/...` deep link opens Safari to a page this project's own script generated, so the ground-truth answer is exact by construction. This is a materially different growth mechanism than every prior dataset version: instead of enumerating a fixed, finite set of visually-distinguishable status-bar states, content variety is now bounded only by how many pages the generator writes.
- **Contacts: shipped, but not as an empty state.** The simulator ships 6 fixed sample contacts (John Appleseed, Kate Bell, Anna Haro, Daniel Higgins Jr., David Taylor, Hank M. Zakroff) as a bundled fixture, not random per-boot data -- confirmed by direct visual inspection, not assumed from documentation. Only the count (6, always) is used as the exact answer.
- **Reminders: attempted, rejected.** Shows "No Reminders" once past onboarding -- deterministic and visually confirmed -- but the one-time "Welcome to Reminders" screen on first launch requires an actual tap to dismiss, and neither an out-of-band pre-launch nor an in-sequence warmup capture (both tried) cleared it reliably. This capture harness has no touch-injection mechanism for system apps (its one XCUITest target only drives AXIOMMobile itself), so Reminders is dropped rather than shipped with a broken promoted capture.
- **Calendar: rejected outright.** Unlike the status bar (controllable via `simctl status_bar override`), there is no `simctl` mechanism to control the simulator's actual system clock. Calendar always shows the real current date, which is not a value this generator can predict or keep stable across a future re-run on a different day -- using it would break the deterministic-regeneration guarantee the rest of this pipeline depends on.

**A real, non-deterministic capture failure mode, caught and handled, not assumed away.** The first N Safari captures in a fresh simulator session land on a transitional "Start Page" or a blank page instead of the target content, where N is not fixed -- 1, 3, and 4 were all observed across different capture attempts against the same code. Rather than guess a warmup count and trust it, `ml/scripts/promote_v05_new_apps.py` uses each capture's recorded `file_size_bytes` as an automated verification gate: the broken and correct captures fall into two consistently separated size bands (~117KB vs ~150-160KB), confirmed against direct visual inspection of multiple captures in both bands. This caught and excluded one otherwise-invisible bad capture (`web04`) in the run this dataset version was built from -- a capture that was not marked as a warmup attempt and would have silently shipped wrong ground truth (the manifest would have recorded "$156" as an answer for a screenshot that actually shows a blank page) under a purely count-based warmup scheme.

### 4.2 Closing the Drive-Sync Gap

v4 (the paper) identified data locality -- not modeling ability -- as "the primary practical bottleneck," specifically that the 452 (later 751) examples committed to the manifest were never synced via Google Drive to the machine doing model training, forcing `axiom_lora_v1`'s training and the abandoned selection sweep onto a machine-local, non-committed reconstruction of the data.

This gap is closed for the auto-generated majority of the dataset (699 of 751 images at the time, 93%), which turns out not to need Drive sync at all: the capture pipeline is fully deterministic (same committed scenario JSON in, same simulator screenshots out), so `ml/scripts/regenerate_local_images.py` simply re-runs it locally and matches each resulting image back to its manifest row via the `scenario_id` embedded in that row's `notes` field, rather than any hand-maintained mapping. The 52 manually-captured examples (6.9% of the dataset) remain genuinely not reproducible this way and are excluded from local trainable-model experiments in this draft -- a bounded, disclosed scope decision, not a recurring blocker to re-litigate every phase.

### 4.3 Limitations

- **Scale.** 797 examples remains well below typical VQA benchmarks.
- **KG-guided selection strategy** (used in Section 6.2's sweep) was run against the dataset-v3 KG, not the v4 rebuild described in Section 3.3 -- the rebuild landed after that sweep completed. A re-run against the v4 KG, now available, has not yet been performed; the sweep's qualitative finding (KG-guided strongest at practical budgets) is not expected to change from 29 additional Screen/Attribute regions, but this is not yet verified.
- **Annotator agreement.** Not implemented. The auto-generated majority of the dataset is grounded in deterministic, machine-set or machine-rendered state, not subjective human judgment, so inter-annotator kappa remains a weak signal for this portion specifically.
- **Manual-example exclusion.** The 52 hand-captured examples are excluded from all trainable-model experiments reported in this draft (Section 4.2); results should be read as evidence about the auto-generated 93% of the dataset specifically.

---

## 5. Models

### 5.1 Heuristic and from-scratch baselines

`question_lookup_v0` (memorization heuristic) and `tiny_multimodal_v0/v1` (3-layer CNN + char-level text encoder, trained from scratch) are unchanged in architecture from v4.

### 5.2 axiom_lora_v1: pretrained vision backbone + LoRA (unchanged architecture from v4)

Frozen, ImageNet-pretrained `torchvision.models.mobilenet_v3_small` backbone with a LoRA adapter (rank 8, alpha 16) on the final 1x1 convolution. Unchanged from v4; re-evaluated in Section 5.4 with real seed variance.

### 5.3 axiom_lora_text_v1: pretrained text transformer + LoRA (new -- corrects v4)

**What v4 claimed, and what was actually true.** v4 stated that a pretrained-text-transformer approach "wasn't going to convert" to CoreML, citing a `TypeError: only 0-dimensional arrays can be converted to Python scalars` inside the embeddings layer, attributed to "a likely version mismatch between `transformers`' internals and what `coremltools` 9.0's PyTorch frontend can lower" -- and moved to a vision backbone instead within the same work session, without retrying.

**Root cause, isolated by direct repro.** The failure was reproduced exactly (same error, same location) using `sentence-transformers/all-MiniLM-L6-v2` + `peft` LoRA. To test the "version mismatch" hypothesis, three different `torch`/`transformers`/`peft` version combinations were tried, including the exact combination `coremltools` 9.0 itself documents as its most recently tested pairing:

| `torch` | `transformers` | Result |
|---|---|---|
| 2.13.0 (current) | 4.36.0 | Same failure, same location |
| 2.7.0 (coremltools-recommended) | 4.44.2 | Same failure, same location |
| 2.13.0 (current) | 5.14.1 | **Different** failure (`new_ones` op not implemented -- a separate, newer-transformers-specific issue) |

No version pin fixes the original failure. The actual cause: BERT-family embeddings compute `position_ids` dynamically via a length-dependent slice of a registered buffer at trace time, and coremltools 9.0's PyTorch frontend cannot lower the resulting dynamic-int op, independent of library versions -- confirmed by tracing the same model with LoRA removed entirely, which fails identically.

**The fix.** Every question in this project is already padded/truncated to a fixed length (an existing, pre-v5 design decision made for the char-level text encoder and reused here). Passing `position_ids` to the model explicitly as a static registered buffer -- rather than letting the model derive it dynamically from input length -- is therefore exact, not an approximation, and eliminates the dynamic op entirely. Both `torch.jit.trace` and `coremltools.convert` succeed with this fix, with and without LoRA applied, verified against the current (`torch` 2.13.0) toolchain with `transformers`/`peft` pinned to the one version pair confirmed to convert cleanly (`transformers==4.44.2`, `peft==0.13.2` -- `transformers` 5.x hits the separate `new_ones` issue above, unrelated to this fix).

**Architecture.** Frozen `sentence-transformers/all-MiniLM-L6-v2` (BERT-family) text tower with a LoRA adapter (rank 8, alpha 16) on the query/value attention projections, static `position_ids`, mean-pooled over the attention mask, projected to a 64-dim feature. The image side is the unchanged from-scratch CNN from `tiny_multimodal` (not LoRA-adapted), isolating the pretrained-*text* contribution specifically, mirroring how `axiom_lora_v1` isolates the pretrained-*vision* contribution.

**Verification.** Full pipeline (train -> checkpoint -> reload -> predict -> CoreML export) run end-to-end: **0% PyTorch/CoreML prediction drift**. On-device Swift integration (a WordPiece tokenizer in the app, which the char-level models never needed) is out of scope for this pass -- Python-side train/export/accuracy-gate only, the same scope boundary v4 applied to `axiom_lora_v1` before its own on-device evaluation was complete.

### 5.4 Architecture comparison: a real, multi-seed result (corrects v4)

**What v4 claimed, and why it doesn't hold up.** v4 reported `axiom_lora_v1` (30.0% test EM) as a "wash, not a win" against a from-scratch `tiny_multimodal_v1` (35.0% test EM) -- but each number came from exactly one training run. No seed variance was reported, and v4's own limitations section acknowledged this directly ("axiom_lora_v1 has only 1 seed -- no confidence interval possible").

**This draft's comparison.** All three architectures (from-scratch, vision+LoRA, text+LoRA) trained for 5 seeds each, 40 epochs, class-weighted cross-entropy, on the same locally-regenerated dataset (Section 4.2; 699 examples, auto-generated portion only, excluding the 52 manual examples for all three models equally):

| Model | Test EM (mean +/- std, 5 seeds) |
|---|---|
| `tiny_multimodal_v1` (from-scratch) | 32.0% +/- 1.3 |
| `axiom_lora_v1` (vision + LoRA) | 36.6% +/- 4.7 |
| `axiom_lora_text_v1` (text + LoRA) | 37.1% +/- 5.3 |

**Paired bootstrap significance (10,000 resamples over the 5 seeds):**

| Comparison | Mean diff | 95% CI | Significant? |
|---|---|---|---|
| `axiom_lora_v1` - from-scratch | +4.6pp | [+1.1, +8.0] | Yes |
| `axiom_lora_text_v1` - from-scratch | +5.1pp | [+1.7, +8.6] | Yes |
| `axiom_lora_text_v1` - `axiom_lora_v1` | +0.5pp | [-4.6, +5.1] | No |

**Read honestly, in the opposite direction from v4.** Both pretrained-backbone approaches significantly outperform from-scratch training on this task, at 5 seeds. This reverses v4's central modeling conclusion, which was built on a single run per model. The vision-LoRA and text-LoRA approaches are statistically indistinguishable from each other at this seed count -- neither modality has a demonstrated edge yet. v4's explanation for the (apparent, single-run) pretrained-backbone underperformance -- "ImageNet pretraining optimizes for object/texture recognition, which does not obviously transfer to reading exact digits" -- does not survive this result and should not be treated as established.

**Caveat.** This comparison excludes the 52 manually-captured examples (Section 4.2) and was not run against the literal committed dataset v4 split. A same-recipe run against the full committed split, including the manual examples, has not yet been performed.

---

## 6. Selection Strategies

Four strategies, unchanged in implementation from v4: Random, Uncertainty (metadata-proxy scoring), Diversity (k-center greedy), KG-guided (round-robins across KG `(Screen, Attribute)` regions).

### 6.1 What v4 actually ran, named accurately

v4's headline "240-run, 10-seed" sweep (Section 6.2 of that draft) ran against `question_lookup_v0` -- a string-memorization heuristic with no training, no device constraints, and no domain reasoning. It is a legitimate test of each strategy's example-selection logic, and v4 reported it as such without overclaiming what model it used. But presented without qualification as "the full comparison," it is easy to read as answering the project's actual research question (learning curves for a *trainable* model), which it does not.

### 6.2 The real trainable-model sweep (new -- the SPEC's actual deliverable)

**Why v4 didn't have this.** v4 attempted this sweep, got 50 of 240 cells complete, and stopped because "sustained multi-process training load made the laptop uncomfortably hot" -- reported as a genuine hardware/thermal constraint of running this class of experiment on personal laptop hardware, not a bug.

**What was actually true.** No file in the training path -- `run_trainable_baseline.py`, `tiny_multimodal.py`, `axiom_lora.py` -- ever constructed a `torch.device` or moved a tensor to one. Every training run in this project's history, across both semesters, ran on CPU by default, on a machine (Apple M1) with a working, unused GPU (`torch.backends.mps.is_available()` returns `True`). The "laptop overheating" v4 attributed to this class of experiment being inherently too demanding for personal hardware was a CPU-saturation problem the code never tried to avoid.

**The fix and the result.** Added MPS device detection (with CPU fallback) across the training path, fixing one bug the change exposed along the way (class-weighted loss building its weight tensor on the wrong device). With this fix, a 4-strategy x 4-budget x 5-seed sweep (`{50, 150, 300, 600}`, 80 runs total, 20 epochs, class-weighted) against `axiom_lora_v1` on the locally-regenerated dataset completed in under 30 minutes of wall-clock time on this machine's GPU -- not the several hours a naive extrapolation from the CPU-bound attempt would have suggested, and nowhere near "uncomfortably hot."

**Table: Test EM by strategy and budget (mean of 5 seeds)**

| Budget | Random | Uncertainty | Diversity | KG-guided |
|--------|--------|-------------|-----------|-----------|
| 50  | 9.1%  | 0.0%  | 2.3%  | 2.3%  |
| 150 | 21.1% | 0.0%  | 0.6%  | **29.7%** |
| 300 | 40.0% | 0.0%  | 2.3%  | 38.9% |
| 600 | 34.3% | 31.4% | 34.3% | **37.1%** |

**A genuine, previously invisible failure mode.** Uncertainty and Diversity selection catastrophically fail to produce a learnable training subset at small-to-medium budgets -- test EM at or near 0% through budget 300, not a generalization gap but a training failure: at budget=150, Diversity's own *training-subset* exact match is 2.7% (4/150 correct), meaning the model cannot even fit the examples it was given, let alone generalize. This is invisible in a sweep against a memorization heuristic (v4's Section 6.2), which has no notion of "failing to learn" -- it is specific to evaluating selection strategies against a real trainable model, and is the reason this sweep, not the heuristic one, is the deliverable the original SPEC actually asked for.

**KG-guided is the strongest strategy at practical budgets.** At budget=150 -- a fifth of the largest budget tested -- KG-guided (29.7%) already outperforms Random (21.1%) by a wide margin and Diversity/Uncertainty by an order of magnitude, while remaining competitive with Random at every budget tested. All four strategies converge by budget=600, where only the KG-guided vs. Uncertainty gap remains statistically significant (paired bootstrap, 10,000 resamples over 5 seeds): KG-guided beats Uncertainty by +5.7pp (95% CI [+1.7, +9.7]); KG-guided vs. Random (+2.9pp, CI [0.0, +7.4]) and KG-guided vs. Diversity (+2.8pp, CI [-4.6, +10.3]) do not cross the significance threshold at this seed count.

**Power-law fits** (y = a\*x^b, log-log OLS over the 4 budget-mean points):
- Random: R^2 = 0.865 (b = 0.58) -- the cleanest fit of any strategy, any sweep, this project has produced
- KG-guided: R^2 = 0.771 (b = 1.13)
- Diversity: R^2 = 0.396 (b = 1.02) -- distorted by the near-zero low-budget collapse
- Uncertainty: degenerate -- insufficient non-zero points to fit (3 of 4 budgets are exactly 0%)

Random's fit quality here is notably stronger than any fit in v4's heuristic-only sweep (best R^2 there was 0.49) -- a real trainable model's learning curve, at least for random sampling, behaves closer to the smooth scaling literature predicts than a memorization heuristic's did.

---

## 7. On-Device Evaluation

### 7.1 Physical-Device Latency (unchanged from v4, iPhone 15 Pro Max, A17 Pro)

| Model | Condition | p50 (ms) | p95 (ms) | Threshold |
|---|---|---|---|---|
| tiny_multimodal_v0 | cold | 14.0 | 26.2 | PASS |
| tiny_multimodal_v0 | warm | 14.5 | 22.0 | PASS |
| tiny_multimodal_v1 | standard | 14.5 | 24.6 | PASS |

All physical-device sessions pass all latency thresholds with wide margin (28x below the 400ms p50 limit). No new physical-device latency session was run this pass for `axiom_lora_v1` or `axiom_lora_text_v1`.

### 7.2 Energy and Memory: measured for the first time, any model, any semester

`scripts/run_physical_device_session.sh` consolidates the Instruments runbook's Time Profiler / Allocations / Power Profiler workflow (each required as a separate trace by Instruments itself; "Power Profiler" is this Xcode version's name for what the runbook and older Xcode versions call "Energy Log" -- confirmed via `xcrun xctrace list templates`) into one script per model, with the app accepting a `--model` launch argument so a session doesn't require manually driving the picker. This is the first physical-device session this project has actually run, and it surfaced five real, sequential bugs in the script before it worked cleanly -- listed in full in Section 8, since fixing tooling that had never touched real hardware before is as much a part of this result as the numbers themselves.

**Table: Energy and memory, iPhone 15 Pro Max (A17 Pro), iOS 26.6**

| Model | Peak Memory | Avg Power | Threshold (< 5%/hr) | Thermal |
|---|---|---|---|---|
| `tiny_multimodal_v1` | 65.89 MiB | 5.2%/hr | **FAIL** (narrow) | Nominal |
| `axiom_lora_v1` | 58.49 MiB | 4.8%/hr | **PASS** (narrow) | Nominal |

Both comfortably clear the 500MB memory threshold (peak usage is roughly 1/8th of the limit for both models). Neither comfortably clears the energy threshold -- one fails narrowly, one passes narrowly, and the ~0.4 percentage-point gap between them is small enough that "pass vs. fail" here reflects measurement noise at these margins at least as much as a real difference between the models. Thermal state stayed Nominal throughout for both, ruling out thermal throttling as a confound.

**A methodology catch during this session, not glossed over.** The first energy capture for each model was recorded while the device was USB-tethered to the Mac -- necessary for `xctrace` to attach -- and therefore actively charging, confirmed by the "Charger Connected" track showing active for the full recording and an uninformative exact 0.0%/hr reading as the direct symptom (a charging device cannot show real battery drain; it's gaining charge, not losing it). Re-captured over a Wi-Fi-paired connection with the USB cable physically disconnected, which produced the real, non-zero readings reported above. The charging-condition traces are kept for reference (Thermal State and the CPU-activity shape are still valid under either condition) but are not the source of the energy numbers in this table.

**A second honest caveat**: both average-power readings blend a brief (~1-10s) burst of active inference with tens of seconds of near-idle time afterward in the same 45-47s recording -- a "typical session" rate, not a pure continuous-active-inference rate. `axiom_lora_v1`'s trace shows a ~1s instantaneous peak of 32.8%/hr during its active burst, well above its own 4.8%/hr session average, which is the clearest direct evidence of this. A rate under genuinely continuous inference (rather than 50 quick iterations followed by idle) would likely be higher for both models than either number in the table.

Full methodology, per-field provenance, and both models' complete readings: `results/analysis/device_profiling_v1/summary.json`.

---

## 8. Real Bugs Found and Fixed

Continuing the project's standing practice of reporting bugs found in its own tooling as part of the record:

1. **No device management anywhere in the training path** (Section 6.2) -- not a bug in the traditional sense (the code was correct, just never GPU-aware), but its absence was misdiagnosed in v4 as a hardware/thermal limitation of the experiment class itself, which is the more consequential error.
2. **Class-weighted loss device mismatch**, exposed by the MPS fix: `CrossEntropyLoss(weight=...)` requires its weight tensor on the same device as its inputs; the class-count/weight computation was CPU-only and never moved.
3. **A silently-wrong dataset promotion**, caught by the file-size verification gate (Section 4.1): scenario `web04` was not marked as a warmup attempt but was, in fact, a broken capture (blank page) that would have shipped incorrect ground truth (e.g. an answer of "$156" for an image that shows nothing) had the promotion pipeline trusted the generator's warmup/non-warmup classification alone.
4. **`coremltools.convert` version-mismatch misdiagnosis** (Section 5.3): the actual root cause (dynamic `position_ids`) was never isolated in v4; "likely version mismatch" was recorded as the explanation without testing it, and it was wrong.

Five more were found and fixed in sequence during this draft's physical-device session (Section 7.2) -- its first-ever run against real hardware, not a simulator:

5. **Device-detection false positive**: the script's `xctrace list devices` text-parsing filter silently selected a Simulator instead of the connected physical device, because simulator entries don't reliably contain the literal word "Simulator" in their name. Replaced with `xcodebuild -showdestinations`, which explicitly tags real devices and flags incompatible ones.
6. **Expired provisioning profile not renewed**: plain `xcodebuild` embeds whatever profile is already on disk even if expired; Xcode's GUI Run button renews it first but the CLI does not unless told to. Fixed with `-allowProvisioningUpdates`.
7. **Install path pointed at a stale build**: a hardcoded guess at the build output path happened to match a real leftover app bundle from months earlier, with a long-expired embedded profile -- so the fresh, correctly-signed build was never actually the one installed. Fixed by querying `xcodebuild -showBuildSettings` for the real `BUILT_PRODUCTS_DIR` instead of guessing.
8. **Fragile PID-lookup race**: launching the app via `devicectl` and then grepping `devicectl device info processes` for its PID to attach `xctrace` was unreliable -- `devicectl`'s own `--help` states its text output isn't a supported interface for scripts at all. Replaced with `xctrace record --launch`, which launches and attaches atomically.
9. **Wrong Instruments template name**: the runbook and script both called it "Energy Log," matching older Xcode versions; this Xcode version calls it "Power Profiler," and `xctrace` fails outright on an unrecognized template name rather than fuzzy-matching. Confirmed via `xcrun xctrace list templates` and fixed throughout.

A separate, non-code methodology issue was also caught and corrected during this same session: the first energy reading for each model was captured while the device was charging over USB, producing an uninformative exact 0.0%/hr result. Section 7.2 has the full account.

---

## 9. Limitations and Threats to Validity

### 9.1 Quality Gap (unresolved, but the picture has changed)

The 70% EM target is not met by any model. The best-known result under a fair, multi-seed comparison is now `axiom_lora_text_v1` at 37.1% +/- 5.3% test EM (Section 5.4) -- meaningfully closer than either v4's single-run 30.0% for the pretrained approach or the from-scratch baseline's 32.0%, but the gap to 70% remains large and neither this draft nor v4 has evidence about *why* it's this large beyond "more data helped before."

### 9.2 Scope of the Architecture Comparison

Section 5.4's comparison excludes the 52 manually-captured examples and was not run against the literal committed dataset v4 split (Section 4.2/4.3) -- a same-recipe run against the full committed data, manual examples included, is open work.

### 9.3 KG-Guided Sweep Ran Against the Pre-Rebuild KG

The knowledge graph has since been rebuilt against dataset v4 (Section 3.3), but the Section 6.2 sweep ran before that rebuild, against dataset-v3-derived KG regions. The 29.7% test EM at budget=150 (Section 6.2) reflects KG-guided selection with no visibility into the 46 new Safari/Contacts examples. Whether re-running against the v4 KG changes this result is not yet verified.

### 9.4 Statistical Limitations

- 5 seeds per model for the architecture comparison (Section 5.4) -- a real improvement over v4's single run, still modest by broader ML-research standards.
- 5 seeds per (strategy, budget) cell in the trainable-model sweep (Section 6.2) -- half v4's heuristic-sweep seed count, a deliberate right-sizing for wall-clock feasibility (Section 6.2's Appendix reproduction command), not a data limitation discovered after the fact.
- Random's power-law fit (R^2 = 0.865) is the strongest this project has produced in any sweep; Uncertainty's is degenerate (3 of 4 budget means are exactly 0%).

### 9.5 Scope

- Energy and memory are now measured (Section 7.2), but only for `tiny_multimodal_v1` and `axiom_lora_v1` -- `axiom_lora_text_v1` has no on-device Swift integration in this pass, so it cannot be profiled the same way. Both measured readings also reflect a mixed active/idle recording window rather than pure continuous-inference load (Section 7.2's caveat).
- No ablation on LoRA rank, or on unfreezing more of either pretrained backbone.
- No comparison to production VLMs (Florence, LLaVA, Qwen-VL remain config-only candidates, unchanged since v1).
- Reminders and Calendar remain out of the dataset (Section 4.1), for reasons specific to each (touch-injection requirement; no deterministic clock control), not a general ceiling on further app-diversity growth.

---

## 10. Discussion

1. **The most important finding this draft reports is about the project's own process, not a model.** Three separate v4 conclusions -- a conversion dead end, a quality wash, and a hardware limitation -- turned out to be artifacts of stopping investigation at the first plausible explanation rather than the actual cause. All three reversed under direct re-examination that took, in total, less time than the original (abandoned) attempts. The lesson is not "try harder" in the abstract; it's that this project's own honesty norm (disclose limitations plainly) had started to substitute for closing them, and disclosure without a genuine attempt at remediation is not the same discipline this project was built on in semester 1.
2. **Pretrained backbones do help on this task**, contrary to v4's headline conclusion -- both vision and text modalities, roughly equally, at the seed count tested. This reopens a question v4 had closed (whether pretraining is a poor prior for this task) rather than answering it.
3. **The selection-strategy question, asked of a real model for the first time, gives a different answer than the heuristic sweep did.** v4's memorization-heuristic sweep found KG-guided overtaking Random by budget 50, with all strategies producing *some* signal at every budget. Against a real trainable model, Uncertainty and Diversity instead collapse to near-0% test EM through budget 300 -- not a weaker version of the heuristic-sweep pattern, but a qualitatively different failure this project could not have seen without fixing the compute problem that blocked it in v4. KG-guided remains the standout strategy in both sweeps, for a related but not identical reason: coverage-first selection that starved a memorization heuristic of repeats (v4) instead appears to give a real model enough distinct signal to actually learn from, where Diversity and Uncertainty's specific selection criteria do not, at least at these budgets.
4. **Data locality is resolved for 93% of the dataset**, and the remaining 7% (manual examples) is a small, bounded, disclosed gap rather than a recurring blocker -- closing it fully just requires one round of Drive access, not further engineering.

## 11. Conclusion

This draft corrects three conclusions from v4 that did not survive direct re-examination -- a text-LoRA conversion failure attributed to the wrong cause, a single-run "wash, not a win" verdict that reverses at five seeds, and a sweep abandonment attributed to hardware limits that were actually a missing device-management code path -- and extends the dataset with genuinely new content after discovering a stale assumption about simulator app availability. The central quality question remains open (best result: 37.1% test EM against a 70% target), but the evidence base under it is now materially more reliable than it was in v4. Energy and memory, the two constraints this project had never measured on any model in any semester, are measured for the first time in this draft: both models pass memory comfortably, energy is a narrow split (one model over threshold, one under, by a margin smaller than the measurement's own noise floor) -- a real result, not a clean win, delivered by fixing five genuine bugs in the profiling tooling on its first actual contact with physical hardware rather than working around them.

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
# === Dataset v4 (local regeneration, no Drive access needed for auto-generated portion) ===
python3 ml/scripts/regenerate_local_images.py --device "iPhone 17 Pro Max"
./scripts/capture_new_apps_v05.sh --device "iPhone 17 Pro Max"
python3 ml/scripts/promote_v05_new_apps.py --input ~/axiom-local-data/raw_v05 --execute

# === axiom_lora_text_v1 (the fixed text-LoRA path) ===
python3 ml/scripts/run_trainable_baseline.py --model-id axiom_lora_text_v1 \
    --image-root ~/axiom-local-data/image_root --manifest-dir ~/axiom-local-data/manifests \
    --epochs 40 --class-weighted

# === 5-seed architecture comparison ===
for model in tiny_multimodal_v1 axiom_lora_v1 axiom_lora_text_v1; do
  for seed in 0 1 2 3 4; do
    python3 ml/scripts/run_trainable_baseline.py --model-id "$model" --seed "$seed" \
        --image-root ~/axiom-local-data/image_root --manifest-dir ~/axiom-local-data/manifests \
        --epochs 40 --class-weighted \
        --output-dir ~/axiom-local-data/arch_comparison/"${model}_seed${seed}"
  done
done

# === Trainable-model selection sweep (real deliverable, not the heuristic-only version) ===
python3 ml/scripts/run_selection_sweep.py \
    --strategies random uncertainty diversity kg_guided \
    --budgets 50 150 300 600 --seeds 0 1 2 3 4 \
    --model-id axiom_lora_v1 \
    --image-root ~/axiom-local-data/image_root --manifest-dir ~/axiom-local-data/manifests \
    --epochs 20 --class-weighted
```

## Appendix B: Dataset Fingerprints

### Dataset v4 (797 examples)

See `data/manifests/v4_fingerprint.json` (committed) for SHA-256 fingerprints of pool/val/test.

### Dataset v3 (archived)

See `data/manifests/v3/fingerprint.json` (committed).

## Appendix C: Analysis Artifacts

- Architecture comparison (Section 5.4): `results/analysis/arch_comparison_v1/summary.json`
- Trainable-model selection sweep (Section 6.2): `results/analysis/selection_sweep_trainable_v1/summary.json`, raw per-run results in `~/axiom-local-data/selection_sweep_v1/` (machine-local, not committed -- regenerate via the Appendix A command)
