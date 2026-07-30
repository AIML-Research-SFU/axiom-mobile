# AXIOM-Mobile Model Selection and Baseline Scaffold

Last updated: 2026-04-13

## Purpose

Phase 2 starts with two separate needs:

1. A runnable end-to-end offline baseline so the team can validate experiment plumbing.
2. A structured shortlist of real VLM candidates for later training and Core ML work.

These are not the same requirement. The runnable baseline exists to prove the pipeline works now. The VLM shortlist exists to guide the next model-selection decision.

## Executable Baseline

The current executable model is:

- `question_lookup_v0`

It is a zero-dependency heuristic baseline that:

- memorizes the most common answer for each normalized training question
- falls back to the global majority answer when the question is unseen

This model is intentionally simple. It is not a deployable multimodal model. Its job is to validate:

- data loading
- split handling
- metrics computation
- artifact writing
- result schema stability

Run it with:

```bash
python3 ml/scripts/run_baseline.py
```

Outputs are written to:

- `results/baselines/question_lookup_v0_seed0/`

## Candidate Shortlist

The current VLM candidate configs live in:

- `ml/configs/models/florence_2_base.json`
- `ml/configs/models/llava_mobile.json`
- `ml/configs/models/qwen_vl_chat_int4.json`

These are config-only placeholders until the team locks:

- exact checkpoints
- dependency versions
- hardware feasibility
- Core ML conversion approach

## Selection Rubric

The baseline candidate decision should be made using this rubric:

1. Mobile feasibility
   - plausible path to `< 100 MB` deployed footprint after compression
   - realistic on-device latency path on iPhone/M-series hardware

2. Multimodal fit
   - supports image + text reasoning directly
   - suitable for screenshot QA rather than generic captioning only

3. Engineering feasibility
   - clear Python inference/training path
   - clear export/conversion story
   - manageable dependency surface for a class project timeline

4. Research value
   - credible baseline for later selection-strategy comparisons
   - not so large that deployment becomes the only challenge

## Trainable Multimodal Baseline

As of 2026-04-12, the repo now has a second executable model:

- `tiny_multimodal_v0`

This is the first **real trainable multimodal model** in the repo. It is deliberately simple and small (~39K parameters), designed to unblock Phase 4 (Core ML conversion), not to be the final research model.

### Architecture

- **Image encoder:** 3-layer CNN (conv2d → relu × 3, adaptive_avg_pool2d) on 128×128 RGB input → 64-dim feature
- **Text encoder:** character-level embedding (ASCII, 128-vocab) + mean pool → linear → 64-dim feature
- **Fusion:** concatenation → 128-dim
- **Head:** linear → relu → linear → answer classes

### Why this model

1. **Unblocks Phase 4:** Produces a real `.pt` checkpoint that can be traced/scripted for Core ML conversion
2. **Export-friendly ops:** Only conv2d, relu, linear, embedding, adaptive_avg_pool2d — all have clean `coremltools` mappings
3. **Fixed input sizes:** 128×128 image, 128-char text — no variable-length sequences
4. **Small footprint:** ~160KB checkpoint, well under the 100MB target
5. **Image-aware:** Actually processes screenshot pixels, unlike `question_lookup_v0`

### What this model does NOT do

- It is not a strong model — accuracy on 37 training examples will be low
- It does not use pretrained weights or transfer learning
- It does not implement attention, transformers, or any VLM architecture
- It is not the final candidate for publication

### How to run

```bash
# With private screenshots:
python3 ml/scripts/run_trainable_baseline.py --image-root /path/to/screenshots_v1

# With synthetic fixtures (for testing):
python3 ml/scripts/run_trainable_baseline.py \
    --image-root results/trainable_fixtures/images \
    --manifest-dir results/trainable_fixtures/manifests \
    --output-dir results/trainable_fixtures/run_output
```

### What becomes possible after this

1. **Phase 4 Core ML conversion:** `torch.jit.trace()` the `TinyMultimodalNet` → `coremltools.convert()` → `.mlpackage`
2. **App integration:** Load the `.mlpackage` in `CoreMLInferenceService`, replacing the placeholder
3. **Real on-device profiling:** Benchmark actual model inference, not simulated latency
4. **Model upgrade path:** Replace `TinyMultimodalNet` with a stronger architecture (e.g., LoRA fine-tuned VLM) while keeping the same training/export pipeline

