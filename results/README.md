# AXIOM-Mobile Results

This directory stores experiment artifacts that are generated locally and are not intended to be committed in full.

## Baseline Runs

The Phase 2 scaffold writes lightweight baseline runs to:

- `results/baselines/<model_id>_seed<seed>/`

Current executable baseline:

- `question_lookup_v0`

Expected files per run:

- `run_result.json`
- `model_state.json`
- `predictions_pool.jsonl`
- `predictions_val.jsonl`
- `predictions_test.jsonl`

`run_result.json` is the canonical summary artifact for later analysis.

## Selection Sweeps

Phase 3 sweep results are written to:

- `results/selection_sweeps/sweep_v0/`

See `docs/SELECTION_STRATEGIES.md` and `docs/LEARNING_CURVES.md` for details.

## Device Profiles

Phase 5 on-device profiling sessions are stored under:

- `results/device_profiles/{device}_{model_id}_{timestamp}/`

Each session directory contains the app-exported CSV + `_meta.json`, plus optional `trace_metrics.json` (manually extracted Instruments data) and raw `.trace` files.

The summary pipeline (`ml/scripts/summarize_device_profiles.py`) ingests sessions and writes analysis artifacts to `results/device_profiles/analysis/`.

Synthetic test fixtures live in `results/device_profiles/_fixtures/` and are not production data.

### First real session

The first real Core ML profiling session was captured on 2026-04-12:
- `iphone17pro-sim_tiny_multimodal_v0_20260412T212027Z/` — iPhone 17 Pro Simulator, 20 iterations, `is_placeholder: false`
- Latency: p50=199.5ms (PASS), p95=304.2ms (PASS)
- Simulator-only — not publishable; validates the full pipeline end-to-end

### Staging new sessions

Use the staging script to copy app exports into the correct folder structure:

```bash
python3 ml/scripts/stage_device_profile_session.py \
    --from-simulator --device-name "iphone17pro-sim"
```

See `docs/DEVICE_PROFILES.md` for the full session contract, schema, and threshold evaluation documentation.
