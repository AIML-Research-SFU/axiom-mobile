# AXIOM-Mobile Timeline and Progress Tracker

Last updated: 2026-03-15

This file tracks the 16-week project plan and marks what is complete based on the current repository state.

## Status Legend

- `[x]` Complete (verified in repo)
- `[~]` In progress / partially complete
- `[ ]` Not started or not verifiable from repo

## Quick Verification: Annie + Mahim Deliverables

### Annie (Step 1: schema + repo rules)

- `[x]` `data/schema/example.schema.json` exists and defines the dataset example format.
- `[x]` `data/README.md` exists with labeling and privacy rules.
- `[x]` `.gitignore` blocks raw screenshot/image files (`data/raw/`, `data/images/`, `*.png`, `*.jpg`, `*.jpeg`, `*.heic`, `*.webp`).
- `[ ]` Branch/PR workflow steps are not verifiable from local files alone.

### Mahim (Step 2: toy dataset + split + inspector)

- `[x]` `data/manifests/pool.jsonl`, `val.jsonl`, and `test.jsonl` are populated.
- `[x]` Initial toy dataset milestone was completed; current manifests now contain 52 total examples.
- `[x]` `ml/scripts/inspect_dataset.py` exists and validates required fields + split overlap.
- `[x]` `python3 ml/scripts/inspect_dataset.py` runs successfully on current manifests.
- `[x]` Shared private screenshot storage is now verifiable from Drive screenshots (`archive/`, `review/`, `screenshots_v0/`, `screenshots_v1/`).
- `[ ]` Branch/PR workflow steps are not verifiable from local files alone.

## 16-Week Timeline (Planned vs Current State)

## Phase 0 (Week 0-1): Repo and Workflow Foundation

- `[x]` Data schema path exists: `data/schema/example.schema.json`.
- `[x]` Manifest files exist: `data/manifests/{pool,val,test}.jsonl`.
- `[x]` Dataset validation script exists: `ml/scripts/inspect_dataset.py`.
- `[~]` Repo skeleton exists (`app/`, `ml/`, `kg/`, `results/`) but many components are placeholders.
- `[x]` CI workflows exist for repo guards and dataset validation (`.github/workflows/guards.yml`, `.github/workflows/python-checks.yml`).

Deliverable status: `[~]` Partially complete.

## Phase 1 (Weeks 1-4): Dataset Curation

- `[x]` Labeling protocol/rules documented (`data/README.md`).
- `[x]` Initial toy dataset created (10 examples total).
- `[x]` Splits are present (pool/val/test).
- `[x]` Shared Google Drive folder structure exists for private screenshots (`archive/`, `review/`, `screenshots_v0/`, `screenshots_v1/`).
- `[x]` Dataset has been expanded beyond the first 50-example checkpoint (52 total examples in manifests).
- `[~]` `screenshots_v1/` exists but is not populated yet, so the finalized dataset freeze has not happened.
- `[ ]` Dataset v1 target (200+ screenshots, 500+ QA pairs) not reached yet.
- `[ ]` Dual-annotator agreement workflow (Cohen's kappa >= 0.75) not implemented in repo.
- `[ ]` Bounding box grounding metadata pipeline not implemented.
- `[ ]` KG v1 (~1000 entities + API + app loader) not implemented yet.

Deliverable status: `[~]` In progress.

## Phase 2 (Weeks 5-6): Model Selection and Baseline

- `[ ]` Model harness (`train()`, `predict()`, `export_coreml()`) not present.
- `[ ]` Candidate model configs (Florence/LLaVA/Qwen-VL) not present.
- `[ ]` Baseline training artifacts/metrics not present.
- `[ ]` SwiftUI testbed shell not present in repo.
- `[ ]` Core ML baseline conversion pipeline not present.

Deliverable status: `[ ]` Not started in current codebase.

## Phase 3 (Weeks 7-10): Selection Strategies and Training Pipeline

- `[ ]` Selection strategy interfaces (RAND/UNC/DIV/KG) not implemented.
- `[ ]` Sweep runner (4 strategies x 6 budgets x 3 seeds) not implemented.
- `[ ]` Learning curve generation scripts/plots not present.
- `[ ]` App model picker + CSV logging hooks not present.

Deliverable status: `[ ]` Not started in current codebase.

## Phase 4 (Weeks 11-12): Compression and Core ML Conversion

- `[ ]` Quantization pipeline not implemented.
- `[ ]` Automated PyTorch -> Core ML export pipeline not implemented.
- `[ ]` Post-conversion accuracy-drop gate (<= 3%) not implemented.
- `[ ]` App integration for `.mlpackage` loading not implemented.

Deliverable status: `[ ]` Not started in current codebase.

## Phase 5 (Weeks 13-14): On-Device Evaluation

- `[ ]` Benchmark mode in app not implemented.
- `[ ]` Instruments profiling runbook not present.
- `[ ]` Full device evaluation CSV logs not present.
- `[ ]` Final quality + performance metric computation pipeline not present.

Deliverable status: `[ ]` Not started in current codebase.

## Phase 6 (Weeks 15-16): Analysis and Publication

- `[ ]` Statistical analysis package (power-law fits, paired tests, Pareto analysis) not present.
- `[ ]` Paper draft file(s) not present in repo.
- `[ ]` Demo flow integration and final presentation assets not present.

Deliverable status: `[ ]` Not started in current codebase.

## Next Practical Milestones

- `[x]` Expand manifests from 10 -> 50 examples while keeping question/answer quality constraints.
- `[x]` Add a reusable Python dataset module under `ml/src/axiom/data/` (loader + validation + split stats).
- `[~]` Add baseline CI workflows for Python checks. Dataset validation exists, but placeholder iOS checks are still missing.
