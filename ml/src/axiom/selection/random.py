"""Random (uniform) selection strategy."""

from __future__ import annotations

import random as _random
from typing import Any

from .base import SelectionStrategy


class RandomSelector(SelectionStrategy):
    """Uniform random selection with deterministic seeding.

    This is the baseline selection strategy.  It picks *budget*
    indices from the pool uniformly at random using a seeded RNG.
    """

    name = "random"

    def select(
        self,
        pool: list[dict[str, Any]],
        budget: int,
        seed: int,
    ) -> list[int]:
        self._validate(len(pool), budget)
        rng = _random.Random(seed)
        indices = list(range(len(pool)))
        rng.shuffle(indices)
        return sorted(indices[:budget])
