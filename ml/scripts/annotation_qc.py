#!/usr/bin/env python3
"""Quality-control summary for AXIOM-Mobile dataset manifests."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "src"))

from axiom.data import load_all_splits  # noqa: E402

ALLOWED_DIFFICULTIES = {1, 2, 3}
OPTIONAL_FIELDS = ("difficulty", "notes")


def _is_present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def _extract_numeric_suffix(value: str, prefix: str, suffix: str = "") -> int:
    if not value.startswith(prefix):
        raise ValueError(f"Expected '{value}' to start with '{prefix}'")
    if suffix and not value.endswith(suffix):
        raise ValueError(f"Expected '{value}' to end with '{suffix}'")

    core = value[len(prefix) :]
    if suffix:
        core = core[: -len(suffix)]
    if not core.isdigit():
        raise ValueError(f"Expected numeric suffix in '{value}'")
    return int(core)


def _validate_row_consistency(split_name: str, rows: list[dict[str, object]]) -> None:
    for idx, row in enumerate(rows, start=1):
        row_id = str(row["id"])
        image_filename = str(row["image_filename"])

        id_num = _extract_numeric_suffix(row_id, "ex_")
        image_num = _extract_numeric_suffix(image_filename, "img_", ".png")
        if id_num != image_num:
            raise ValueError(
                f"[{split_name}] Row {idx} has mismatched id/image pair: "
                f"{row_id} vs {image_filename}"
            )

        if _is_present(row.get("difficulty")):
            difficulty = int(row["difficulty"])
            if difficulty not in ALLOWED_DIFFICULTIES:
                raise ValueError(
                    f"[{split_name}] Row {idx} has invalid difficulty '{difficulty}'"
                )


def _optional_field_counts(rows: list[dict[str, object]]) -> dict[str, int]:
    counts = {field: 0 for field in OPTIONAL_FIELDS}
    for row in rows:
        for field in OPTIONAL_FIELDS:
            if _is_present(row.get(field)):
                counts[field] += 1
    return counts


def _difficulty_counts(rows: list[dict[str, object]]) -> Counter[int]:
    counts: Counter[int] = Counter()
    for row in rows:
        if _is_present(row.get("difficulty")):
            counts[int(row["difficulty"])] += 1
    return counts


def _note_domain(note: object) -> str:
    if not _is_present(note):
        return "missing notes"

    text = str(note).strip()
    if "→" in text:
        return text.split("→", 1)[0].strip()
    return text


def _collect_duplicates(
    rows: list[dict[str, object]], key_fn
) -> dict[object, list[str]]:
    groups: dict[object, list[str]] = defaultdict(list)
    for row in rows:
        groups[key_fn(row)].append(str(row["id"]))
    return {
        key: ids
        for key, ids in groups.items()
        if key not in ("", None) and len(ids) > 1
    }


def _print_duplicate_section(
    title: str, duplicates: dict[object, list[str]], formatter
) -> None:
    if not duplicates:
        print(f"- {title}: none")
        return

    print(f"- {title}: {len(duplicates)} patterns")
    for key, ids in sorted(duplicates.items(), key=lambda item: (-len(item[1]), str(item[0])))[:5]:
        print(f"  {formatter(key)} -> {', '.join(ids)}")


def main() -> int:
    splits = load_all_splits(repo_root=ROOT, validate=True)

    for split_name, rows in splits.items():
        _validate_row_consistency(split_name, rows)

    all_rows = [row for rows in splits.values() for row in rows]

    print("QC summary")
    print("==========")
    print("Split sizes:")
    for split_name in ("pool", "val", "test"):
        print(f"- {split_name}: {len(splits[split_name])}")
    print(f"- total: {len(all_rows)}")

    print("\nDifficulty distribution:")
    for split_name in ("pool", "val", "test"):
        difficulty_counts = _difficulty_counts(splits[split_name])
        print(
            f"- {split_name}: d1={difficulty_counts[1]}, "
            f"d2={difficulty_counts[2]}, d3={difficulty_counts[3]}"
        )

    print("\nOptional field completeness:")
    for split_name in ("pool", "val", "test"):
        field_counts = _optional_field_counts(splits[split_name])
        total = len(splits[split_name])
        print(
            f"- {split_name}: difficulty={field_counts['difficulty']}/{total}, "
            f"notes={field_counts['notes']}/{total}"
        )

    domain_counts = Counter(_note_domain(row.get("notes")) for row in all_rows)
    print("\nTop note domains:")
    for domain, count in domain_counts.most_common(8):
        print(f"- {domain}: {count}")

    print("\nReview signals:")
    duplicate_images = _collect_duplicates(all_rows, lambda row: str(row["image_filename"]).strip())
    duplicate_questions = _collect_duplicates(all_rows, lambda row: str(row["question"]).strip())
    duplicate_qa = _collect_duplicates(
        all_rows,
        lambda row: (
            str(row["question"]).strip(),
            str(row["answer"]).strip(),
        ),
    )

    _print_duplicate_section("reused image filenames", duplicate_images, str)
    _print_duplicate_section("repeated question texts", duplicate_questions, str)
    _print_duplicate_section(
        "repeated exact question/answer pairs",
        duplicate_qa,
        lambda item: f"{item[0]} -> {item[1]}",
    )

    print("\n✅ Annotation QC completed without blocking issues.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
