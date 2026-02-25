# AXIOM-Mobile Timeline and Progress Tracker

Last updated: 2026-02-25

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
- `[x]` Current split is 7/1/2 (10 total) and matches the expected toy split.
- `[x]` `ml/scripts/inspect_dataset.py` exists and validates required fields + split overlap.
- `[x]` `python3 ml/scripts/inspect_dataset.py` runs successfully on current manifests.
- `[ ]` Private screenshot storage setup is not verifiable from repo.
- `[ ]` Branch/PR workflow steps are not verifiable from local files alone.

## 16-Week Timeline (Planned vs Current State)

## Phase 0 (Week 0-1): Repo and Workflow Foundation

- `[x]` Data schema path exists: `data/schema/example.schema.json`.
- `[x]` Manifest files exist: `data/manifests/{pool,val,test}.jsonl`.
- `[x]` Dataset validation script exists: `ml/scripts/inspect_dataset.py`.
- `[~]` Repo skeleton exists (`app/`, `ml/`, `kg/`, `results/`) but many components are placeholders.
- `[ ]` CI workflows are planned but not implemented (`.github/workflows/` currently empty).

Deliverable status: `[~]` Partially complete.

## Phase 1 (Weeks 1-4): Dataset Curation

- `[x]` Labeling protocol/rules documented (`data/README.md`).
- `[x]` Initial toy dataset created (10 examples total).
- `[x]` Splits are present (pool/val/test).
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

1. Expand manifests from 10 -> 50 examples while keeping question/answer quality constraints.
2. Add a reusable Python dataset module under `ml/src/axiom/data/` (loader + validation + split stats).
3. Add baseline CI workflows for Python lint/test and placeholder iOS checks.
