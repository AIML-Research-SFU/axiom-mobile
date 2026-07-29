"""KG-guided selection strategy — unblocked in Phase 9.

Was blocked since Phase 1 on KG v1 not existing (see ``docs/TIMELINE.md``).
KG v1 now exists (``kg/entities.json``, ``kg/relations.json``, built by
``ml/scripts/build_kg.py``), extracted programmatically from the dataset's
own ``notes``/``question``/``answer`` fields — no separate curation effort.

Algorithm
---------
Per the original proposal ("KG-guided: cover underrepresented KG regions"),
this selects examples to maximize breadth across (Screen, Attribute) pairs
— the same region definition used to build the committed KG (see
``axiom.kg.region_of``) — before depth within any single region. This is
a genuinely different signal from the other three strategies:

- RAND ignores structure entirely.
- UNC scores by difficulty/answer-rarity/question-rarity — properties of
  individual examples.
- DIV maximizes pairwise text (Jaccard) distance between question/answer/
  notes strings — a generic similarity signal, not grounded in any
  explicit entity structure.
- KG-guided uses the explicit (App, Screen) x Attribute structure the KG
  encodes: round-robin across regions in a seeded-shuffled order, taking
  one item from each region per pass, so a fixed budget is spent covering
  as many distinct (screen, attribute) combinations as possible rather
  than concentrating on whichever regions happen to dominate the pool.

Deterministic for a given (pool, budget, seed): region order and
within-region item order are both seeded-shuffled.
"""

from __future__ import annotations

import random as _random
from collections import defaultdict
from typing import Any

from axiom.kg import region_of

from .base import SelectionStrategy


class KGGuidedSelector(SelectionStrategy):
    """Round-robin selection across KG (Screen, Attribute) regions,
    prioritizing coverage breadth over depth within any one region."""

    name = "kg_guided"

    def select(
        self,
        pool: list[dict[str, Any]],
        budget: int,
        seed: int,
    ) -> list[int]:
        self._validate(len(pool), budget)

        rng = _random.Random(seed)

        region_groups: dict[tuple[str, str], list[int]] = defaultdict(list)
        for i, row in enumerate(pool):
            region_groups[region_of(row)].append(i)

        # Shuffle within each region so which item is picked first (when
        # a region isn't fully consumed) is still seed-deterministic, not
        # dataset-order-dependent.
        for indices in region_groups.values():
            rng.shuffle(indices)

        # Shuffle region visiting order per seed too, so no single region
        # (e.g. whichever happens to be alphabetically first) is
        # systematically favored across seeds.
        region_order = list(region_groups.keys())
        rng.shuffle(region_order)

        selected: list[int] = []
        pointers = {region: 0 for region in region_order}

        while len(selected) < budget:
            progressed = False
            for region in region_order:
                if len(selected) >= budget:
                    break
                indices = region_groups[region]
                p = pointers[region]
                if p < len(indices):
                    selected.append(indices[p])
                    pointers[region] = p + 1
                    progressed = True
            if not progressed:
                # All regions exhausted before reaching budget -- shouldn't
                # happen since _validate() already checked budget <= pool
                # size, but guard against an infinite loop regardless.
                break

        return sorted(selected)