### Phase 4 status

- [x] `torch.jit.trace()` the trained model — implemented in `TinyMultimodalBaseline.export_coreml()`
- [x] `coremltools.convert()` to produce `.mlpackage` — 96KB output, well under 100MB target
- [x] Post-conversion accuracy gate (<= 3% drop) — `ml/scripts/export_coreml.py` compares PyTorch vs Core ML on val/test splits
- [x] Real-data training run — 37 pool / 5 val / 10 test on 52 real screenshots; 24 answer classes; train EM=16.2%, test EM=10%
- [x] App integration — `CoreMLInferenceService` loads bundled `.mlpackage`, preprocesses image+text, runs real Core ML prediction
- [x] Model catalog — `tiny_multimodal_v0` is first entry with `isCoreMLReady: true`
- [x] Benchmark pipeline — `isPlaceholder=false` for real Core ML runs; CSV + `_meta.json` export works
- [ ] Quantization — deferred (model is already 96KB)
- [x] Real on-device profiling — completed for both v0 (2 sessions) and v1 (1 session) on AT-X (iPhone 15 Pro Max, A17 Pro); p50=14.0–14.5ms, all latency thresholds PASS

## Trainable Multimodal Baseline v1 (Dataset v2 Refresh)

As of 2026-04-13, the repo has a second version of the trainable baseline:

- `tiny_multimodal_v1`

This model uses the **same architecture** as v0 (3-layer CNN + char-level text encoder + concat fusion) but is trained on **dataset v2** (382 pool examples, 128 normalized answer classes) with class-weighted cross-entropy loss.

### v0 → v1 comparison

| Metric | v0 (24 classes, dataset v1) | v1 (128 classes, dataset v2) |
|--------|----------------------------|------------------------------|
| Pool EM | 16.2% | 30.9% |
| Val EM | 0.0% | 26.7% |
| Test EM | 10.0% | 27.5% |
| Parameters | 40,376 | 47,136 |
| Training epochs | 20 | 40 |
| Class-weighted loss | No | Yes |
| Core ML accuracy drop | 0% | 0% |

### What changed

1. **128 normalized answer classes** (vs 24): classification head widened from 24 to 128 outputs
2. **Class-weighted CE loss**: inverse-frequency weights (capped at 10×) mitigate severe long-tail answer imbalance
3. **40 training epochs** (vs 20): longer training schedule for larger dataset
4. **Dataset v2**: 382 pool examples from 152 unique screenshots (vs 37 pool from 52 screenshots)

### Confidence calibration

v1 ships with an empirically calibrated confidence threshold (0.45) instead of v0's heuristic (0.40):

- **Correct predictions**: min confidence ~0.48, mean ~0.74–0.79
- **Incorrect predictions**: median confidence ~0.04, max ~0.50–0.64
- **Threshold 0.45**: preserves ~88–91% of correct predictions, filters most incorrect ones
- **Random baseline**: 1/128 = 0.78% (vs 1/24 = 4.2% for v0)

The threshold is stored in a per-model metadata sidecar (`tiny_multimodal_v1_metadata.json`), not hardcoded in Swift.

### How to run

```bash
# Train v1 on dataset v2:
python3 ml/scripts/run_trainable_baseline.py \
    --model-id tiny_multimodal_v1 \
    --image-root /path/to/screenshots_v1 \
    --epochs 40 \
    --class-weighted \
    --output-suffix _v2

# Export to Core ML:
python3 ml/scripts/export_coreml.py \
    --model-id tiny_multimodal_v1 \
    --checkpoint-dir results/trainable_baselines/tiny_multimodal_v1_seed0_v2/checkpoint \
    --image-root /path/to/screenshots_v1 \
    --output-dir results/coreml_exports/tiny_multimodal_v1_seed0_v2

# Copy artifacts into app:
cp -R results/coreml_exports/tiny_multimodal_v1_seed0_v2/TinyMultimodal.mlpackage \
    app/AXIOMMobile/AXIOMMobile/Resources/TinyMultimodalV1.mlpackage
cp results/coreml_exports/tiny_multimodal_v1_seed0_v2/label_vocab.json \
    app/AXIOMMobile/AXIOMMobile/Resources/tiny_multimodal_v1_labels.json
```

### App integration

