# AXIOM-Mobile Model Selection and Baseline Scaffold

Last updated: 2026-03-15

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

### What still remains for full Phase 4

- [x] `torch.jit.trace()` the trained model — implemented in `TinyMultimodalBaseline.export_coreml()`
- [x] `coremltools.convert()` to produce `.mlpackage` — 96KB output, well under 100MB target
- [x] Post-conversion accuracy gate (<= 3% drop) — `ml/scripts/export_coreml.py` compares PyTorch vs Core ML on val/test splits
- [ ] App integration for `.mlpackage` loading
- [ ] Real on-device evaluation with actual model inference

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
