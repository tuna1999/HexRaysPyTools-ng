"""Per-IDB Session context.

Replaces all module-level global mutable state from the original plugin
(`cache.py`, `variable_scanner.py`, `classes.py`, `temporary_structure.py`).

Lifecycle: `MyPlugin.init()` calls `session.open()`;
`MyPlugin.term()` calls `session.close()`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .actions.hx_callback import HxCallbackManager
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

    # HxCallbackManager reference (set by plugin.init() after construction).
    # Used by recent_callback_errors property (F4).
    hx_callbacks: HxCallbackManager | None = None

    # Widget factories — wired by plugin entry (plugin.py) after Session is
    # created. Domain actions call these factories instead of importing UI
    # widgets directly. This is the ONLY legal UI→session wiring point in
    # the 5-layer architecture (F1.b fix).
    class_viewer_factory: Callable[[], Any] | None = None
    structure_graph_viewer_factory: Callable[[Any], Any] | None = None
    structure_builder_factory: Callable[[Any], Any] | None = None

    # IDA caches (replaces cache.py globals)
    imported_ea: set[int] = field(default_factory=set)
    demangled_names: dict[str, set[int]] = field(default_factory=dict)
    touched_functions: set[int] = field(default_factory=set)
    # CONTAINING_RECORD candidates per cfunc (entry_ea -> lvar idx -> candidate).
    # Populated by the CMAT_BUILT collector, consumed by the Select action.
    potential_negatives: dict[int, dict[int, Any]] = field(default_factory=dict)


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
        # Drop ctree-coupled state — tinfo/cfunc objects from this IDB must
        # not survive into a session for another database.
        self.potential_negatives.clear()
        self.is_open = False
        logger.info("Session closed")

    @property
    def recent_callback_errors(self) -> list[tuple[int, Exception]]:
        """Last 10 errors from HxCallbackManager (read-only snapshot).

        F4: surfaces silent handler failures. UI code can poll this to render
        status bar warning / log action. Returns empty list if hx_callbacks
        not yet wired (e.g. before plugin.init() completes).
        """
        if self.hx_callbacks is None:
            return []
        return list(self.hx_callbacks.errors[-10:])

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
        import idaapi  # type: ignore[import-not-found]
        import idautils  # type: ignore[import-not-found]
        import idc  # type: ignore[import-not-found]

        from ..pure.name_mangle import sanitize_c_name
        from .const import init_consts

        # Build the tinfo singletons for this IDB. The scanner engine
        # (Phase A.5+) depends on these; importing here is the natural
        # place to wire the dependency.
        self.imported_ea.clear()
        self.demangled_names.clear()
        self.touched_functions.clear()

        def _import_cb(ea: int, name: str | None, ordinal: int) -> bool:  # noqa: ARG001
            self.imported_ea.add(int(ea))
            return True

        try:
            module_count = int(idaapi.get_import_module_qty())
            for index in range(max(module_count, 0)):
                idaapi.enum_import_names(index, _import_cb)
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            logger.debug("Failed to enumerate imports: %s", exc)

        try:
            for address, raw_name in idautils.Names():
                demangled = idc.demangle_name(str(raw_name), idc.INF_SHORT_DN)
                if not demangled:
                    continue
                key = sanitize_c_name(str(demangled))
                if key:
                    self.demangled_names.setdefault(key, set()).add(int(address))
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            logger.debug("Failed to build demangled-name cache: %s", exc)

        self.consts = init_consts()
        logger.debug(
            "Caches initialized (imports=%d, demangled=%d)",
            len(self.imported_ea),
            len(self.demangled_names),
        )

    def _init_workspaces(self) -> None:
        """Initialize domain workspaces.

        Mirrors the original plugin's init() flow:
        ``cache.temporary_structure = TemporaryStructureModel()`` and
        ``XrefStorage().open()`` — these were the two pieces of state
        every scanner / event handler relied on. In the new design:
        - ``ReconWorkspace`` lazily constructs its :class:`StructureModel`
          on first ``.model`` access so scanner actions can write to it
          without first opening the Structure Builder widget.
        - ``XrefStorage`` is netnode-backed; ``open()`` loads any
          existing data + auto-migrates the legacy array format.
        """
        from .recon.workspace import ReconWorkspace
        from .templated.templated_types import TemplatedTypes
        from .xrefs.xref_storage import XrefStorage

        self.templated = TemplatedTypes(self.templated_types_file)
        self.recon = ReconWorkspace(self.templated)
        self.xrefs = XrefStorage()
        if self.store_xrefs:
            # Only load persisted xrefs when persistence is enabled —
            # otherwise start from a clean in-memory store for this session.
            self.xrefs.open()
        logger.debug("Workspaces initialized (recon + xrefs + templated types)")