v1 is the default model in the app. The `CoreMLInferenceService` dispatches by model ID to load the correct `.mlpackage` and label vocab. Both v0 and v1 are available in the model picker.

Model-specific behavior (confidence threshold, class count, supported question types) is driven by metadata sidecars (`{model_id}_metadata.json`) bundled in app Resources, so adding future model versions requires no Swift code changes.

## AXIOM-LoRA v1 (Phase 8: Pretrained Backbone + LoRA)

As of 2026-07-20, the repo has a third executable model:

- `axiom_lora_v1`

This replaces the from-scratch image encoder used by `tiny_multimodal_v0/v1`
with a real pretrained vision backbone, and applies LoRA to it -- the
methodology the original README promised ("LoRA (PEFT) fine-tuning") but
which was never implemented until now.

### What was attempted first, and why it's not what shipped

The original plan was a pretrained **text** tower (a small HuggingFace
transformer) fine-tuned with LoRA via `peft`, on the theory that this most
directly matches the README's stated approach. This was actually attempted,
not just considered:

1. `prajjwal1/bert-tiny` -- failed to load: its tokenizer repo predates the
   installed `transformers` (5.14.1)'s serialization format and can't be
   converted even with `sentencepiece` installed.
2. `sentence-transformers/all-MiniLM-L6-v2` -- tokenizer loaded fine, LoRA
   applied fine via `peft`, `torch.jit.trace` succeeded, but
   `coremltools.convert` failed inside the embeddings/position-id ops:
   `TypeError: only 0-dimensional arrays can be converted to Python
   scalars`.
3. To isolate the cause, the same model was traced and converted **without**
   LoRA. It failed identically -- proving the break is in the base
   pretrained transformer's traced graph (likely `transformers`' newer
   masking/position-id codegen vs. what coremltools 9.0's PyTorch frontend
   can lower), not anything LoRA-specific.

