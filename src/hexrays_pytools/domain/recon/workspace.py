"""ReconWorkspace — container for the structure reconstruction model.

Replaces `cache.temporary_structure` global from the original plugin.

The workspace owns:
- ``model`` — the Qt :class:`StructureModel` (None until the Structure Builder
  opens a session)
- ``main_offset`` — the struct offset the user is currently reconstructing;
  every scanner reads it as the ``origin`` argument to ``SearchVisitor``
- the ``StructureBuilder`` widget (when opened)
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .structure_model import StructureModel

logger = logging.getLogger(__name__)


class ReconWorkspace:
    """Workspace for the structure reconstruction feature.

    Holds the temporary structure model being built + the currently
    selected "main" struct offset.
    One instance per Session.
    """

    def __init__(self) -> None:
        self._model: StructureModel | None = None
        # The primary struct offset the user is reconstructing. Scanners
        # read this as the `origin` argument to SearchVisitor. Default 0
        # (no offset selected) — the StructureBuilder sets this on row click.
        self.main_offset: int = 0

    @property
    def model(self) -> StructureModel | None:
        """The current structure model (None until wired)."""
        return self._model

    def set_model(self, model: StructureModel) -> None:
        """Set the structure model."""
        self._model = model

    def clear(self) -> None:
        """Clear all workspace state (model + main_offset)."""
        self._model = None
        self.main_offset = 0
        logger.debug("ReconWorkspace cleared")

    def is_empty(self) -> bool:
        """Return True if the workspace has no active model."""
        return self._model is None
