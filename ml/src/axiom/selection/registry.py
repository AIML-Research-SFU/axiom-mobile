"""Strategy registry — maps string names to selector instances."""

from __future__ import annotations

from .base import SelectionStrategy
from .diversity import DiversitySelector
from .kg_guided import KGGuidedSelector
from .random import RandomSelector
from .uncertainty import UncertaintySelector

_REGISTRY: dict[str, type[SelectionStrategy]] = {
    "random": RandomSelector,
    "uncertainty": UncertaintySelector,
    "diversity": DiversitySelector,
    "kg_guided": KGGuidedSelector,
}

ALL_STRATEGY_NAMES: list[str] = sorted(_REGISTRY)


def get_strategy(name: str) -> SelectionStrategy:
    """Instantiate a selection strategy by name.

    Raises ``KeyError`` if the name is not registered.
    """
    cls = _REGISTRY.get(name)
    if cls is None:
        raise KeyError(
            f"Unknown strategy '{name}'. Available: {ALL_STRATEGY_NAMES}"
        )
    return cls()


def list_strategies() -> list[str]:
    """Return all registered strategy names."""
    return list(ALL_STRATEGY_NAMES)
