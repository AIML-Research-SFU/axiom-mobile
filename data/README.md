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
- `data/manifests/pool.jsonl` → unlabeled pool candidates or training pool
- `data/manifests/val.jsonl` → validation set manifest
- `data/manifests/test.jsonl` → test set manifest

Do not store raw data in this repo.