This was a pre-registered risk in the roadmap ("if the transformer text
tower doesn't convert cleanly, fall back..."), so hitting it and falling
back is the plan working as intended, not a failure to hide.

### What shipped instead

- **Image encoder:** `torchvision.models.mobilenet_v3_small` (ImageNet
  IMAGENET1K_V1 weights), entirely frozen, with a genuine LoRA adapter
  (rank=8, alpha=16, zero-initialized `up` projection per the standard LoRA
  convention) on the final 1x1 conv (96->576 channels) -- the one place in
  this architecture where "LoRA-adapting a pretrained layer" is actually
  meaningful, since everything else is trained from scratch anyway. Verified
  via direct inspection of `torchvision`'s backbone (not assumed) before
  wiring it up. BatchNorm inside the frozen backbone is held in `.eval()`
  mode permanently (even during `net.train()`) so its running statistics
  don't drift from tiny (~16-example) fine-tuning batches.
- **Text encoder:** unchanged from `tiny_multimodal_v0/v1` -- the same
  character-level embedding + linear projection. Not "LoRA-adapted",
  because there's nothing pretrained there to adapt; the char encoder was
  never the bottleneck (questions are a small set of fixed templates).
- **Fusion + classifier:** same shape as `tiny_multimodal` (concat -> linear
  -> relu -> linear), so the rest of the pipeline (training loop, vocab
  building, checkpoint format) is reused via subclassing
  (`AxiomLoraBaseline(TinyMultimodalBaseline)`, overriding only
  `_build_net()` and `export_coreml()`), not duplicated.

### A real gap this surfaced: image availability

Training needs the actual screenshot pixels, not just the manifests. The
452 examples committed before Phase 7 (52 manual + 400 v0.3.0 auto-exact)
were never synced to this machine -- Google Drive isn't set up here (same
gap flagged after Phase 7). Rather than train on just the 299 new v0.4.0
images (a small, low-diversity slice, and most of the frozen val/test split
wouldn't even resolve), the 100 v0.3.0 base scenarios were **recaptured
fresh** via the same deterministic simulator generator into a
**machine-local-only** directory
(`~/Datasets/axiom-mobile/local_base_recapture/`, `local_phase8_images/`,
`local_phase8_manifests/` -- none of this is committed or touches
`data/manifests/`), combined with the 60 delta scenarios, to get a
699-QA-pair, 158-answer-class local training set. This is **not** the
committed dataset v3 split -- it's missing the 52 manually-captured
examples and uses different image filenames/IDs, so results below aren't a
byte-for-byte comparison to `tiny_multimodal_v1`'s reported numbers.
Retraining on the real committed v3 split is a follow-up once the Drive
sync gap is closed (same blocker noted after Phase 7).

### Results (local Phase 8 dataset: pool=629, val=30, test=40, 40 epochs, class-weighted CE)

| Metric | tiny_multimodal_v1 (committed v2, from scratch) | axiom_lora_v1 (local phase8 set, pretrained+LoRA) |
|--------|---|---|
| Pool EM | 30.9% | 32.0% |
| Val EM | 26.7% | 23.3% |
| Test EM | 27.5% | 30.0% |
| Total params | ~47K | ~1.01M (927K frozen backbone + ~78K trainable) |
| Core ML size | 96 KB | 2.04 MB |
| Core ML accuracy drop | 0% | 0% |

**Honest read: this is roughly on par with v1, not a clear win.** Test EM is
a few points higher, val EM a few points lower -- within noise range for
30-40 example eval splits, and not a like-for-like comparison given the
different (local-only) dataset. The pretrained ImageNet backbone does not
obviously transfer well to "read the exact digits in a status bar" the way
it would to natural object recognition -- ImageNet pretraining optimizes
for texture/shape/object features, not precise small-text reading, and only
the final conv layer's LoRA adapter plus a linear head are actually
learning task-specific features here. This is a real, useful negative-ish
result, not a setback to obscure: it suggests the quality gap identified in
`paper/PAPER_DRAFT_v3.md` may need more than a swapped vision backbone --
worth testing with more trainable capacity (e.g. unfreezing more of the
backbone, or a higher LoRA rank) once training on the real, larger,
committed dataset is possible.

### Core ML export

`ml/scripts/export_coreml_lora.py` (parallel to `export_coreml.py`, not a
generalization of it -- matches the existing one-script-per-architecture
convention). Accuracy gate **PASSED** with **0% drop** on both val and test.
Package size **2.04 MB**, comfortably under the 100MB target.

### Latency

Only a macOS-host CoreML inference timing was run as a proxy
(`mlmodel.predict()` in a loop, p50=0.17ms) -- **this is not on-device iOS
latency** and should not be reported as such. Full integration (bundling
`AxiomLora.mlpackage` into the app, wiring `CoreMLInferenceService`, adding
a model-metadata sidecar, running `--auto-benchmark` on Simulator and then
physical device) was not done in this pass and is the clear next step
before this model's latency can be honestly compared to v0/v1's measured
14.0-14.5ms on iPhone 15 Pro Max.

### How to reproduce

```bash
# Recapture base scenarios locally (only needed if data/manifests/ images
# aren't available on your machine -- if you have the synced Drive folder,
# just point --image-root at it and use data/manifests/ directly instead).
./scripts/capture_screenshots.sh --scenarios scripts/capture_scenarios.json \
    --output ~/Datasets/axiom-mobile/local_base_recapture --batch-id local_base_recapture001

# Train
python3 ml/scripts/run_trainable_baseline.py \
    --model-id axiom_lora_v1 \
    --image-root ~/Datasets/axiom-mobile/local_phase8_images \
    --manifest-dir ~/Datasets/axiom-mobile/local_phase8_manifests \
    --epochs 40 --class-weighted

# Export + accuracy gate
python3 ml/scripts/export_coreml_lora.py \
    --checkpoint-dir results/trainable_baselines/axiom_lora_v1_seed0_local/checkpoint \
    --image-root ~/Datasets/axiom-mobile/local_phase8_images \
    --manifest-dir ~/Datasets/axiom-mobile/local_phase8_manifests
```

### Phase 8 status

- [x] De-risk spike: pretrained MobileNetV3-Small traces and converts cleanly via coremltools
- [x] De-risk spike: pretrained transformer + LoRA text tower attempted, failed at coremltools conversion (isolated to base transformer, not LoRA), fallback used per pre-registered plan
- [x] `axiom_lora_v1`: pretrained MobileNetV3-Small (frozen) + genuine LoRA adapter (rank=8) on final conv + unchanged char-level text encoder
- [x] Trained on a 699-QA-pair local reproduction of the auto-generated majority of dataset v3 (Drive sync gap blocks training on the literal committed split)
- [x] Core ML export: accuracy gate passed, 0% drop, 2.04MB package
- [ ] On-device (Simulator or physical) latency benchmarking -- needs app integration, not done this pass
- [ ] Retrain on the real committed dataset v3 split once Drive sync is available
- [ ] Quality result is a wash vs v1, not a win -- worth investigating unfreezing more backbone / higher LoRA rank once real-data training is possible

### Phase 10 addendum: a full selection-strategy sweep with axiom_lora_v1 was attempted and abandoned

Phase 10 tried to run the same 4-strategy x 6-budget x 10-seed sweep used
for `question_lookup_v0` (see `docs/SELECTION_STRATEGIES.md`,
`docs/LEARNING_CURVES.md`) with `axiom_lora_v1` instead, on the local
Phase 8 dataset (committed v3 images still unavailable on this machine).
The infrastructure work paid off -- `run_selection_sweep.py` was extended
with `--image-root`/`--manifest-dir`/`--epochs`/`--class-weighted` flags,
verified working end to end, real per-cell timing was measured (~2.5 min
at the worst-case budget) rather than guessed, and the full 240-run grid
was launched.

It was killed partway through (50/240 runs complete) and the partial
results deleted. A single sequential process was slow (interrupted by the
laptop sleeping); parallelizing across the 4 strategies plus `caffeinate`
to prevent sleep sped it up but made the machine uncomfortably hot under
sustained multi-process training load. This is a personal laptop, not
dedicated training hardware, and the honest call was to stop rather than
push through.

**What this means going forward**: `axiom_lora_v1` is real, trained,
CoreML-exported, and passes its accuracy gate (see above) -- that part of
Phase 8 stands. What doesn't exist is a full-scale strategy comparison
*using* it. If that's wanted later, it needs either a much smaller
grid (fewer seeds/budgets, e.g. 3 seeds x 3 budgets instead of 10x6) or
compute that isn't this laptop -- not a retry of the same approach.

## Phase 11: quantization, app integration, Simulator profiling

### Quantization

`ml/scripts/quantize_coreml.py` (new, Phase 11) applies int8 linear
weight quantization via `coremltools.optimize` to an exported
`.mlpackage`, then re-runs the same accuracy-drop gate discipline used at
export time (original vs quantized, not PyTorch vs CoreML). Deferred for
`tiny_multimodal_v0/v1` since those were already tiny (96KB); worth doing
for `axiom_lora_v1` since it's dominated by the frozen pretrained
backbone.

**Result**: 2.04MB -> 1.14MB (**1.80x compression**), **0% accuracy
drop** on both val and test (bit-identical predictions before/after).
One benign `RuntimeWarning: divide by zero` during quantization (a
per-channel weight with zero range, likely a bias or a dead unit) --
verified harmless given predictions match exactly.

### Real bugs found and fixed in the analysis pipeline

Running `ml/scripts/run_statistical_analysis.py` against the new Phase
10/11 data surfaced three real, pre-existing bugs, all fixed:

1. **Stale sweep hardcode**: `discover_sweep()` always loaded
   `selection_sweeps/sweep_v0` (the original 54-run Phase 3 scaffold
   sweep) because that directory always exists, so the fallback
   auto-discovery logic never triggered even after the real 240-run
   Phase 10 sweep existed alongside it. Fixed to pick whichever sweep
   directory has the most completed run files, not directory name.
2. **Stale Pareto size**: the Pareto view read `expected_app_footprint_mb`
   from a training run's embedded model-spec *snapshot* (frozen at
   train time) instead of the actual measured `mlpackage_size_mb` from
   the real CoreML export. `axiom_lora_v1`'s spec estimate was corrected
   from 6.0MB to the measured 2.04MB after Phase 8's export, but the
   training run's snapshot still had the old number. Fixed to prefer the
   measured export size when available. `export_coreml.py` (the
   original tiny_multimodal export script) was also missing this field
   entirely -- added it there too, matching `export_coreml_lora.py`.
