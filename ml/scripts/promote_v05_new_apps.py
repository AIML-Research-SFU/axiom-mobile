#!/usr/bin/env python3
"""Promote the v0.5.0 new-app captures (Safari synthetic pages + Contacts)
into data/manifests/pool.jsonl.

Why this isn't just index_generated_screenshots.py --auto-promote: that
tool classifies purely from each scenario's declared qa_pairs, which
can't know that a specific capture came out broken (blank page / stale
UI) at capture time -- verified here to happen even for scenarios NOT
marked as a deliberate `_warmup` scenario (e.g. `web04` in the run this
was built against: 4 real-content scenarios were still on the
transitional Start Page despite 3 throwaway warmup captures ahead of
them). Every capture already records `file_size_bytes`
(capture_screenshots.sh), and the blank/broken band is empirically and
consistently separated from the real-content band (~117KB vs ~150-160KB,
confirmed against direct visual inspection of multiple captures in both
bands) -- so file size is used as an automated, verified correctness
gate here, in addition to (not instead of) excluding scenarios with
qa_pairs == [] (deliberate warmup captures).

Usage:
    python3 ml/scripts/promote_v05_new_apps.py --input ~/axiom-local-data/raw_v05 --dry-run
    python3 ml/scripts/promote_v05_new_apps.py --input ~/axiom-local-data/raw_v05 --execute
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFESTS_DIR = REPO_ROOT / "data" / "manifests"
MIN_GOOD_FILE_SIZE_BYTES = 130_000  # see module docstring


def load_capture_index(input_dir: Path) -> list[dict[str, Any]]:
    entries = []
    for line in (input_dir / "capture_index.jsonl").read_text().splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def next_start_id() -> int:
    """Highest ex_NNN across pool/val/test, plus 1."""
    max_id = 0
    for name in ("pool.jsonl", "val.jsonl", "test.jsonl"):
        for line in (MANIFESTS_DIR / name).read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            n = int(row["id"].split("_")[1])
            max_id = max(max_id, n)
    return max_id + 1


def build_rows(entries: list[dict[str, Any]], start_id: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Returns (promoted_rows, skipped_entries)."""
    promoted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    next_id = start_id

    for entry in entries:
        qa_pairs = entry.get("qa_pairs", [])
        if not qa_pairs:
            continue  # deliberate warmup capture, nothing to promote

        file_size = entry.get("file_size_bytes", 0)
        if file_size < MIN_GOOD_FILE_SIZE_BYTES:
            skipped.append(entry)
            continue

        for qa in qa_pairs:
            row = {
                "id": f"ex_{next_id:03d}",
                "image_filename": f"img_{next_id}.png",
                "question": qa["question"],
                "answer": qa["answer"],
                "difficulty": qa.get("difficulty", 1),
                "notes": entry["notes"],
            }
            promoted.append({**row, "_source_image": str(Path(entry["image_filename"]))})
            next_id += 1

    return promoted, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Raw capture directory (contains capture_index.jsonl)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    input_dir = Path(args.input).expanduser()
    entries = load_capture_index(input_dir)
    start_id = next_start_id()
    promoted, skipped = build_rows(entries, start_id)

    print(f"Loaded {len(entries)} captures from {input_dir}")
    print(f"Next available id: ex_{start_id:03d}")
    print(f"\nSkipped (file_size < {MIN_GOOD_FILE_SIZE_BYTES:,} bytes -- verified-broken capture):")
    for e in skipped:
        print(f"  {e['id']} ({e['scenario_id']}): {e['file_size_bytes']:,} bytes")
    print(f"\nPromoted: {len(promoted)} QA rows from {len({p['_source_image'] for p in promoted})} screenshots")
    for p in promoted[:5]:
        clean = {k: v for k, v in p.items() if not k.startswith("_")}
        print(f"  {json.dumps(clean)}")
    if len(promoted) > 5:
        print(f"  ... and {len(promoted) - 5} more")

    if not args.execute:
        print("\n[dry-run] No files written. Pass --execute to write.")
        return 0

    pool_path = MANIFESTS_DIR / "pool.jsonl"
    with open(pool_path, "a") as f:
        for p in promoted:
            clean = {k: v for k, v in p.items() if not k.startswith("_")}
            f.write(json.dumps(clean) + "\n")
    print(f"\nAppended {len(promoted)} rows to {pool_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
