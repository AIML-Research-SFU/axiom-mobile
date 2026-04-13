# Phase 6 Statistical Analysis Package

Last updated: 2026-04-13

## Overview

The Phase 6 statistical analysis package ingests all experiment artifacts produced across Phases 2-5 and computes honest, reproducible summary statistics. Every result carries an explicit status from a fixed vocabulary so downstream consumers (paper draft, presentation) can never accidentally overstate what the data supports.

**What this package does:**

- Aggregates learning curves across strategies, budgets, and seeds
- Computes bootstrap confidence intervals for all point estimates
- Fits power-law scaling curves when the data is non-degenerate
- Performs paired bootstrap comparisons between strategies
- Separates simulator and physical-device latency data
- Computes Pareto-optimal quality-vs-efficiency frontiers
- Writes reproducible JSON, CSV, Markdown, and SVG outputs

**What this package does NOT prove today:**

1. No physical-device latency evidence (all data is from iOS Simulator)
2. No statistical significance claims (3 seeds, tiny test/val sets)
3. No quality conclusions (70% EM target not met; ~10% test EM)
4. No energy/memory conclusions (require physical-device Instruments traces)

## Inputs

The runner script (`ml/scripts/run_statistical_analysis.py`) discovers artifacts from these directories:

| Source | Path | Content |
|--------|------|---------|
| Heuristic baselines | `results/baselines/*/run_result.json` | Pool/val/test EM for question_lookup_v0 |
| Trainable baselines | `results/trainable_baselines/*/run_result.json` | Pool/val/test EM for tiny_multimodal_v0 |
| Selection sweeps | `results/selection_sweeps/sweep_v0/summary.json` | 3 strategies x 6 budgets x 3 seeds |
| CoreML exports | `results/coreml_exports/*/conversion_report.json` | Model size, parameter count |
| Device profiles | `results/device_profiles/analysis/summary.json` | Latency percentiles per session |

All paths are relative to the project root. The script resolves them automatically.

## Outputs

Written to `results/analysis/phase6_v0/` (configurable via `--output-dir`):

| File | Format | Purpose |
|------|--------|---------|
| `summary.json` | JSON | Complete machine-readable analysis with all nested results |
| `summary.csv` | CSV | Flat model comparison table (model_id, type, EM scores, latency, size) |
| `analysis.md` | Markdown | Human-readable report with tables, fits, and caveats |
| `learning_curves.svg` | SVG | Deterministic learning-curve plot (stdlib xml.etree, no matplotlib) |

## Usage

```bash
# Default output directory
python3 ml/scripts/run_statistical_analysis.py

# Custom output directory
python3 ml/scripts/run_statistical_analysis.py --output-dir results/analysis/phase6_v1
```

The script uses only Python stdlib (no numpy, scipy, or matplotlib). It is deterministic: the same inputs always produce the same outputs.

## Statistical Methods

### Bootstrap Confidence Intervals

All confidence intervals use the **percentile bootstrap** method with 10,000 resamples and a fixed RNG seed (42) for reproducibility.

**Why bootstrap instead of parametric tests?**

- Sample sizes are tiny: 3 seeds per strategy-budget combination, 5-50 observations per session.
- The normality assumption required by t-tests and z-intervals is dubious with n=3.
- Bootstrap makes no distributional assumptions — it resamples from the empirical distribution.

**Behavior at edge cases:**

| n | Status | CI behavior |
|---|--------|-------------|
| 0 | `insufficient_data` | Returns (0, 0, 0) |
| 1 | `insufficient_data` | Degenerate: CI = point estimate |
| 2-4 | `partial` | CI computed but flagged as potentially unreliable |
| 5+ | `complete` | Standard bootstrap CI |

Implementation: `ml/src/axiom/analysis/stats.py :: bootstrap_ci()`

### Paired Bootstrap Comparisons

Strategy comparisons use **paired bootstrap resampling** of the difference in means (A - B), where pairs are matched by seed index.

**Why paired instead of independent?**

- The same seeds produce correlated results across strategies (same data splits, same random selections at each budget). Pairing by seed removes this shared variance.
- Independent two-sample tests would treat correlated observations as independent, inflating variance estimates.

Skipped when pair counts differ or n < 2.

Implementation: `ml/src/axiom/analysis/stats.py :: paired_bootstrap_diff()`

### Power-Law Fitting

Learning curves are fit to the model `y = a * x^b` via **log-log ordinary least squares**:

