# Selection Strategies — Phase 3 Scaffold (updated Phase 9)

Last updated: 2026-07-29

## Overview

This document describes the active-learning selection strategy scaffold, originally built in Phase 3. The sweep runner exercises multiple selection strategies over the current frozen dataset split — as of dataset v3, `pool=681`, `val=30`, `test=40` (the `pool=37/val=5/test=10` split referenced in the rest of this doc's examples is the original Phase 3 scaffold dataset; the mechanics described are unchanged, only the numbers have grown) — using the executable `question_lookup_v0` baseline.

The goal is not to produce publishable learning curves yet — the dataset and model are still small for that, though the addition of `axiom_lora_v1` (Phase 8) and dataset v3 (Phase 7) are steps toward changing that.  The goal is to validate the experiment pipeline end-to-end so that it scales cleanly as a stronger model and larger dataset become available.

## Strategies

### RAND (`random`)

**Status**: Executable

Uniform random selection with deterministic seeding.  Serves as the baseline selection strategy that all others are compared against.

### UNC (`uncertainty`)

**Status**: Executable (proxy mode)

The current executable baseline (`question_lookup_v0`) is a lookup heuristic that does not produce prediction probabilities.  Real uncertainty estimation (logit entropy, margin sampling) is not possible with this model.

**Current proxy**: metadata-based scoring using three signals available in the manifest:

1. **Difficulty** — human-assigned difficulty rating.  Higher difficulty items are harder for models and proxy for higher prediction uncertainty.
2. **Answer rarity** — answers that appear less frequently in the pool are harder to memorize.  Items with rarer answers score higher.
3. **Question-pattern rarity** — questions that appear less frequently provide less training signal, so they proxy as more uncertain.

Items are ranked by `(difficulty DESC, answer_rarity DESC, question_rarity DESC)` with deterministic seeded tie-breaking.

**When to replace**: when a real VLM with logit output is available, replace the metadata proxy with entropy-based or margin-based uncertainty scoring in `ml/src/axiom/selection/uncertainty.py`.

### DIV (`diversity`)

**Status**: Executable

Greedy farthest-first traversal over lightweight text features.  Each pool item is represented as a bag-of-words token set from its `question`, `answer`, and `notes` fields.  Distance is Jaccard distance between token sets.

The algorithm:

1. Start with a random seed item (deterministic via seed).
2. Repeatedly add the item whose minimum Jaccard distance to the selected set is largest.
3. Break ties deterministically.

This maximises pairwise diversity in the selected subset without requiring any ML dependencies.

### KG (`kg_guided`)

**Status**: Executable (Phase 9)

KG-guided selection uses `kg/entities.json` / `kg/relations.json` (KG v1, built by `ml/scripts/build_kg.py` from the dataset's own `notes`/`question`/`answer` fields — see `kg/README.md` for the full writeup). No more `NotImplementedError`; the sweep runner executes this strategy for real now.

**Algorithm**: every pool example belongs to a `(Screen, Attribute)` region — e.g. `(Settings/Wi-Fi, wifi_status)`. The selector round-robins across all distinct regions in a seeded-shuffled order, taking one item per region per pass, so a fixed budget is spent maximizing coverage breadth across the KG's entity structure before going deep into any single region.

This is a genuinely different signal from the other three strategies — not a re-skin of DIV's text-similarity distance:

- RAND ignores structure.
- UNC scores individual-example properties (difficulty, answer/question rarity).
- DIV maximizes pairwise Jaccard distance over raw question/answer/notes text.
- KG-guided uses the explicit `(App, Screen) x Attribute` structure the KG encodes.

**Measured, not asserted**: at budget=25 on the current pool (37 distinct regions total), KG-guided covers **25/37 regions** vs **11/37** for plain random sampling at the same budget.

## Running the sweep

From the repository root:

```bash
python3 ml/scripts/run_selection_sweep.py
```

Default configuration (updated Phase 10 — previously budgets up to 37 and 3 seeds, matching the old 37-example scaffold dataset):

- **Strategies**: random, uncertainty, diversity, kg_guided
- **Budgets**: 10, 25, 50, 100, 250, 500
- **Seeds**: 0 through 9 (10 seeds)
- **Model**: question_lookup_v0 (no images required)

Custom example, heuristic baseline on committed data:

```bash
python3 ml/scripts/run_selection_sweep.py \
    --strategies random uncertainty diversity kg_guided \
    --budgets 10 25 50 100 250 \
    --seeds 0 1 2 \
    --model-id question_lookup_v0 \
    --output-dir results/selection_sweeps/my_run
```

**Phase 10**: the sweep runner now supports trainable image-based models too (previously it only worked with `question_lookup_v0` — `instantiate_model()` was never called with `image_root`, so any image-based model would fail the moment `model.train()` tried to load a screenshot). New flags:

```bash
python3 ml/scripts/run_selection_sweep.py \
    --model-id axiom_lora_v1 \
    --image-root /path/to/screenshots \
    --manifest-dir /path/to/manifests \
    --epochs 20 \
    --class-weighted \
    --output-dir results/selection_sweeps/my_lora_run
```

- `--image-root` — same resolution rules as `run_trainable_baseline.py` (explicit flag, else `AXIOM_SCREENSHOT_ROOT`). Not required for `question_lookup_v0`, which never touches images.
- `--manifest-dir` — override `data/manifests/`, e.g. to point at a local-only manifest set built when the committed images aren't available on this machine (see `docs/MODEL_SELECTION.md`'s Phase 8 writeup for why that situation exists).
- `--epochs`/`--class-weighted` — forwarded to `model.train()` only if explicitly set, so `question_lookup_v0`'s fixed `train()` signature (which doesn't accept these) is unaffected by default.

