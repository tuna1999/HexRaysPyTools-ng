"""Per-IDB Session context.

Replaces all module-level global mutable state from the original plugin
(`cache.py`, `variable_scanner.py`, `classes.py`, `temporary_structure.py`).

Lifecycle: `MyPlugin.init()` calls `session.open()`;
`MyPlugin.term()` calls `session.close()`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .const import Consts
    from .recon.workspace import ReconWorkspace
    from .templated.templated_types import TemplatedTypes
    from .xrefs.xref_storage import XrefStorage

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Per-IDB state container. Created once per IDA database open."""

    is_open: bool = False
    idb_path: str = ""

    # Domain workspaces (lazy-init in open())
    recon: ReconWorkspace | None = None
    xrefs: XrefStorage | None = None
    templated: TemplatedTypes | None = None

    # IDA caches (replaces cache.py globals)
    imported_ea: set[int] = field(default_factory=set)
    demangled_names: dict[str, set[int]] = field(default_factory=dict)
    touched_functions: set[int] = field(default_factory=set)

    # tinfo singletons for the active IDB (replaces core/const.py module globals)
    consts: Consts | None = None

    # Settings (loaded from HCLI ida-settings in open())
    log_level: int = logging.INFO
    propagate_through_all_names: bool = False
    store_xrefs: bool = True
    scan_any_type: bool = False
    templated_types_file: str = ""

    def open(self) -> None:
        """Open the session. Idempotent."""
        if self.is_open:
            return
        self._load_settings()
        self._init_caches()
        self._init_workspaces()
        self.is_open = True
        logger.info("Session opened for %s", self.idb_path or "<no IDB>")

    def close(self) -> None:
        """Close the session, persisting state. Idempotent."""
        if not self.is_open:
            return
        if self.xrefs and self.store_xrefs:
            self.xrefs.flush()
        self.is_open = False
        logger.info("Session closed")

    def _load_settings(self) -> None:
        """Load settings from HCLI ida-settings into session fields."""
        # settings.py is created in Task 1.4; fall back to defaults here
        try:
            from .settings import load_into

            load_into(self)
        except ImportError:
            logger.debug("settings.py not yet available, using defaults")

    def _init_caches(self) -> None:
        """Initialize IDA-derived caches (imported EAs, demangled names, consts)."""
        # Build the tinfo singletons for this IDB. The scanner engine
        # (Phase A.5+) depends on these; importing here is the natural
        # place to wire the dependency.
        from .const import init_consts

        self.consts = init_consts()
        logger.debug("Caches initialized (consts populated)")

    def _init_workspaces(self) -> None:
        """Lazy-init domain workspaces."""
        # Real init happens in Phase 2 (recon, xrefs, templated modules)
        # For now, just mark the slots.
        self.recon = None
        self.xrefs = None
        self.templated = None
