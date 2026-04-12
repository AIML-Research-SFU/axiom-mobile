# Selection Strategies — Phase 3 Scaffold

Last updated: 2026-04-12

## Overview

This document describes the Phase 3 active-learning selection strategy scaffold.  The sweep runner exercises multiple selection strategies over the current frozen dataset split (`pool=37`, `val=5`, `test=10`) using the executable `question_lookup_v0` baseline.

The goal is not to produce publishable learning curves yet — the dataset and model are too small for that.  The goal is to validate the experiment pipeline end-to-end so that it scales cleanly when a real VLM and a larger dataset are available.

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

**Status**: Blocked

KG-guided selection requires a Knowledge Graph (KG v1) with entity and relation coverage metadata.  This dependency does not exist yet:

    TIMELINE.md Phase 1: [ ] KG v1 (~1000 entities + API + app loader) not implemented yet.

The selector raises `NotImplementedError`.  The sweep runner records this as a skipped strategy and continues with the remaining strategies.

## Running the sweep

From the repository root:

```bash
python3 ml/scripts/run_selection_sweep.py
```

Default configuration:

- **Strategies**: random, uncertainty, diversity, kg_guided
- **Budgets**: 5, 10, 15, 20, 25, 37
- **Seeds**: 0, 1, 2
- **Model**: question_lookup_v0

Custom example:

```bash
python3 ml/scripts/run_selection_sweep.py \
    --strategies random uncertainty diversity \
    --budgets 5 10 20 37 \
    --seeds 0 1 \
    --model-id question_lookup_v0 \
    --output-dir results/selection_sweeps/my_run
```

### Budget validation

Budgets are validated against the current pool size.  Any budget exceeding `pool=37` is automatically dropped with a warning.  The sweep does not silently run impossible configurations.

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

## Current limitations

1. **Small pool**: 37 examples limits the granularity of learning curves.
2. **Heuristic baseline**: `question_lookup_v0` memorizes question→answer mappings; it does not learn visual features.  Strategy differences may be muted.
3. **Uncertainty proxy**: uses metadata, not model logits.
4. **KG-guided blocked**: no KG infrastructure exists yet.
5. **No plotting**: learning curve visualisation is a future step (Phase 3 continued or Phase 6).

## Package structure

```
ml/src/axiom/selection/
├── __init__.py          Public exports
├── base.py              SelectionStrategy ABC
├── registry.py          Name → class registry
├── random.py            RandomSelector
├── uncertainty.py       UncertaintySelector (proxy)
├── diversity.py         DiversitySelector
└── kg_guided.py         KGGuidedSelector (blocked)
```