**Real timing, not estimated**: a single `axiom_lora_v1` cell at the most expensive budget (500) took ~2.5 minutes. A full 4-strategy x 6-budget x 10-seed grid (240 runs) is on the order of **4 hours** of sustained CPU load — this was tried (including parallelizing across strategies to cut wall-clock time) and abandoned on a personal laptop due to heat. Treat this as a job for either a much smaller grid (fewer seeds/budgets) or non-laptop compute, not something to run synchronously or as a multi-hour background job on a machine someone is actively using.

### Budget validation

Budgets are validated against the current pool size.  Any budget exceeding the pool size is automatically dropped with a warning.  The sweep does not silently run impossible configurations.

### Output structure

```
results/selection_sweeps/<timestamp>/
├── runs/
│   ├── random_question_lookup_v0_b5_s0.json
│   ├── random_question_lookup_v0_b5_s1.json
│   ├── ...
│   └── diversity_question_lookup_v0_b37_s2.json
├── summary.json
└── summary.csv
```

Each per-run JSON contains: run_id, strategy, budget, seed, model_id, dataset fingerprint, selected example IDs, training summary, and val/test/train_subset exact-match metrics.

`summary.json` contains the aggregate sweep metadata and a flat list of per-run metrics for downstream analysis.

`summary.csv` has one row per (strategy, budget, seed) — including skipped runs — for quick inspection in a spreadsheet.

**Real Phase 10 sweep output**: `results/selection_sweeps/sweep_v1_committed/` (question_lookup_v0, committed dataset v3, 240 runs). See `docs/LEARNING_CURVES.md` for the aggregated findings.

**A matching `axiom_lora_v1` sweep was attempted and deliberately abandoned**, not just deferred: the `--image-root`/`--manifest-dir`/`--epochs`/`--class-weighted` flags documented above exist and work (verified: a single cell completed cleanly, real accuracy numbers came back), but running the full 240-run grid meant sustained heavy CPU load on a personal laptop for hours, which got uncomfortably hot. The partial results were deleted rather than kept in a half-finished state. This is a genuine, acknowledged scope limitation, not a technical blocker — see `docs/MODEL_SELECTION.md`.

## Current limitations

1. **Pool size**: 681 examples (dataset v3) is far larger than the original 37-example scaffold. The full sweep has been re-run at this scale (Phase 10) with `question_lookup_v0`.
2. **Heuristic baseline only**: `question_lookup_v0` memorizes question→answer mappings; it does not learn visual features, so strategy differences reflect memorization dynamics, not visual generalization. `axiom_lora_v1` (Phase 8) is executable and sweep-compatible, but a full-grid sweep with it is impractical on available hardware (see above) — this is consistent with every sweep this project has run to date, all of which used the heuristic baseline for exactly this reason.
3. **Uncertainty proxy**: uses metadata, not model logits.
4. **KG-guided (Phase 9)**: no longer blocked. Uses `kg/entities.json`/`kg/relations.json`, built programmatically from the dataset. See `kg/README.md` for the full writeup, including a measured coverage comparison against random sampling.
5. **Plotting available**: learning curve SVG plots are generated by `ml/scripts/generate_learning_curves.py`; see `docs/LEARNING_CURVES.md`.

## Package structure

```
ml/src/axiom/selection/
├── __init__.py          Public exports
├── base.py              SelectionStrategy ABC
├── registry.py          Name → class registry
├── random.py            RandomSelector
├── uncertainty.py       UncertaintySelector (proxy)
├── diversity.py         DiversitySelector
└── kg_guided.py         KGGuidedSelector (Phase 9: executable, uses kg/)

ml/src/axiom/kg/
├── __init__.py           Public exports
└── extract.py            KG entity/relation extraction from dataset ground truth
```
