"""Abstract base class for data selection strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SelectionStrategy(ABC):
    """Interface for pool-subset selection in active-learning sweeps.

    Each strategy receives the full pool and returns a list of indices
    representing the selected training subset.  Strategies must be
    deterministic for a given (pool, budget, seed) triple.
    """

    name: str

    @abstractmethod
    def select(
        self,
        pool: list[dict[str, Any]],
        budget: int,
        seed: int,
    ) -> list[int]:
        """Return *budget* indices into *pool*.

        Parameters
        ----------
        pool:
            The full pool split loaded from ``data/manifests/pool.jsonl``.
        budget:
            Number of examples to select (must be <= len(pool)).
        seed:
            Random seed for reproducibility.

        Returns
        -------
        list[int]
            Indices into *pool* (0-based, no duplicates, length == budget).
        """

    def _validate(self, pool_size: int, budget: int) -> None:
        if budget < 1:
            raise ValueError(f"Budget must be >= 1, got {budget}")
        if budget > pool_size:
            raise ValueError(
                f"Budget ({budget}) exceeds pool size ({pool_size})"
            )
