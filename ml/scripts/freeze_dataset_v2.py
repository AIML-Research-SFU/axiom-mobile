#!/usr/bin/env python3
"""Dataset v2 freeze: deterministic split rebalancing with stratification.

Merges all current entries (pool + val + test) and re-splits them into
balanced pool/val/test sets that reflect the expanded task and answer space.

Key properties:
  - Deterministic: uses a fixed random seed → same output every time
  - Stratified: val/test sample from each question-type stratum
  - Versioned: archives v1 manifests, writes SHA256 fingerprint
  - Safe: dry-run mode previews changes without writing

Usage:
    python3 ml/scripts/freeze_dataset_v2.py                # preview (dry-run)
    python3 ml/scripts/freeze_dataset_v2.py --execute       # write manifests
    python3 ml/scripts/freeze_dataset_v2.py --execute --archive-v1  # archive v1 first
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS_DIR = ROOT / "data" / "manifests"

# ── Configuration ────────────────────────────────────────────────────
SEED = 20260413          # deterministic seed for reproducibility
VAL_COUNT = 30           # target val size
TEST_COUNT = 40          # target test size
# remainder goes to pool

# Question type classification for stratification
QUESTION_TYPE_PATTERNS: list[tuple[str, str]] = [
    ("time", "time"),
    ("battery percentage", "battery_pct"),
    ("battery charging", "charging"),
    ("signed into", "apple_account"),
    ("search bar", "search_bar"),
    ("wi-fi", "wifi_status"),
    ("bluetooth", "bluetooth_status"),
    ("cellular", "cellular_status"),
    ("airplane", "airplane_mode"),
    ("temperature", "temperature"),
    ("lock screen", "lock_screen"),
    ("calculator", "calculator"),
    ("equation", "calculator"),
    ("map", "maps"),
    ("weather", "weather"),
    ("clock", "clock"),
    ("airdrop", "control_center"),
    ("app store", "app_store"),
    ("low power", "battery_settings"),
    ("color", "visual_detail"),
    ("city", "location"),
    ("date", "date"),
    ("visual mode", "map_style"),
]


def _classify_question(question: str) -> str:
    """Assign a question-type stratum based on the question text."""
    q_lower = question.lower()
    for pattern, qtype in QUESTION_TYPE_PATTERNS:
        if pattern in q_lower:
            return qtype
    return "other"


def load_all_entries() -> list[dict[str, Any]]:
    """Load entries from all three splits."""
    all_entries: list[dict[str, Any]] = []
    for split in ("pool", "val", "test"):
        path = MANIFESTS_DIR / f"{split}.jsonl"
        if not path.exists():
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    entry["_source_split"] = split
                    all_entries.append(entry)
    return all_entries


def stratified_split(
    entries: list[dict[str, Any]],
    val_count: int,
    test_count: int,
    seed: int,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Deterministic stratified split.

    Ensures val and test sets sample proportionally from each question
    type stratum, so they represent the expanded answer space.
    """
    rng = random.Random(seed)

    # Group by question type
    strata: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        qtype = _classify_question(entry["question"])
        entry["_question_type"] = qtype
        strata[qtype].append(entry)

    # Shuffle within each stratum
    for qtype_entries in strata.values():
        rng.shuffle(qtype_entries)

    total = len(entries)
    eval_count = val_count + test_count
    val_set: list[dict] = []
    test_set: list[dict] = []
    pool_set: list[dict] = []

    # Proportional allocation per stratum, alternating val/test for rare types
    alternate_to_test = False  # toggle for single-eval strata
    for qtype, qtype_entries in sorted(strata.items()):
        n = len(qtype_entries)
        # How many from this stratum go to eval (val + test)?
        stratum_eval = max(1, round(n * eval_count / total))
        # Don't take more than n-1 (leave at least 1 for pool)
        stratum_eval = min(stratum_eval, n - 1) if n > 1 else 0

        eval_entries = qtype_entries[:stratum_eval]
        pool_entries = qtype_entries[stratum_eval:]

        if len(eval_entries) == 1:
            # Rare type: alternate between val and test for coverage
            if alternate_to_test:
                test_set.extend(eval_entries)
            else:
                val_set.extend(eval_entries)
            alternate_to_test = not alternate_to_test
        elif len(eval_entries) > 1:
            # Split eval into val/test proportionally, ensuring at least 1 each
            stratum_val = max(1, round(len(eval_entries) * val_count / eval_count))
            stratum_val = min(stratum_val, len(eval_entries) - 1)  # leave ≥1 for test

            val_set.extend(eval_entries[:stratum_val])
            test_set.extend(eval_entries[stratum_val:])

        pool_set.extend(pool_entries)

    # If we overshot or undershot val/test, rebalance from pool
    # (move excess eval back to pool, or pull more from pool)
    rng.shuffle(pool_set)

    while len(val_set) > val_count and pool_set:
        pool_set.append(val_set.pop())
    while len(test_set) > test_count and pool_set:
        pool_set.append(test_set.pop())

    while len(val_set) < val_count and pool_set:
        val_set.append(pool_set.pop())
    while len(test_set) < test_count and pool_set:
        test_set.append(pool_set.pop())

    # Sort each split by ID for deterministic output
    def sort_key(e: dict) -> int:
        try:
            return int(e["id"].replace("ex_", ""))
        except (ValueError, AttributeError):
            return 0

    pool_set.sort(key=sort_key)
    val_set.sort(key=sort_key)
    test_set.sort(key=sort_key)

    return pool_set, val_set, test_set


