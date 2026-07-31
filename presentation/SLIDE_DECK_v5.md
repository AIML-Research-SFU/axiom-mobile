---
marp: true
theme: default
paginate: true
---

# AXIOM-Mobile

## Corrections and Real Results

Annie Boltwood, Mahim Chaudhary, Ariel Tyson

Simon Fraser University -- CMPT 496 -- Semester Update v5

---

## Why This Deck Exists

v4 closed with three conclusions. None were fabricated -- all were disclosed honestly. None survived a second look:

1. "Text-transformer LoRA wasn't going to convert" -- never actually root-caused
2. "axiom_lora_v1 is a wash, not a win" -- one run per model, no seeds
3. "Sweep abandoned, laptop got too hot" -- training never used the GPU at all

This deck reports what a second look found.

---

## Where v4 Left Off

- Dataset v3: 751 examples, KG v1 built, 4-strategy sweep run (**on a heuristic, not a trainable model**)
- `axiom_lora_v1` (pretrained + LoRA): reported as losing to from-scratch, n=1
- Selection sweep on a real model: attempted, abandoned at 50/240 runs
- Energy/memory: never measured, any model, any semester

---

## Correction 1: The LoRA Text Path Was Fixable

**The claim:** coremltools conversion "wasn't going to convert," likely a version mismatch. Never retried.

**What we did:** reproduced the exact failure, then tested 3 different `torch`/`transformers` version pairs -- including the exact combo coremltools itself recommends. **Same failure, every time.** Not a version issue.

**Root cause:** BERT-family models compute `position_ids` dynamically at trace time. coremltools can't lower that op. Fix: pass `position_ids` as a static tensor -- exact, not approximate, given this project's fixed-length questions.

**Result:** `axiom_lora_text_v1` converts cleanly. 0% PyTorch/CoreML prediction drift.

---

## Correction 2: The "Wash, Not a Win" Was n=1

v4's entire verdict on `axiom_lora_v1` rested on **one training run per model.**

We reran it: **5 seeds per model**, same data, same recipe.

| Model | Test EM (mean ± std, 5 seeds) | vs. from-scratch |
|---|---|---|
| `tiny_multimodal_v1` (from-scratch) | 32.0% ± 1.3 | -- |
| `axiom_lora_v1` (vision + LoRA) | 36.6% ± 4.7 | **+4.6pp, significant** |
| `axiom_lora_text_v1` (text + LoRA) | 37.1% ± 5.3 | **+5.1pp, significant** |

**Both pretrained approaches significantly beat from-scratch.** The opposite of v4's conclusion. (95% bootstrap CI excludes zero for both comparisons.)

---

## Correction 3: The Laptop Never Had a Chance

v4: "sustained multi-process training made the laptop uncomfortably hot" -- reported as a hardware limit of this class of experiment.

**What was actually true:** zero lines of training code, anywhere in the project, across both semesters, ever constructed a `torch.device`. Every run was CPU-only, on a machine with a working, idle Apple Silicon GPU.

Fixed. Also caught a real bug the fix exposed: class-weighted loss building its weight tensor on the wrong device.

Verified end-to-end on MPS: 0% accuracy drop through the full export pipeline.

---

## The Real Selection Sweep (New)

80 runs (4 strategies x 4 budgets x 5 seeds), ~30 min on GPU, against `axiom_lora_v1` -- **a real trainable model**, not the memorization heuristic v4's 240-run sweep used.

| Budget | Random | Uncertainty | Diversity | KG-guided |
|--------|--------|-------------|-----------|-----------|
| 50  | 9.1%  | 0.0%  | 2.3%  | 2.3%  |
| 150 | 21.1% | 0.0%  | 0.6%  | **29.7%** |
| 300 | 40.0% | 0.0%  | 2.3%  | 38.9% |
| 600 | 34.3% | 31.4% | 34.3% | **37.1%** |

