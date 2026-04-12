"""Typed result schema for baseline experiment runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class SplitMetrics:
    split_name: str
    num_examples: int
    num_correct: int
    exact_match: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BaselineRunResult:
    run_id: str
    created_at_utc: str
    model: dict[str, Any]
    dataset: dict[str, Any]
    training: dict[str, Any]
    metrics: dict[str, dict[str, Any]]
    artifacts: dict[str, str]
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SelectionRunResult:
    """Result of a single selection-strategy experiment run."""

    run_id: str
    created_at_utc: str
    strategy: str
    budget: int
    seed: int
    model_id: str
    dataset: dict[str, Any]
    selected_ids: list[str]
    training: dict[str, Any]
    metrics: dict[str, dict[str, Any]]
    notes: str = ""
    status: str = "completed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SweepSummary:
    """Aggregate summary of a full selection sweep."""

    sweep_id: str
    created_at_utc: str
    config: dict[str, Any]
    dataset: dict[str, Any]
    strategies_executed: list[str]
    strategies_skipped: list[dict[str, str]]
    runs: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
