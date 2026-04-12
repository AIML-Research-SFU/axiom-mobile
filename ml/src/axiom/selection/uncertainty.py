"""Uncertainty-proxy selection strategy.

The current executable baseline (question_lookup_v0) does not produce
real prediction probabilities.  This module implements an honest
metadata-based proxy:

1. **Difficulty** — the human-assigned difficulty rating on each
   example.  Higher difficulty items are harder for models and serve
   as a proxy for prediction uncertainty.

2. **Answer rarity** — answers that appear less frequently in the
   pool are harder to memorize, making those examples more
   "uncertain" for a lookup-style baseline.

3. **Question-pattern rarity** — questions that appear less
   frequently are less likely to be memorized.

All three signals are available in the current manifest metadata and
require no model inference.  When a real VLM with logit output is
available, this proxy should be replaced with entropy-based or
margin-based uncertainty scoring.
"""

from __future__ import annotations

import random as _random
from collections import Counter
from typing import Any

from .base import SelectionStrategy


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _uncertainty_scores(pool: list[dict[str, Any]]) -> list[tuple[int, float, float]]:
    """Score each pool item (higher = more uncertain).

    Returns a list of (difficulty, answer_rarity, question_rarity)
    tuples aligned with *pool* indices.
    """
    answers = [_normalize(str(row.get("answer", ""))) for row in pool]
    questions = [_normalize(str(row.get("question", ""))) for row in pool]

    answer_counts = Counter(answers)
    question_counts = Counter(questions)

    scores: list[tuple[int, float, float]] = []
    for i, row in enumerate(pool):
        difficulty = int(row.get("difficulty", 1))
        answer_rarity = 1.0 / answer_counts[answers[i]]
        question_rarity = 1.0 / question_counts[questions[i]]
        scores.append((difficulty, answer_rarity, question_rarity))

    return scores


class UncertaintySelector(SelectionStrategy):
    """Select examples that are likely hardest for the current baseline.

    See module docstring for full proxy rationale.  The seed controls
    random tie-breaking so that results are deterministic.
    """

    name = "uncertainty"

    def select(
        self,
        pool: list[dict[str, Any]],
        budget: int,
        seed: int,
    ) -> list[int]:
        self._validate(len(pool), budget)

        rng = _random.Random(seed)
        indices = list(range(len(pool)))
        rng.shuffle(indices)  # random ordering for deterministic tie-breaking

        scores = _uncertainty_scores(pool)

        # Stable sort (descending) preserves the shuffled order for ties.
        ranked = sorted(indices, key=lambda i: scores[i], reverse=True)
        return sorted(ranked[:budget])
