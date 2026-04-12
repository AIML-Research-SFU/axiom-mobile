"""Diversity-maximising selection strategy.

Uses a greedy farthest-first traversal over lightweight text features
extracted from each pool item's question, answer, and notes fields.
Distance is Jaccard distance between token sets.

This requires no ML dependencies — just stdlib string operations.
"""

from __future__ import annotations

import random as _random
from typing import Any

from .base import SelectionStrategy


def _token_set(row: dict[str, Any]) -> frozenset[str]:
    """Extract a bag-of-words feature set from a pool item."""
    tokens: list[str] = []
    for field in ("question", "notes", "answer"):
        text = str(row.get(field, "")).lower()
        tokens.extend(text.split())
    return frozenset(tokens)


def _jaccard_distance(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 0.0
    return 1.0 - len(a & b) / len(a | b)


class DiversitySelector(SelectionStrategy):
    """Greedy farthest-first selection maximising pairwise diversity.

    1. Start with a random seed item (deterministic via *seed*).
    2. Repeatedly add the item whose minimum Jaccard distance to
       the already-selected set is largest.
    3. Break ties deterministically using the seeded shuffle order.

    Complexity is O(budget * pool_size) which is fine for the current
    37-item pool and scales to a few thousand items.
    """

    name = "diversity"

    def select(
        self,
        pool: list[dict[str, Any]],
        budget: int,
        seed: int,
    ) -> list[int]:
        self._validate(len(pool), budget)

        rng = _random.Random(seed)
        features = [_token_set(row) for row in pool]

        # Pick a random starting item.
        first = rng.randrange(len(pool))
        selected: list[int] = [first]
        remaining = set(range(len(pool))) - {first}

        while len(selected) < budget and remaining:
            best_idx = -1
            best_min_dist = -1.0

            # Tie-break order: iterate remaining in a shuffled but
            # deterministic order so the first max-distance candidate
            # encountered wins consistently.
            candidates = sorted(remaining)
            rng.shuffle(candidates)

            for i in candidates:
                min_dist = min(
                    _jaccard_distance(features[i], features[j])
                    for j in selected
                )
                if min_dist > best_min_dist:
                    best_min_dist = min_dist
                    best_idx = i

            selected.append(best_idx)
            remaining.discard(best_idx)

        return sorted(selected)
