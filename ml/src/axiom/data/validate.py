"""Validation helpers for AXIOM-Mobile JSONL manifests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

REQUIRED_FIELDS = ("id", "image_filename", "question", "answer")


def _is_empty_string(value: object) -> bool:
    return isinstance(value, str) and value.strip() == ""


def validate_rows(rows: Sequence[Mapping[str, object]], split_name: str) -> None:
    """Validate a single split for required fields and duplicate IDs."""
    seen_ids: set[str] = set()

    for idx, row in enumerate(rows, start=1):
        for field in REQUIRED_FIELDS:
            value = row.get(field)
            if value is None or _is_empty_string(value):
                raise ValueError(
                    f"[{split_name}] Missing/empty '{field}' at row {idx}: {row}"
                )

        row_id = str(row["id"])
        if row_id in seen_ids:
            raise ValueError(f"[{split_name}] Duplicate id '{row_id}'")
        seen_ids.add(row_id)


def validate_split_overlaps(splits: Mapping[str, Sequence[Mapping[str, object]]]) -> None:
    """Ensure split IDs are disjoint."""
    ids_by_split: dict[str, set[str]] = {
        split_name: {str(row["id"]) for row in rows}
        for split_name, rows in splits.items()
    }

    split_names = list(ids_by_split.keys())
    for i, left_name in enumerate(split_names):
        for right_name in split_names[i + 1 :]:
            overlap = ids_by_split[left_name] & ids_by_split[right_name]
            if overlap:
                raise ValueError(
                    f"ID overlap between {left_name} and {right_name}: {sorted(overlap)}"
                )

