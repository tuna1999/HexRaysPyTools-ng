"""ReconWorkspace — container for the structure reconstruction model.

Replaces `cache.temporary_structure` global from the original plugin.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .structure_model import StructureModel

logger = logging.getLogger(__name__)


class ReconWorkspace:
    """Workspace for the structure reconstruction feature.

    Holds the temporary structure model being built.
    One instance per Session.
    """

    def __init__(self) -> None:
        self._model: StructureModel | None = None

    @property
    def model(self) -> StructureModel | None:
        """The current structure model (None until wired)."""
        return self._model

    def set_model(self, model: StructureModel) -> None:
        """Set the structure model."""
        self._model = model

    def clear(self) -> None:
        """Clear all workspace state."""
        self._model = None
        logger.debug("ReconWorkspace cleared")

    def is_empty(self) -> bool:
        """Return True if the workspace has no active model."""
        return self._model is None
