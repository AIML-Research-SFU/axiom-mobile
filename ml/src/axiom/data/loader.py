"""JSONL dataset loading utilities for AXIOM-Mobile."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .validate import validate_rows, validate_split_overlaps

SPLITS = ("pool", "val", "test")


def _repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root is not None:
        return Path(repo_root).resolve()
    # loader.py -> data -> axiom -> src -> ml -> repo_root
    return Path(__file__).resolve().parents[4]


def _manifest_path(split: str, repo_root: str | Path | None = None) -> Path:
    if split not in SPLITS:
        raise ValueError(f"Unknown split '{split}'. Expected one of {SPLITS}.")
    return _repo_root(repo_root) / "data" / "manifests" / f"{split}.jsonl"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing manifest: {path}")

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path} line {lineno}: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(
                    f"Invalid JSON object in {path} line {lineno}: expected object"
                )
            rows.append(row)

    return rows


def load_split(
    split: str,
    repo_root: str | Path | None = None,
    validate: bool = True,
) -> list[dict[str, Any]]:
    rows = _read_jsonl(_manifest_path(split, repo_root=repo_root))
    if validate:
        validate_rows(rows, split)
    return rows


def load_all_splits(
    repo_root: str | Path | None = None,
    validate: bool = True,
) -> dict[str, list[dict[str, Any]]]:
    splits = {
        split: load_split(split, repo_root=repo_root, validate=validate)
        for split in SPLITS
    }
    if validate:
        validate_split_overlaps(splits)
    return splits

