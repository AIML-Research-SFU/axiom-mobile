---
marp: true
theme: default
paginate: true
---

# AXIOM-Mobile

## Minimal Data for On-Device Domain Reasoning

Annie Boltwood, Mahim Chaudhary, Ariel Tyson

Simon Fraser University -- CMPT 416 -- Semester 2 Update

---

## Where We Left Off (Semester 1)

- Dataset v2: 452 examples, 128 classes
- `tiny_multimodal_v1`: from-scratch CNN, **27.5% test EM** vs. 70% target
- 3 of 4 selection strategies executable; KG-guided blocked (no KG)
- Latency measured on physical device (14.0-14.5ms); energy/memory not measured
- 3 seeds per sweep condition

---

## This Semester: Four Things We Set Out to Do

1. Scale the dataset further -- zero manual labeling
2. Build the knowledge graph, unblock the 4th selection strategy
3. Deliver on the original "LoRA fine-tuning" promise
4. Close the quantization + on-device profiling gaps

---

## 1. Dataset v3: 452 -> 751 Examples

| Version | Examples | Pool | Val | Test |
|---------|----------|------|-----|------|
| v2 | 452 | 382 | 30 | 40 |
| **v3** | **751** | **681** | 30 | 40 |

- Same zero-manual-labeling simulator pipeline as v2
- New dimension: cellular signal bars (visually confirmed distinguishable)
- **Tested and rejected**: Wi-Fi bars (not distinguishable), carrier name (not rendered on-device)
- Caught and fixed a real bug: a one-time system prompt corrupted 1 example's ground truth -- found by actually looking at the image, not trusting the pipeline

---

## 2. KG v1: Built, Not Curated

| Entity type | Count |
|---|---|
| App | 9 |
| Screen | 19 |
| Attribute | 20 |
| AnswerValue | 187 |
| **Total** | **235** |

- Extracted **programmatically** from the dataset's own fields -- zero manual entity curation
- Original proposal guessed "~1,000 entities" before real data existed -- we report the real number
- Found and fixed a real parsing bug before shipping (compound screen names misclassified as separate apps)

---

## KG-Guided Selection: Now Real

- Round-robins across `(Screen, Attribute)` regions -- maximize breadth before depth
- **Measured**, not assumed: 25/37 regions covered at budget=25, vs. **11/37 for random** at the same budget
- Genuinely different mechanism from Diversity (text similarity) and Uncertainty (per-example scoring)

---

## Full Selection Sweep at Scale (New)

**240 runs** on the real committed dataset v3: 4 strategies x 6 budgets x **10 seeds** (up from 3)

| Budget | Random | Diversity | Uncertainty | KG-guided |
|--------|--------|-----------|-------------|-----------|
| 10  | 31.5% | 4.3% | 5.0% | 10.3% |
| 50  | 37.0% | 32.8% | 0.0% | **39.5%** |
| 500 | 36.0% | 35.3% | 27.5% | 35.0% |

- Random wins small budgets (memorization heuristic needs repeats)
- **KG-guided overtakes random by budget 50** -- coverage stops being a liability once budgets are large enough
- Power-law fits improved (R^2 up to 0.49, from <0.2 in v3) -- still weak, but real progress

---

## 3. axiom_lora_v1: Delivering on the LoRA Promise

The original README said "LoRA (PEFT) fine-tuning." Never implemented until now.

**What we tried first:** pretrained *text* transformer + LoRA
- Failed at CoreML conversion (isolated to the base transformer, not LoRA -- confirmed via a control test with LoRA removed)
- This was a pre-registered fallback scenario, not an improvised excuse

**What shipped:** frozen pretrained MobileNetV3-Small + genuine LoRA adapter (rank 8) on the final conv layer, unchanged text encoder

---

## axiom_lora_v1: The Honest Result

Same data, same recipe, direct comparison:

| Model | Params | Test EM |
|---|---|---|
| `axiom_lora_v1` (pretrained + LoRA) | 1.01M | 30.0% |
| `tiny_multimodal_v1` (from scratch, retrained) | 49K | **35.0%** |

