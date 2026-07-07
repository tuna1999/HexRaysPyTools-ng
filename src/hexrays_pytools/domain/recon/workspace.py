"""ReconWorkspace — container for the structure reconstruction model.

Replaces `cache.temporary_structure` global from the original plugin.

The workspace owns:
- ``model`` — the Qt :class:`StructureModel`. Built **lazily** on first
  access via the ``model`` property; ``__init__`` does not touch Qt.
  Scanner actions and the Structure Builder both receive a non-None
  model by the time they use it. The Structure Builder binds to the
  same model.
- ``main_offset`` — the struct offset the user is currently reconstructing;
  every scanner reads it as the ``origin`` argument to ``SearchVisitor``.
- the ``StructureBuilder`` widget (when opened).

Lifecycle: ``Session.open`` creates a :class:`ReconWorkspace` and assigns it
to ``Session.recon``. The Structure Builder widget, when opened, calls
``set_model()`` to replace the model (rare — kept for API symmetry).
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
        # F6: true lazy init — StructureModel (Qt-dependent) is constructed
        # on first .model access, not at workspace init. This keeps
        # Session.open() PySide6-free so unit tests can construct a
        # ReconWorkspace without Qt available. Mirrors the original plugin's
        # behavior where the model was always present at session start —
        # scanner actions that check `workspace.model is None` still see a
        # model after first access (and the property always returns one).
        self._model: StructureModel | None = None
        # The primary struct offset the user is reconstructing. Scanners
        # read this as the `origin`` argument to SearchVisitor. Default 0
        # (no offset selected) — the StructureBuilder sets this on row click.
        self.main_offset: int = 0

    @property
    def model(self) -> StructureModel:
        """The current structure model.

        F6: lazy construction — first access builds an empty StructureModel,
        subsequent accesses return the cached instance. Returns a fresh
        StructureModel if `_model` was forcibly deleted (defensive). Always
        returns a non-None StructureModel in normal use.
        """
        if self._model is None:
            self._model = _create_empty_model()
        return self._model

    def set_model(self, model: StructureModel) -> None:
        """Replace the structure model (rare — the widget binds in ``__init__``)."""
        self._model = model

    def clear(self) -> None:
        """Empty the model + reset main_offset.

        Note: the model **stays alive** — only its items are cleared. This
        keeps subsequent scanner actions working without a re-init step.
        The original plugin cleared items the same way (the global model
        never went away).
        """
        if self._model is not None:
            self._model.clear()
        self.main_offset = 0
        logger.debug("ReconWorkspace cleared (items + main_offset reset)")

    def is_empty(self) -> bool:
        """Return True if the model has no items (or no model at all).

        ``empty`` is checked against items, not model existence — the model
        is always present after first ``.model`` access.
        """
        if self._model is None:
            return True
        return self._model.rowCount() == 0


def _create_empty_model() -> StructureModel:
    """Build an empty :class:`StructureModel` (true lazy via property accessor).

    ``workspace`` is imported by ``structure_model`` in the Qt model code
    paths; importing the model class at the top of this file would create
    a cycle. Local import keeps the module import graph clean AND keeps
    PySide6 dependency out of ReconWorkspace.__init__ (F6).
    """
    from .structure_model import StructureModel

    return StructureModel()
