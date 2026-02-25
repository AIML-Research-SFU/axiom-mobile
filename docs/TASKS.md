# AXIOM-Mobile Next Task Breakdown

Last updated: 2026-02-25
Sprint window: 2026-02-25 to 2026-03-10

## Sprint Goal

Complete the next practical milestones after the current toy dataset:

1. Expand dataset manifests from 10 to at least 50 validated examples.
2. Add reusable dataset loading/validation code under `ml/src/axiom/data/`.
3. Add baseline CI checks so dataset and Python code quality are enforced.

## Workload Split (Even)

Each person is assigned **6 points** of work:
- 2 points: data labeling contribution
- 3 points: implementation task
- 1 point: peer review/QA

## Ariel Tyson (6 points)

- `[ ]` **Labeling batch (2 pts):** add examples `ex_011` to `ex_024` in `data/manifests/pool.jsonl`.
- `[ ]` **ML data module (3 pts):** create initial reusable loader/validator package:
  - `ml/src/axiom/data/__init__.py`
  - `ml/src/axiom/data/loader.py`
  - `ml/src/axiom/data/validate.py`
- `[ ]` **Peer QA (1 pt):** review Annie’s labeled items for schema, clarity, and exact-answer format.

Deliverables:
- PR 1: `data: add Ariel labeling batch (ex_011-ex_024)`
- PR 2: `ml: add reusable dataset loader and validator module`

## Annie Boltwood (6 points)

- `[ ]` **Labeling batch (2 pts):** add examples `ex_025` to `ex_038` in `data/manifests/pool.jsonl`.
- `[ ]` **Data quality tooling (3 pts):** add annotation QC helper script:
  - `ml/scripts/annotation_qc.py`
  - Computes per-field completeness and duplicate checks
  - Outputs a short QC summary in terminal
- `[ ]` **Peer QA (1 pt):** review Mahim’s labeled items for ambiguity and grounding quality.

Deliverables:
- PR 1: `data: add Annie labeling batch (ex_025-ex_038)`
- PR 2: `data: add annotation QC helper script`

## Mahim Chaudhary (6 points)

- `[ ]` **Labeling batch (2 pts):** add examples `ex_039` to `ex_052` in `data/manifests/pool.jsonl`.
- `[ ]` **CI baseline (3 pts):** add GitHub Actions workflow(s):
  - `.github/workflows/python-checks.yml`
  - Run `python3 ml/scripts/inspect_dataset.py`
  - Run a basic Python lint/test command scaffold (non-blocking if tests are not yet present)
- `[ ]` **Peer QA (1 pt):** review Ariel’s labeled items for schema compliance and answer precision.

Deliverables:
- PR 1: `data: add Mahim labeling batch (ex_039-ex_052)`
- PR 2: `ci: add baseline Python and dataset validation workflow`

## Shared Team Tasks

- `[ ]` Resolve peer-review comments before merge.
- `[ ]` Run `python3 ml/scripts/inspect_dataset.py` after each labeling PR update.
- `[ ]` Freeze first 50 examples after merge and rebalance splits into:
  - `pool.jsonl`: 35
  - `val.jsonl`: 5
  - `test.jsonl`: 10
- `[ ]` Update [TIMELINE.md](/Users/arieltyson/Desktop/SFU/Research/CMPT%20416/Repo/axiom-mobile/docs/TIMELINE.md) progress checkboxes after all PRs merge.

## Definition of Done

- At least 50 examples exist across manifests with no duplicate IDs.
- `ml/scripts/inspect_dataset.py` passes on merged `main`.
- New `ml/src/axiom/data/` module is present and importable.
- CI runs automatically on PRs and validates dataset manifests.
- All three teammates contributed equal effort (6 points each).
