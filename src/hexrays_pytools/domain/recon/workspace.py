"""ReconWorkspace — container for the structure reconstruction model.

Replaces `cache.temporary_structure` global from the original plugin.
Phase 2 will expand this with the actual `StructureModel` (QAbstractTableModel);
for Phase 1 we just establish the skeleton so Session.recon can point to it.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ReconWorkspace:
    """Workspace for the structure reconstruction feature.

    Holds the temporary structure model being built (Phase 2 adds the Qt model).
    One instance per Session.
    """

    def __init__(self) -> None:
        self._model: object | None = None  # StructureModel added in Phase 2

    @property
    def model(self) -> object | None:
        """The current structure model (None until Phase 2 wires it)."""
        return self._model

    def clear(self) -> None:
        """Clear all workspace state."""
        self._model = None
        logger.debug("ReconWorkspace cleared")

    def is_empty(self) -> bool:
        """Return True if the workspace has no active model."""
        return self._model is None
