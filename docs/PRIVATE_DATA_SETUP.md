# Private Data Setup

Last updated: 2026-04-12

## Overview

AXIOM-Mobile stores raw screenshots outside the git repository for privacy compliance. Training and Core ML export scripts need access to these images at runtime via a **screenshot root** directory.

The canonical screenshot folder is `screenshots_v1/` in the shared Google Drive.

## Quick Start

### Option A: Set environment variable (recommended)

```bash
export AXIOM_SCREENSHOT_ROOT=/path/to/screenshots_v1
```

Add this to your shell profile (`~/.zshrc` or `~/.bashrc`) so it persists across sessions.

### Option B: Pass explicitly to scripts

```bash
python3 ml/scripts/run_trainable_baseline.py --image-root /path/to/screenshots_v1
python3 ml/scripts/export_coreml.py --image-root /path/to/screenshots_v1
```

### Option C: Run the auto-discovery script

```bash
python3 ml/scripts/locate_screenshot_root.py
```

This searches common macOS locations for Google Drive synced folders.

## Where to Get the Screenshots

1. Open the shared Google Drive folder (link in team docs).
2. Navigate to `screenshots_v1/`.
3. Either:
   - **Sync via Google Drive for Desktop** — the discovery script will find it automatically under `~/Library/CloudStorage/GoogleDrive-*/My Drive/`.
   - **Download the folder** — place it somewhere stable (e.g., `~/Desktop/screenshots_v1/`).

## Verification

After setting up, verify the root is valid:

```bash
python3 ml/scripts/locate_screenshot_root.py
```

Expected output:

```
  FOUND: /path/to/screenshots_v1
  Images: <count>
```

## Using Synthetic Fixtures (No Screenshots)

For pipeline testing without real screenshots, use the synthetic fixtures:

```bash
python3 ml/scripts/run_trainable_baseline.py \
    --image-root results/trainable_fixtures/images \
    --manifest-dir results/trainable_fixtures/manifests \
    --output-dir results/trainable_fixtures/run_output

python3 ml/scripts/export_coreml.py \
    --checkpoint-dir results/trainable_fixtures/run_output/checkpoint \
    --image-root results/trainable_fixtures/images \
    --manifest-dir results/trainable_fixtures/manifests \
    --output-dir results/trainable_fixtures/coreml_output
```

## Common Issues

| Symptom | Fix |
|---|---|
| `ValueError: No image root configured` | Set `AXIOM_SCREENSHOT_ROOT` or pass `--image-root` |
| `FileNotFoundError: Missing images` | Ensure all filenames in manifests have matching files in the screenshot root |
| Discovery script finds folder but "no images" | The folder may be a sync placeholder — open it in Finder to trigger download |
| Google Drive for Desktop not showing | Check `~/Library/CloudStorage/` for `GoogleDrive-*` entries |

## Data Policy Reminder

- Raw screenshots are **never committed** to git (blocked by `.gitignore`).
- Only filenames are stored in manifest JSONL files.
- Screenshots are referenced by `image_filename` field in manifests.
- See `data/README.md` for the full labeling and privacy policy.
