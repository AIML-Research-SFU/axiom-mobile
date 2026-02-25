#!/usr/bin/env python3
"""Validate and summarize AXIOM-Mobile manifests."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "src"))

from axiom.data import load_all_splits  # noqa: E402


def main() -> None:
    all_rows = load_all_splits(repo_root=ROOT, validate=True)

    pool_ids = {row["id"] for row in all_rows["pool"]}
    val_ids = {row["id"] for row in all_rows["val"]}
    test_ids = {row["id"] for row in all_rows["test"]}
    total = len(pool_ids) + len(val_ids) + len(test_ids)

    print("✅ Dataset manifests look valid.")
    print(f"pool: {len(pool_ids)} examples")
    print(f"val : {len(val_ids)} examples")
    print(f"test: {len(test_ids)} examples")
    print(f"TOTAL: {total} examples\n")

    print("Sample questions (first 3 from pool):")
    for row in all_rows["pool"][:3]:
        print(f"- [{row['id']}] {row['question']}  ->  {row['answer']}")


if __name__ == "__main__":
    main()
