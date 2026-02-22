#!/usr/bin/env python3
import json
from pathlib import Path

REQUIRED_FIELDS = ["id", "image_filename", "question", "answer"]

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = {
    "pool": ROOT / "data" / "manifests" / "pool.jsonl",
    "val":  ROOT / "data" / "manifests" / "val.jsonl",
    "test": ROOT / "data" / "manifests" / "test.jsonl",
}

def read_jsonl(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in {path} line {lineno}: {e}") from e
            rows.append(obj)
    return rows

def validate(rows, name):
    ids = set()
    for i, r in enumerate(rows):
        for field in REQUIRED_FIELDS:
            if field not in r or r[field] in (None, ""):
                raise ValueError(f"[{name}] Missing/empty field '{field}' in item index {i}: {r}")
        if r["id"] in ids:
            raise ValueError(f"[{name}] Duplicate id found: {r['id']}")
        ids.add(r["id"])

def main():
    all_rows = {}
    for name, path in MANIFESTS.items():
        rows = read_jsonl(path)
        validate(rows, name)
        all_rows[name] = rows

    pool_ids = {r["id"] for r in all_rows["pool"]}
    val_ids  = {r["id"] for r in all_rows["val"]}
    test_ids = {r["id"] for r in all_rows["test"]}

    overlap = (pool_ids & val_ids) | (pool_ids & test_ids) | (val_ids & test_ids)
    if overlap:
        raise ValueError(f"IDs overlap across splits: {sorted(overlap)}")

    total = len(pool_ids) + len(val_ids) + len(test_ids)

    print("✅ Dataset manifests look valid.")
    print(f"pool: {len(pool_ids)} examples")
    print(f"val : {len(val_ids)} examples")
    print(f"test: {len(test_ids)} examples")
    print(f"TOTAL: {total} examples\n")

    print("Sample questions (first 3 from pool):")
    for r in all_rows["pool"][:3]:
        print(f"- [{r['id']}] {r['question']}  ->  {r['answer']}")

if __name__ == "__main__":
    main()
