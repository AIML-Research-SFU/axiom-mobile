#!/usr/bin/env python3

import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]

MANIFESTS = [
    ROOT / "data" / "manifests" / "pool.jsonl",
    ROOT / "data" / "manifests" / "val.jsonl",
    ROOT / "data" / "manifests" / "test.jsonl",
]

FIELDS = [
    "id",
    "image_filename",
    "question",
    "answer",
    "difficulty",
    "notes",
]


def read_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main():
    all_rows = []

    for path in MANIFESTS:
        if not path.exists():
            print(f"Warning: missing {path}")
            continue

        rows = read_jsonl(path)
        all_rows.extend(rows)

    total = len(all_rows)

    print("\n========== DATASET QC SUMMARY ==========\n")
    print(f"Total examples: {total}\n")

    # -------- Field completeness --------
    print("Field completeness:")

    for field in FIELDS:
        present = sum(
            1 for r in all_rows if field in r and r[field] not in ("", None)
        )
        percent = (present / total) * 100 if total else 0
        print(f"{field:15} {present}/{total} ({percent:.1f}%)")

    print()

    # -------- Duplicate checks --------
    ids = [r.get("id") for r in all_rows]
    images = [r.get("image_filename") for r in all_rows]

    id_counts = Counter(ids)
    image_counts = Counter(images)

    dup_ids = [k for k, v in id_counts.items() if v > 1]
    dup_imgs = [k for k, v in image_counts.items() if v > 1]

    print("Duplicate checks:")

    print(f"Duplicate IDs: {len(dup_ids)}")
    if dup_ids:
        print(" ", dup_ids)

    print(f"Duplicate image filenames: {len(dup_imgs)}")
    if dup_imgs:
        print(" ", dup_imgs)

    print()

    # -------- Answer length stats --------
    answers = [r.get("answer", "") for r in all_rows if "answer" in r]

    if answers:
        lengths = [len(a) for a in answers]

        print("Answer length stats:")
        print(f"Min length: {min(lengths)}")
        print(f"Max length: {max(lengths)}")
        print(f"Avg length: {sum(lengths)/len(lengths):.2f}")

    print("\n========================================\n")


if __name__ == "__main__":
    main()
