# AXIOM-Mobile Paper Workspace

Last updated: 2026-04-13

## Contents

| File | Description |
|------|-------------|
| `PAPER_DRAFT_v1.md` | First-pass research paper skeleton grounded in current repo results |
| `PAPER_DRAFT_v2.md` | Revision with physical-device latency evidence from AT-X (iPhone 15 Pro Max) |
| `assets/generated/` | Machine-generated figures, tables, and snapshots (do not hand-edit) |

## Generated Assets

Run the asset generator to (re-)produce paper-ready outputs from the current analysis artifacts:

```bash
python3 ml/scripts/build_paper_assets.py
```

This reads from `results/analysis/phase6_v0/` and `results/device_profiles/analysis/` and writes to `paper/assets/generated/`. Outputs are deterministic — same inputs always produce the same files.

| Asset | Source | Description |
|-------|--------|-------------|
| `learning_curves.svg` | `results/analysis/phase6_v0/learning_curves.svg` | Copied from analysis output |
| `model_comparison.csv` | `results/analysis/phase6_v0/summary.json` | Flat model comparison table |
| `device_profile_summary.csv` | `results/device_profiles/analysis/summary.json` | Per-session latency summary |
| `results_snapshot.md` | Multiple sources | Concise machine-generated results packet |

## Versioning

The draft is numbered (`v1`, `v2`, ...) to track major revisions. Create a new version file (e.g., `PAPER_DRAFT_v2.md`) rather than overwriting the previous version, so the team can diff between drafts.

## Honest status

This is a **first-pass draft** grounded in current repo outputs:
- All results are from the current 52-example dataset with a heuristic lookup + tiny multimodal baseline
- Physical-device latency evidence now available (iPhone 15 Pro Max: p50=14.0ms, p95=26.2ms); energy and memory still pending
- The 70% EM target is not met (~10% test EM)
- The draft explicitly marks these limitations throughout

## Next steps

1. ~~Acquire physical-device profiling data~~ (DONE -- 2 sessions on AT-X, iPhone 15 Pro Max)
2. ~~Revise draft with real device results~~ (DONE -- PAPER_DRAFT_v2.md)
3. Scale dataset and retrain with a stronger model
4. Final formatting for target venue (6-8 page format per SPEC.md)
