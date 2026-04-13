# AXIOM-Mobile Dataset Rules (v0)

This repo stores **labels only** (JSONL manifests).  
**Raw screenshots MUST NOT be committed to Git.**

---

## What is one example?

One example is:
- a screenshot (stored privately, outside this repo)
- a question about what is visible in the screenshot
- the correct answer (short and exact)

We store these examples as **JSON Lines** in `data/manifests/*.jsonl`:
- one JSON object per line
- each JSON object follows the schema in `data/schema/example.schema.json`

---

## Critical Rules

### 1) Do not commit images
Do NOT commit any screenshot files to git:
- png, jpg, jpeg, heic, webp

Screenshots live in a shared private folder (e.g., Google Drive).  
This repo only contains filenames like `img_001.png`.

Enforcement:
- Local pre-commit guard: run `bash scripts/install-hooks.sh` once per clone.
- CI guard: PRs run `.github/workflows/guards.yml` and fail if image files are tracked.

### 2) Questions must be answerable by looking
Your question must be answerable directly from visible content.
Avoid interpretation and opinions.

Good:
- "What is the battery percentage shown?"
- "Is Wi-Fi on or off?"
- "What time is shown on the lock screen?"

Bad:
- "Is this a good battery life?"
- "What should the user do next?"

### 3) Answers must be short and exact
Answers should be:
- a number, word, or short phrase
- no explanations
- no extra punctuation unless it appears in the screenshot (e.g., 82%)

### 4) Filenames must be stable
Use consistent screenshot filenames in private storage:
- img_001.png, img_002.png, ...

The JSONL must match those names exactly.

---

## Where files go

- `data/schema/example.schema.json` → definition of one example
- `data/manifests/pool.jsonl` → training pool (382 entries in v2)
- `data/manifests/val.jsonl` → validation set manifest (30 entries in v2)
- `data/manifests/test.jsonl` → test set manifest (40 entries in v2)
- `data/manifests/v1/` → archived v1 manifests with SHA256 fingerprints
- `data/manifests/v2_fingerprint.json` → SHA256 fingerprints for v2 manifests

Do not store raw data in this repo.

---

## Dataset Versions

### v2 (current) — 452 examples

Deterministic freeze with stratified split rebalancing (seed=20260413).

| Split | Count | Question Types |
|-------|-------|---------------|
| pool  | 382   | 20 types (time, battery%, charging, Apple Account, search bar, Wi-Fi, Bluetooth, etc.) |
| val   | 30    | 9 types (includes rare: bluetooth, cellular, airplane, other) |
| test  | 40    | 9 types (includes rare: calculator, maps, app_store, temperature) |

Sources: 52 manual hand-labeled + 400 auto-generated exact-answer entries.

Freeze script: `python3 ml/scripts/freeze_dataset_v2.py --execute --archive-v1`

### v1 (archived) — 127 examples

Original dataset with unbalanced splits (pool=112, val=5, test=10).
Archived in `data/manifests/v1/` with fingerprints.

---

## Review and Freeze Workflow

### 1) Working screenshots stay in private storage
Use the shared Drive working folder for screenshots under review:
- `screenshots_v0/` → active working set
- `screenshots_v1/` → reviewed frozen set
- `review/` → screenshots that need fixes or discussion
- `archive/` → replaced or rejected screenshots

### 2) Every manifest row must match the screenshot exactly
Before freezing an example, the reviewer must confirm:
- the screenshot exists in Drive with the exact `image_filename`
- the question is answerable directly from visible content
- the answer matches what is shown on screen exactly
- there is no private information that should be removed or cropped

### 3) Run the repo QC scripts before freezing
From the repo root, run:

```bash
python3 ml/scripts/inspect_dataset.py
python3 ml/scripts/annotation_qc.py
```

`inspect_dataset.py` is the blocking structural validator.
`annotation_qc.py` prints a QC summary for completeness, duplicate checks, and split stats.

### 4) Freeze only approved screenshots
After review passes:
- keep the working copy in `screenshots_v0/`
- copy the approved final image into `screenshots_v1/`
- move superseded or unusable files into `archive/`

This keeps the research dataset reproducible while preserving the working history.

---

## Automated Dataset Scaling

### Exact-answer promotion (auto_exact)

The screenshot automation harness (`scripts/generate_exact_scenarios.py` + `scripts/capture_screenshots.sh`) can generate examples with deterministic exact answers. These are auto-promoted to `pool.jsonl` via:

```bash
python3 ml/scripts/index_generated_screenshots.py \
  --input ~/Datasets/axiom-mobile/generated_screenshots \
  --promote --start-id <next_id> --auto-promote
```

Auto-exact answers are only emitted when the scenario state is controlled:
- Status bar time/battery — set by `xcrun simctl status_bar`
- Battery charging indicator — set by `--batteryState`
- Apple Account sign-in state — deterministic on fresh simulator
- App-specific defaults — verified by visual inspection

### Label status classification

| Status | Meaning | Where it goes |
|--------|---------|--------------|
| `auto_exact` | Answer is deterministic and visually verified | Appended to `pool.jsonl` automatically |
| `needs_review` | Answer hint provided, needs human verification | Stays in `generated_candidates.jsonl` |
| `needs_labeling` | No answer provided | Stays in `generated_candidates.jsonl` |

### Screenshot naming

Auto-generated screenshots use `gen_XXXX_<scenario>.png` naming during capture. When promoted to manifests, entries use canonical `img_NNN.png` naming (matching `ex_NNN` IDs). The `rename_map.json` file maps capture filenames to manifest filenames for copying to Drive.

### What is NOT auto-promoted

- Toggle states unless the test explicitly controls them
- Dynamic content (weather, live data, network names)
- Content requiring scrolling or navigation
- Any val/test split entries (always manual)

See `docs/SCREENSHOT_AUTOMATION.md` for the full pipeline documentation.