def write_manifest(path: Path, entries: list[dict[str, Any]]) -> None:
    """Write entries to JSONL, stripping internal metadata fields."""
    with open(path, "w") as f:
        for entry in entries:
            clean = {k: v for k, v in entry.items() if not k.startswith("_")}
            f.write(json.dumps(clean) + "\n")


def compute_fingerprint(manifests_dir: Path) -> dict[str, str]:
    """SHA256 fingerprint for each manifest file."""
    fingerprints: dict[str, str] = {}
    for split in ("pool", "val", "test"):
        path = manifests_dir / f"{split}.jsonl"
        if path.exists():
            content = path.read_bytes()
            fingerprints[split] = hashlib.sha256(content).hexdigest()
    return fingerprints


def archive_v1(manifests_dir: Path) -> Path:
    """Archive current manifests to v1/ subdirectory."""
    v1_dir = manifests_dir / "v1"
    v1_dir.mkdir(exist_ok=True)
    for split in ("pool", "val", "test"):
        src = manifests_dir / f"{split}.jsonl"
        if src.exists():
            shutil.copy2(src, v1_dir / f"{split}.jsonl")
    return v1_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dataset v2 freeze with deterministic stratified splitting"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Write manifests (default is dry-run preview)",
    )
    parser.add_argument(
        "--archive-v1",
        action="store_true",
        help="Archive current manifests to data/manifests/v1/ before overwriting",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=SEED,
        help=f"Random seed for deterministic split (default: {SEED})",
    )
    parser.add_argument(
        "--val-count",
        type=int,
        default=VAL_COUNT,
        help=f"Target val set size (default: {VAL_COUNT})",
    )
    parser.add_argument(
        "--test-count",
        type=int,
        default=TEST_COUNT,
        help=f"Target test set size (default: {TEST_COUNT})",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  AXIOM-Mobile Dataset v2 Freeze")
    print("=" * 60)

    # Load all entries
    entries = load_all_entries()
    print(f"\nLoaded {len(entries)} total entries from current manifests")

    source_counts = Counter(e.get("_source_split", "unknown") for e in entries)
    for split, count in sorted(source_counts.items()):
        print(f"  {split}: {count}")

    # Classify question types
    qtype_counts: Counter[str] = Counter()
    for e in entries:
        qtype = _classify_question(e["question"])
        qtype_counts[qtype] += 1

    print(f"\nQuestion type distribution ({len(qtype_counts)} types):")
    for qtype, count in qtype_counts.most_common():
        print(f"  {qtype}: {count}")

    # Unique answers
    answer_counts = Counter(e["answer"] for e in entries)
    print(f"\nUnique answers: {len(answer_counts)}")
    print(f"  Most common: {answer_counts.most_common(5)}")

    # Unique images
    image_set = set(e["image_filename"] for e in entries)
    print(f"Unique image filenames: {len(image_set)}")

    # Perform split
    pool, val, test = stratified_split(
        entries,
        val_count=args.val_count,
        test_count=args.test_count,
        seed=args.seed,
    )

    print(f"\nProposed v2 split (seed={args.seed}):")
    print(f"  pool: {len(pool)} entries")
    print(f"  val:  {len(val)} entries")
    print(f"  test: {len(test)} entries")
    print(f"  total: {len(pool) + len(val) + len(test)} entries")

    # Show val/test question type coverage
    val_types = Counter(_classify_question(e["question"]) for e in val)
    test_types = Counter(_classify_question(e["question"]) for e in test)
    print(f"\n  Val question types: {dict(val_types.most_common())}")
    print(f"  Test question types: {dict(test_types.most_common())}")

    # Verify no overlaps
    pool_ids = {e["id"] for e in pool}
    val_ids = {e["id"] for e in val}
    test_ids = {e["id"] for e in test}
    assert pool_ids.isdisjoint(val_ids), "pool/val overlap!"
    assert pool_ids.isdisjoint(test_ids), "pool/test overlap!"
    assert val_ids.isdisjoint(test_ids), "val/test overlap!"
    print(f"\n  No overlaps between splits.")

    if not args.execute:
        print(f"\n[dry-run] No files written. Use --execute to apply.")
        print(f"\nSample val entries:")
        for e in val[:5]:
            print(f"  [{e['id']}] Q: {e['question']}  A: {e['answer']}")
        print(f"\nSample test entries:")
        for e in test[:5]:
            print(f"  [{e['id']}] Q: {e['question']}  A: {e['answer']}")
        return

    # Archive v1
    if args.archive_v1:
        v1_dir = archive_v1(MANIFESTS_DIR)
        print(f"\n[archive] v1 manifests saved to {v1_dir}")
        # Compute v1 fingerprint
        v1_fp = compute_fingerprint(v1_dir)
        fp_path = v1_dir / "fingerprint.json"
        with open(fp_path, "w") as f:
            json.dump({"version": "v1", "sha256": v1_fp}, f, indent=2)
            f.write("\n")
        print(f"  v1 fingerprint: {fp_path}")
        for split, sha in v1_fp.items():
            print(f"    {split}: {sha[:16]}...")

    # Write new manifests
    write_manifest(MANIFESTS_DIR / "pool.jsonl", pool)
    write_manifest(MANIFESTS_DIR / "val.jsonl", val)
    write_manifest(MANIFESTS_DIR / "test.jsonl", test)
    print(f"\n[write] Manifests written:")
    print(f"  pool.jsonl: {len(pool)} entries")
    print(f"  val.jsonl:  {len(val)} entries")
    print(f"  test.jsonl: {len(test)} entries")

    # Compute and write v2 fingerprint
    v2_fp = compute_fingerprint(MANIFESTS_DIR)
    fp_path = MANIFESTS_DIR / "v2_fingerprint.json"
    with open(fp_path, "w") as f:
        json.dump({
            "version": "v2",
            "seed": args.seed,
            "split_sizes": {
                "pool": len(pool),
                "val": len(val),
                "test": len(test),
            },
            "sha256": v2_fp,
        }, f, indent=2)
        f.write("\n")
    print(f"\n[fingerprint] {fp_path}")
    for split, sha in v2_fp.items():
        print(f"  {split}: {sha[:16]}...")

    print(f"\nDataset v2 freeze complete.")
    print(f"\nNext steps:")
    print(f"  1. python3 ml/scripts/inspect_dataset.py")
    print(f"  2. python3 ml/scripts/annotation_qc.py")


if __name__ == "__main__":
    main()