3. **False "Memory: complete" status**: the check was `has_trace_metrics`
   (true for *any* trace sidecar, including a Time Profiler trace with no
   memory data) combined with "any physical session exists" -- so the
   AT-X `tiny_multimodal_v1` session (which only ever captured a Time
   Profiler trace, per `docs/TIMELINE.md`) made the report claim memory
   data was available when every session's `memory` field is actually
   `None`. Fixed to check specifically for `peak_memory_mb` inside
   `trace_metrics` on a physical-device session. Now correctly reports
   `physical_device_required`, matching `docs/INSTRUMENTS_RUNBOOK.md`'s
   own honest status.

### App integration

`axiom_lora_v1` is now bundled into the app locally
(`Resources/AxiomLoraV1.mlpackage`, `axiom_lora_v1_labels.json`,
`axiom_lora_v1_metadata.json` with an empirically calibrated confidence
threshold of 0.45 -- noted honestly that separation between correct/
incorrect confidence is imperfect here, unlike v1's cleaner separation),
routed through `CoreMLInferenceService`, and selectable in the model
picker. **Not** made the default model (`tiny_multimodal_v1` remains
default) -- Phase 8 found this is a wash on quality, not a win.

**Correction to "bundled" -- checked, not assumed.** `*.mlpackage` and
`*.mlmodel` are gitignored project-wide (`.gitignore` lines 29-30).
Checked whether the *existing* `TinyMultimodalV1.mlpackage` (which v0/v1
have used since Phase 4) is tracked in git: it is not (`git ls-files`
returns nothing for it). This means "bundled into the app" has never
meant "ships to a fresh clone via git" for any model in this project --
each contributor's local Xcode checkout only has a working model because
someone ran the export script locally and the file happens to sit in
`Resources/`. `axiom_lora_v1`'s integration is real and builds/runs
correctly on this machine, exactly as real as v0/v1's, and exactly as
local-only. This is a pre-existing project-wide gap, not something
introduced here -- worth a team decision (Git LFS, or a documented
manual "export and copy" step) if teammates need to build the app with
CoreML models present, but not something to unilaterally change in this
pass.

**A second real bug found while wiring this up**: `TestbedViewModel`
initialized `selectedModel` from `ModelCatalog.all[0]` (array position)
rather than the documented `defaultModelID` constant. Adding
`axiom_lora_v1` as the first picker entry would have silently made it
the *actual* default model, contradicting the "keep v1 default" decision
above purely because of list order. Fixed to resolve by `defaultModelID`
explicitly.

### Simulator profiling (pipeline validation only, not publishable)

Built Release, installed on iPhone 17 Pro Simulator (iOS 26.4), ran
`--auto-benchmark`, staged via `ml/scripts/stage_device_profile_session.py
--from-simulator`: 50 iterations, real CoreML inference
(`is_placeholder: false`), **p50 = 99.5ms**. Consistent with this
project's standing position (`docs/INSTRUMENTS_RUNBOOK.md`): Simulator
has no NPU and no real thermal behavior, so this validates the pipeline
end-to-end but is **not** a publishable latency number -- only the
physical-device numbers already in `docs/INSTRUMENTS_RUNBOOK.md` (v0/v1,
14.0-14.5ms) count as evidence.

An Allocations (memory) trace was attempted via `xctrace record
--attach` but the CLI hung across two attempts (both with and without
`--time-limit`) and was abandoned after a bounded effort rather than
burning more time on a flaky tool interaction. Memory remains
`physical_device_required` for `axiom_lora_v1`, same as it already was
for v0/v1 -- not a new gap, and consistent with this project's existing
position that even Simulator memory numbers aren't meaningful.

**Important process note**: the first attempt to regenerate
`results/device_profiles/analysis/summary.json` via
`summarize_device_profiles.py` after adding the new Simulator session
silently *dropped* the real historical AT-X physical-device sessions
from the aggregate -- those raw session folders are gitignored and were
never on this machine to begin with (same Drive-sync-adjacent gap as
elsewhere), so the summarizer only saw the 1 new local session and
rebuilt the "aggregate" from just that. Caught before committing and
reverted via `git checkout`. The new Simulator session's raw CSV/meta
exist locally (gitignored, as designed) but were **not** merged into the
committed aggregate -- doing that safely requires the historical raw
sessions, which aren't available here.

## Result Artifact Contract

Every baseline run should write:

- `run_result.json`
- `model_state.json`
- `predictions_pool.jsonl`
- `predictions_val.jsonl`
- `predictions_test.jsonl`

The result JSON must include:

- model metadata
- dataset fingerprint
- split counts
- training summary
- per-split exact-match metrics
- artifact paths
