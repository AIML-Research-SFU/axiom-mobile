# Learning Curve Analysis — Phase 3 (updated Phase 10)

Last updated: 2026-07-29

## Overview

The learning-curve analysis layer aggregates per-run sweep results into strategy-level statistics and generates deterministic visual artifacts.  It reads a sweep `summary.json` (produced by `run_selection_sweep.py`), groups runs by `(strategy, budget)` across seeds, and outputs structured data plus SVG plots.

## Running the analysis

From the repository root:

```bash
python3 ml/scripts/generate_learning_curves.py \
    --sweep-dir results/selection_sweeps/sweep_v0
```

Custom output directory:

```bash
python3 ml/scripts/generate_learning_curves.py \
    --sweep-dir results/selection_sweeps/sweep_v0 \
    --output-dir results/selection_sweeps/analysis
```

If no `--output-dir` is given, artifacts are written to `<sweep-dir>/analysis/`.

## Output artifacts

| File | Description |
|------|-------------|
| `learning_curve_summary.json` | Structured aggregate: mean/min/max val\_em and test\_em per (strategy, budget), plus sweep metadata and skipped strategies |
| `learning_curve_summary.csv` | Flat table with one row per (strategy, budget) — importable in any spreadsheet tool |
| `learning_curve_val.svg` | Validation exact-match vs training budget, one line per strategy with min/max bands |
| `learning_curve_test.svg` | Test exact-match vs training budget, same format |

## SVG plot details

- **640 x 400 px**, white background, axis labels, grid lines.
- **Colorblind-friendly palette** (Tol bright): random `#4477AA`, uncertainty `#EE6677`, diversity `#228833`, kg\_guided `#CCBB44`.
- Each strategy is drawn as a mean polyline with dot markers, plus a translucent min/max band polygon.
- Generated with `xml.etree.ElementTree` — **no matplotlib or external dependencies**.
- Output is deterministic given the same `summary.json`.

## Phase 10 results (dataset v3, 10 seeds, all 4 strategies executed)

`results/selection_sweeps/sweep_v1_committed/` — the first sweep run on the
real **committed dataset v3** (`pool=681`, `val=30`, `test=40`), widened to
budgets `{10, 25, 50, 100, 250, 500}` and **10 seeds** (up from 3), with
`kg_guided` actually executing instead of being skipped (KG v1 landed in
Phase 9). Still `question_lookup_v0` — see the "Still open" caveat below.

Real, honest observations from `learning_curve_summary.csv`:

1. **At small budgets (10), random clearly wins**: test EM 31.5% vs
   diversity's 4.25% and kg\_guided's 10.25%. This is a genuine, if
   heuristic-specific, finding: `question_lookup_v0` memorizes per
   normalized-question strings, so it needs to see repeated examples of
   the *same* question pattern to generalize. Diversity and KG-guided
   both deliberately spread a tiny budget across many distinct
   regions/topics, which starves the memorization heuristic of repeats
   for any one pattern. Random naturally over-samples the dominant
   question types (time/battery/charging are ~65% of the pool) and wins
   *for this reason specific to a lookup model* — not necessarily evidence
   it would win with a real learned model.
2. **The gap closes and inverts at budgets 50-250**: kg\_guided edges out
   random at b=50 (39.5% vs 37.0% test EM) and b=100 (38.5% vs 36.25%).
   Once the budget is large enough to give the memorization heuristic a
   few repeats per region even under coverage-first selection, KG-guided's
   breadth becomes a net positive rather than a liability.
3. **Uncertainty is erratic and mostly poor** (0-5% test EM for most
   budgets, an unexplained jump to 27.5% at b=500) — consistent with the
   existing caveat that the uncertainty proxy (difficulty/rarity-based,
   not real model logits) may select pathological examples for a
   memorization-style baseline.
4. **All strategies converge near budget=500** (close to full pool),
   as expected.

**Still open, deliberately**: this is `question_lookup_v0`, not a real
learned model. The sweep runner itself never wired `image_root` through
to trainable models before Phase 10 (fixed — see
`ml/scripts/run_selection_sweep.py`'s `--image-root`/`--manifest-dir`
flags, verified working on a single cell). A full 240-run grid with
`axiom_lora_v1` was attempted on the local Phase 8 dataset (the committed
v3 images still aren't available on this machine — Drive sync gap from
Phase 7) but abandoned partway through: sustained multi-hour training
load got the laptop uncomfortably hot, even after parallelizing across
strategies to cut wall-clock time. The partial results were deleted
rather than kept half-finished. This is a real, acknowledged limitation
of running this class of experiment on personal laptop hardware, not a
technical gap — see `docs/MODEL_SELECTION.md`.

## Interpreting the original Phase 3 results (historical)

The original sweep used the `question_lookup_v0` heuristic baseline over a much smaller frozen split (`pool=37`, `val=5`, `test=10`).  Key observations at the time:

1. **Validation EM is 0.0 for all strategies and budgets.**  The 5 val examples happen not to overlap with any memorized question→answer mapping, regardless of which pool subset is selected.
2. **Test EM is low (0–20%) and noisy.**  With only 10 test items and a lookup heuristic, small differences in selected subsets produce large per-seed variance.
3. **All strategies converge at budget=37** (full pool) — expected, since every strategy selects the same complete pool.
4. **kg\_guided is recorded as skipped** throughout the entire pipeline (sweep → summary → analysis → CSV/SVG) — this is what Phase 9 unblocked.

These results validated the pipeline end-to-end.  They were **not** meaningful learning curves — that required a larger dataset (Phase 7) and a KG (Phase 9), both now in place; a real learned model (Phase 8) is the remaining piece for the *committed* dataset.

## Current limitations

1. **Heuristic baseline only**: `question_lookup_v0` memorizes exact question→answer strings; it does not learn visual features, so strategy differences reflect memorization dynamics, not visual generalization. `axiom_lora_v1` is executable (Phase 8) and sweep-compatible (Phase 10), but a full-grid sweep with it was attempted and abandoned due to sustained heavy CPU load on personal laptop hardware — see the note above.
2. **No confidence intervals yet**: 10 seeds is enough for min/max bands to be meaningful but bootstrap CIs (Phase 12) haven't been computed for this sweep yet.
3. **No matplotlib**: stdlib SVG generation is sufficient for the current stage; richer plots can be added when publication-quality figures are needed.

## Regenerating from scratch

To regenerate everything from a fresh sweep:

```bash
# 1. Run the selection sweep
python3 ml/scripts/run_selection_sweep.py \
    --output-dir results/selection_sweeps/sweep_v0

# 2. Generate learning-curve analysis
python3 ml/scripts/generate_learning_curves.py \
    --sweep-dir results/selection_sweeps/sweep_v0
```

Both scripts are deterministic given the same dataset manifests and seeds.
