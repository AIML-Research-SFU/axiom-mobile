"""Regenerate the auto-generated portion of the dataset's images locally,
with no Google Drive access required.

699 of dataset v3's 751 examples (93%) are auto-generated via the
deterministic simulator scenario pipeline (scripts/generate_exact_scenarios.py
+ scripts/capture_screenshots.sh). Because that pipeline is deterministic
-- same committed scenario JSON in, same simulator screenshots out -- this
script re-captures those scenarios on the current machine and matches each
resulting image back to its manifest row via the scenario_id embedded in
that row's `notes` field ("... (auto-captured: <scenario_id>)"), rather
than depending on any manually-maintained rename table.

This closes the Drive-sync gap flagged repeatedly from Phase 7 onward
(docs/TIMELINE.md, paper/PAPER_DRAFT_v4.md Section 9.2) for the auto-
generated majority of the dataset. It deliberately does NOT cover the 52
manually-captured examples (6.9% of the dataset) -- those aren't
reproducible by script and are excluded from local experiments as a
documented, bounded scope decision, not a recurring blocker.

Usage:
    xcrun simctl boot "<device UDID>"   # once, if not already booted
    python3 ml/scripts/regenerate_local_images.py \\
        --device "iPhone 17 Pro Max" \\
        --output-root ~/axiom-local-data

Produces:
    {output_root}/raw_base_v3/       -- raw v0.3.0 captures (100 scenarios)
    {output_root}/raw_delta_v04/     -- raw v0.4.0 delta captures (60 scenarios)
    {output_root}/image_root/        -- img_NNN.png files matching manifest
                                         image_filename values, ready to pass
                                         as --image-root / AXIOM_SCREENSHOT_ROOT
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
NOTES_RE = re.compile(r"auto-captured:\s*([^)]+)\)")

BATCHES = [
    ("scripts/capture_scenarios.json", "raw_base_v3", "exact_v3_batch001"),
    ("scripts/capture_scenarios_v04_delta.json", "raw_delta_v04", "v04_delta_batch001"),
]


def run_capture(device: str, output_root: Path, dry_run: bool) -> None:
    for scenarios_rel, subdir, batch_id in BATCHES:
        out_dir = output_root / subdir
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(REPO_ROOT / "scripts" / "capture_screenshots.sh"),
            "--device", device,
            "--output", str(out_dir),
            "--scenarios", str(REPO_ROOT / scenarios_rel),
            "--batch-id", batch_id,
        ]
        if dry_run:
            cmd.append("--dry-run")
        print(f"\n=== Capturing {scenarios_rel} -> {out_dir} ===")
        subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def load_scenario_to_file(output_root: Path) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    for _, subdir, _ in BATCHES:
        index_path = output_root / subdir / "capture_index.jsonl"
        if not index_path.exists():
            raise FileNotFoundError(f"missing {index_path} -- did capture succeed?")
        for line in index_path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            scenario_id = row["scenario_id"]
            image_path = output_root / subdir / row["image_filename"]
            if scenario_id in mapping:
                raise ValueError(f"duplicate scenario_id across batches: {scenario_id}")
            mapping[scenario_id] = image_path
    return mapping


def assemble_image_root(output_root: Path) -> tuple[int, int, set[str]]:
    target_dir = output_root / "image_root"
    target_dir.mkdir(parents=True, exist_ok=True)
    scenario_to_file = load_scenario_to_file(output_root)

    manual_count = 0
    auto_count = 0
    missing: set[str] = set()

    for manifest_name in ("pool.jsonl", "val.jsonl", "test.jsonl"):
        manifest_path = REPO_ROOT / "data" / "manifests" / manifest_name
        for line in manifest_path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            m = NOTES_RE.search(row.get("notes", ""))
            if not m:
                manual_count += 1
                continue

            src = scenario_to_file.get(m.group(1))
            if src is None:
                missing.add(m.group(1))
                continue

            dst = target_dir / row["image_filename"]
            if not dst.exists():
                shutil.copyfile(src, dst)
            auto_count += 1

    return auto_count, manual_count, missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="iPhone 17 Pro Max",
                         help="Simulator device name (must already be booted or bootable).")
    parser.add_argument("--output-root", default=str(Path.home() / "axiom-local-data"),
                         help="Directory to write raw captures and the assembled image root into.")
    parser.add_argument("--dry-run", action="store_true",
                         help="Pass through to capture_screenshots.sh --dry-run.")
    parser.add_argument("--skip-capture", action="store_true",
                         help="Skip re-capturing and only re-run the assembly step "
                              "(useful if raw captures already exist from a prior run).")
    args = parser.parse_args()

    output_root = Path(args.output_root).expanduser()

    if not args.skip_capture:
        run_capture(args.device, output_root, args.dry_run)

    if args.dry_run:
        return 0

    auto_count, manual_count, missing = assemble_image_root(output_root)

    print(f"\nAuto-generated rows linked to a local image: {auto_count}")
    print(f"Manual rows excluded (no local image -- documented scope decision): {manual_count}")
    if missing:
        print(f"WARNING: {len(missing)} scenario_ids in manifests had no captured file:")
        for s in sorted(missing):
            print(f"  - {s}")
        return 1

    print("No missing scenarios -- full auto-generated set resolved.")
    print(f"\nImage root ready: {output_root / 'image_root'}")
    print(f"Use with: --image-root {output_root / 'image_root'}")
    print(f"       or: export AXIOM_SCREENSHOT_ROOT={output_root / 'image_root'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