**A failure mode v4's heuristic sweep couldn't see:** Uncertainty and Diversity collapse to ~0% through budget 300 -- not a generalization gap, a *training* failure (Diversity's own training-subset EM at budget 150 is 2.7%).

**KG-guided wins where it matters:** +8.6pp over Random at budget 150, on a fifth of the max budget.

---

## Sweep: Power-Law Fits

| Strategy | R² | Note |
|---|---|---|
| Random | **0.865** | Strongest fit this project has produced, any sweep |
| KG-guided | 0.771 | |
| Diversity | 0.396 | Distorted by the low-budget collapse |
| Uncertainty | degenerate | 3 of 4 budget means are exactly 0% |

Only KG-guided vs. Uncertainty is statistically significant at budget=600 (+5.7pp, 95% CI [+1.7, +9.7]) -- the strategies converge once the budget is large enough for all of them to actually learn.

---

## Dataset v4: New Content, Not More Status-Bar Trivia

The "Settings and Maps only" simulator assumption was **stale** -- never re-checked across 3 semesters of growth.

Direct check (`xcrun simctl listapps`) on this machine: Calendar, Reminders, Contacts, Files, Safari, Photos, Health, News, Weather Wallpaper all available.

**Shipped:** Safari + locally-served synthetic HTML pages (unlimited content variety, zero manual labeling), Contacts (bundled 6-sample fixture)
**Rejected, honestly:** Reminders (onboarding needs a real tap, no touch injection available), Calendar (no way to control simulator's system clock deterministically)

**797 total examples**, up from 751.

---

## A Real Bug Caught Mid-Pipeline

First Safari-capture attempt: broken (blank "Start Page" instead of content) for a **variable** number of leading captures -- 1, 3, then 4, across different runs. Not a fixed warmup count.

Fix: use each capture's recorded file size as an automated verification gate. Broken and working captures fall into two clearly separated size bands (~117KB vs ~150-160KB), confirmed by direct visual inspection.

**Caught one real, silently-wrong promotion**: `web04` wasn't flagged as a warmup attempt but was actually broken -- would have shipped "$156" as ground truth for a blank image.

---

## Closing the Drive-Sync Gap

v4: "data locality is the primary bottleneck." True, but only for 7% of the dataset.

699 of 751 v3 images (93%, the auto-generated portion) are **100% reproducible locally** -- the capture pipeline is fully deterministic, so it doesn't need Drive sync at all, just re-running.

`ml/scripts/regenerate_local_images.py` does this now. The remaining 52 manual examples are excluded from local experiments, disclosed as a bounded scope decision -- not re-litigated every phase.

---

## Physical Device: Ready When the Hardware Is

Energy and memory: still unmeasured, any model, any semester -- the one gap that's genuinely not automatable.

`scripts/run_physical_device_session.sh` (new) consolidates the full Instruments workflow (Time Profiler / Allocations / Energy Log, each needing a separate trace) into one script per model. App now accepts `--model <id>` as a launch argument so no manual picker tap is needed.

**What's left:** one ~15-20 minute session with a physical device. Nothing else.

---

## Effectiveness Threshold Scorecard

| Metric | Target | Best Result | Status |
|--------|--------|-------------|--------|
| EM >= 70% | 70% | 37.1% (`axiom_lora_text_v1`, 5-seed) | FAIL |
| Latency p50 <= 400 ms | 400 ms | 14.0-14.5 ms (physical) | PASS |
| Latency p95 <= 600 ms | 600 ms | 22.0-26.2 ms | PASS |
| Energy < 5%/hr | 5%/hr | -- | UNAVAILABLE |
| Memory < 500 MB | 500 MB | -- | UNAVAILABLE |
| Size < 100 MB | 100 MB | 106 KB (`tiny_multimodal_v1`) | PASS |

Quality gap narrower than v4 showed, but still the binding failure.

---

## What We're Being Honest About, This Time Including Ourselves

- v4's three headline conclusions were built on incomplete investigation, not false claims -- each was disclosed plainly, which is exactly what made re-checking them possible
- Disclosing a limitation is not the same as closing it. This project's honesty norm had started substituting for remediation.
- The architecture comparison still excludes the 52 manual examples and hasn't been run on the literal committed split
- KG v1 hasn't been rebuilt against the 46 new v4 examples yet

---

## Key Contributions This Pass

1. Root-caused and fixed the LoRA text-tower conversion failure v4 gave up on
2. Replaced a single-run verdict with a 5-seed, statistically significant result -- **reversing** v4's conclusion
3. Fixed the actual cause of the sweep-blocking "overheating" (no GPU usage, anywhere) and ran the real trainable-model sweep
4. Dataset v4: genuinely new content sources, not another status-bar variant
5. Closed the Drive-sync gap for 93% of the dataset
6. Physical-device profiling reduced to a single short session, ready to run

---

## Next Steps

- Run the physical-device Instruments session -- the one remaining non-automatable gap
- Rebuild KG v1 against dataset v4's new examples
- Re-run the architecture comparison on the full committed split, manual examples included
- More seeds on the trainable-model sweep if the budget allows
- Investigate *why* pretrained backbones help less than hoped -- unfreeze more of the backbone, try a higher LoRA rank, or a UI/document-pretrained backbone instead of ImageNet

---

## Thank You

**Repository**: [axiom-mobile on GitHub](https://github.com/AIML-Research-SFU/axiom-mobile)

Annie Boltwood, Mahim Chaudhary, Ariel Tyson

Simon Fraser University -- CMPT 496

Questions?