```
log(y) = log(a) + b * log(x)
```

R² is reported in log-space. Mean absolute residuals are reported in original scale.

**When fitting is attempted vs skipped:**

| Condition | Status | Reason |
|-----------|--------|--------|
| < 3 data points | `insufficient_data` | Not enough points for meaningful fit |
| < 2 non-zero y values | `degenerate` | Curve is flat at zero; power law is meaningless |
| All x values identical | `degenerate` | Cannot compute slope |
| Otherwise | `complete` | Fit performed with R² and residuals |

Only positive (x, y) pairs are used (log requires > 0). Zero y-values are filtered out before fitting.

Implementation: `ml/src/axiom/analysis/stats.py :: fit_power_law()`

## Simulator vs Physical-Device Separation

This is a core design principle: **simulator and physical-device data are never mixed**.

- Device-profile sessions are classified by checking for `"sim"` in the session directory name.
- Simulator latency validates the instrumentation pipeline but is NOT publishable on-device evidence.
- Physical-device sessions would require: real iPhone connected via USB, Release build, `BenchmarkInputProvider` with real or synthetic screenshot input, Instruments traces (Time Profiler, Allocations, Energy Log).

The analysis report labels every latency measurement with its environment. The Pareto analysis includes latency environment as a visible column.

**What requires physical device (not available from Simulator):**

| Metric | Why |
|--------|-----|
| Latency | Simulator has no NPU, different CPU scheduling |
| Memory (Allocations) | Simulator memory model differs from device |
| Energy (Energy Log) | Only available on physical hardware; Instruments reports relative levels (0-20 scale) |
| Thermal behavior | No thermal throttling on Simulator |

## Status Vocabulary

Every analysis result carries an explicit `status` field from this fixed vocabulary:

| Status | Meaning |
|--------|---------|
| `complete` | Analysis performed with sufficient data |
| `partial` | Analysis performed but with caveats (small n, limited seeds) |
| `blocked` | Cannot proceed due to missing dependency |
| `insufficient_data` | Not enough observations to compute meaningful statistics |
| `simulator_only` | Data exists but only from Simulator (not publishable) |
| `physical_device_required` | Metric requires physical hardware not yet available |
| `skipped` | Analysis intentionally skipped (e.g., mismatched pair counts) |
| `degenerate` | Data is degenerate (e.g., all zeros); statistical method is inapplicable |

Defined in: `ml/src/axiom/analysis/schemas.py :: AnalysisStatus`

## Module Structure

```
ml/src/axiom/analysis/
    __init__.py          — Package docstring
    schemas.py           — Typed dataclass schemas for all analysis outputs
    stats.py             — Statistical helper functions (bootstrap, power-law, percentile)

ml/scripts/
    run_statistical_analysis.py  — Main runner: discovery, analysis, output generation
```

## Current Results (phase6_v0)

As of 2026-04-13, the analysis reflects:

- **Dataset:** 52 examples (pool=37, val=5, test=10), 24 answer classes
- **Strategies analyzed:** random, diversity, uncertainty (kg_guided skipped — requires KG v1)
- **Budgets:** 5, 10, 15, 20, 25, 37
- **Seeds:** 3 per strategy-budget
- **Models:** question_lookup_v0 (heuristic), tiny_multimodal_v0 (trainable, 40K params, 96KB CoreML)
- **Device profiles:** 2 simulator sessions, 0 physical-device sessions
- **Overall status:** `partial`

Key findings:
- Both models achieve ~10% test EM (1/10 correct) and 0% val EM
- Heuristic baseline's 73% pool EM reflects memorization, not generalization
- All pairwise strategy comparisons show 0.0 difference at full-pool budget (all converge to same EM)
- Power-law fits have low R² (0.17 for diversity, 0.02 for random) — expected with tiny, noisy data
- Uncertainty strategy is degenerate (all-zero test EM except at budget=37)

## Extending This Package

**Adding physical-device data:** Drop new session folders into `results/device_profiles/` following the session contract in `docs/DEVICE_PROFILES.md`, re-run `ml/scripts/summarize_device_profiles.py`, then re-run the analysis script. No code changes needed.

**Adding more seeds or strategies:** Re-run the selection sweep with additional configurations, then re-run the analysis script. Discovery is automatic.

**Upgrading to a real model:** Train a larger model, export via `ml/scripts/export_coreml.py`, run baseline evaluation, and re-run analysis. The Pareto view will automatically include the new model.
