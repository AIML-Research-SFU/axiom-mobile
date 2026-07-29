#!/usr/bin/env python3
"""Build kg/entities.json and kg/relations.json from the dataset's own
ground truth (Phase 9).

Unblocks the KG-guided selection strategy, which has been blocked since
Phase 1 (docs/TIMELINE.md: "KG v1 (~1000 entities + API + app loader) not
implemented yet."). No new labeling is done here -- entities and relations
are extracted programmatically from fields the dataset already carries
(`notes`, `question`, `answer`), the same way the auto-exact scenario
pipeline generates QA pairs without manual labeling.

Usage:
    python3 ml/scripts/build_kg.py                 # write kg/entities.json + kg/relations.json
    python3 ml/scripts/build_kg.py --dry-run        # preview counts only
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "src"))

from axiom.data import load_all_splits  # noqa: E402
from axiom.kg import extract_kg  # noqa: E402

KG_DIR = ROOT / "kg"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    parser.add_argument("--repo-root", default=str(ROOT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()

    splits = load_all_splits(repo_root=repo_root, validate=True)
    all_rows = splits["pool"] + splits["val"] + splits["test"]
    print(f"Loaded {len(all_rows)} examples (pool={len(splits['pool'])}, "
          f"val={len(splits['val'])}, test={len(splits['test'])})")

    entities, relations = extract_kg(all_rows)

    type_counts = Counter(e["type"] for e in entities)
    predicate_counts = Counter(r["predicate"] for r in relations)

    print(f"\nEntities: {len(entities)}")
    for t, c in sorted(type_counts.items()):
        print(f"  {t}: {c}")

    print(f"\nRelations: {len(relations)}")
    for p, c in sorted(predicate_counts.items()):
        print(f"  {p}: {c}")

    print(f"\nSample App/Screen entities:")
    for e in [e for e in entities if e["type"] == "Screen"][:8]:
        print(f"  {e['id']}: {e['label']}")

    if args.dry_run:
        print("\n[dry-run] No files written.")
        return 0

    KG_DIR.mkdir(exist_ok=True)

    entities_path = KG_DIR / "entities.json"
    with open(entities_path, "w") as f:
        json.dump(
            {
                "_description": (
                    "Compact KG extracted programmatically from dataset v3's "
                    "notes/question/answer fields. Regenerate with "
                    "ml/scripts/build_kg.py -- do not hand-edit."
                ),
                "_source_dataset": "data/manifests (pool+val+test)",
                "_entity_count": len(entities),
                "_type_counts": dict(sorted(type_counts.items())),
                "entities": entities,
            },
            f,
            indent=2,
        )
        f.write("\n")
    print(f"\n[write] {entities_path} ({len(entities)} entities)")

    relations_path = KG_DIR / "relations.json"
    with open(relations_path, "w") as f:
        json.dump(
            {
                "_description": (
                    "Relations for kg/entities.json. Regenerate with "
                    "ml/scripts/build_kg.py -- do not hand-edit."
                ),
                "_relation_count": len(relations),
                "_predicate_counts": dict(sorted(predicate_counts.items())),
                "relations": relations,
            },
            f,
            indent=2,
        )
        f.write("\n")
    print(f"[write] {relations_path} ({len(relations)} relations)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
