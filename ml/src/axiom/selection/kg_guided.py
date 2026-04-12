"""KG-guided selection strategy — currently blocked.

This strategy requires a Knowledge Graph (KG v1) with entity and
relation coverage metadata that does not yet exist in the repository.
See ``docs/TIMELINE.md`` Phase 1 item:

    ``[ ] KG v1 (~1000 entities + API + app loader) not implemented yet.``

Until the KG module is available, this selector raises
``NotImplementedError`` with a clear message.  The sweep runner
records this as a "skipped" strategy rather than crashing the run.
"""

from __future__ import annotations

from typing import Any

from .base import SelectionStrategy


class KGGuidedSelector(SelectionStrategy):
    """Placeholder for KG-guided selection.

    Raises ``NotImplementedError`` on every call.  The sweep runner
    is designed to catch this and record a skipped status.
    """

    name = "kg_guided"

    def select(
        self,
        pool: list[dict[str, Any]],
        budget: int,
        seed: int,
    ) -> list[int]:
        raise NotImplementedError(
            "KG-guided selection requires KG v1 (~1000 entities + query API) "
            "which is not yet implemented.  See docs/TIMELINE.md Phase 1."
        )