**The pretrained backbone does not win.** From-scratch model matches/beats it with 21x fewer parameters.

Likely explanation: ImageNet pretraining optimizes for object recognition, not reading exact digits/icons in a status bar. Reported as a real negative result, not buried.

---

## 4. Quantization + Profiling

**Quantization** (new): int8 post-training quantization on `axiom_lora_v1`
- 2.04MB -> **1.14MB (1.80x compression)**, **0% accuracy drop**

**Simulator profiling** (new, pipeline validation only): p50 = 99.5ms -- not publishable, same standing rule as v3

**Still outstanding**: energy and memory, on any model, in any semester -- both require a physical device and a person with Instruments, which this pass didn't have

---

## Pareto View (Updated)

| Model | Test EM | Size | Pareto-optimal? |
|-------|---------|------|------------------|
| `question_lookup_v0` | 35.0% | 0.1 MB | Yes |
| `tiny_multimodal_v1` | 35.0% | 0.106 MB | Yes |
| `axiom_lora_v1` | 30.0% | 2.04 MB | **No** |

`axiom_lora_v1` is dominated -- worse quality *and* ~20x bigger than the model it was meant to replace.

---

## Bugs We Found in Our Own Analysis Pipeline

Not modeling bugs -- bugs in the tools that report results:

1. **Stale sweep hardcode**: analysis script always read the old 54-run sweep, silently ignored the real 240-run one
2. **Stale Pareto size**: read a frozen training-time estimate (6.0MB) instead of the measured export size (2.04MB)
3. **False "memory complete" status**: conflated "a trace file exists" with "memory data exists" -- was about to report memory as measured when it never was

All three found and fixed before this deck was built, not after.

---

## Effectiveness Threshold Scorecard

| Metric | Target | Best Result | Status |
|--------|--------|-------------|--------|
| EM >= 70% | 70% | 35.0% (tiny_multimodal_v1, v3-local) | FAIL |
| Latency p50 <= 400 ms | 400 ms | 14.0-14.5 ms (physical) | PASS |
| Latency p95 <= 600 ms | 600 ms | 22.0-26.2 ms | PASS |
| Energy < 5%/hr | 5%/hr | -- | UNAVAILABLE |
| Memory < 500 MB | 500 MB | -- | UNAVAILABLE |
| Size < 100 MB | 100 MB | 106 KB (tiny_multimodal_v1) | PASS |

Same 3/6-pass picture as v3 -- quality remains the binding failure, not efficiency.

---

## What We're Being Honest About

- **axiom_lora_v1 trained on local data, not the committed split** -- Drive sync gap, disclosed not hidden
- **Trainable-model sweep attempted, deliberately abandoned** -- laptop got too hot running 4 parallel training processes; partial results deleted rather than kept half-finished
- **Pretrained backbone made quality worse, not better** -- reported as the headline modeling finding, not softened

---

## Key Contributions This Semester

1. Dataset scaled 452 -> 751, zero manual labeling, one real bug caught by inspection
2. KG v1 built programmatically, 4th selection strategy unblocked and measurably working
3. First statistically meaningful strategy sweep (240 runs, 10 seeds) on real committed data
4. LoRA delivered as originally promised -- with an honest negative result, not a forced win
5. Quantization pipeline implemented and working (1.8x, 0% drop)
6. Three real bugs found and fixed in our own analysis tooling

---

## Next Steps

- Resolve the Drive-sync gap -- it now blocks nearly everything else
- Retrain `axiom_lora_v1` on the real committed dataset for a clean comparison
- Physical-device Instruments sessions for energy + memory (the two constraints never measured, ever)
- Investigate *why* pretrained ImageNet features don't transfer -- unfreeze more backbone, try higher LoRA rank, or a different pretraining source
- Trainable-model selection sweep, at a scope that doesn't require a personal laptop

---

## Thank You

**Repository**: [axiom-mobile on GitHub](https://github.com/AIML-Research-SFU/axiom-mobile)

Annie Boltwood, Mahim Chaudhary, Ariel Tyson

Simon Fraser University -- CMPT 416

Questions?
