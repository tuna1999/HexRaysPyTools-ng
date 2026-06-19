"""IDA plugin entry point.

Defines `HexRaysPyToolsPlugin` (idaapi.plugin_t subclass) that manages the
plugin lifecycle: init/run/term. All state lives in class attributes (per
plugin instance, not module global).
"""
from __future__ import annotations

import logging

import idaapi  # type: ignore[import-not-found]

from .domain.actions.hx_callback import HxCallbackManager
from .domain.actions.hx_events import (
    MemberDoubleClick,
    PotentialNegativeCollector,
    SilentIfSwapper,
    StructXrefCollector,
)
from .domain.actions.registry import ActionRegistry
from .domain.session import Session

logger = logging.getLogger(__name__)


class HexRaysPyToolsPlugin(idaapi.plugin_t):  # type: ignore[misc]
    """The HexRaysPyTools IDA plugin."""

    flags: int = 0
    comment: str = "Comprehensive toolkit for Hex-Rays decompiler"
    help: str = "See https://github.com/yourname/HexRaysPyTools"
    wanted_name: str = "HexRaysPyTools"
    wanted_hotkey: str = ""

    # Per-instance state (not module-level globals)
    session: Session | None = None
    actions: ActionRegistry | None = None
    hx_callbacks: HxCallbackManager | None = None

    @classmethod
    def init(cls) -> int:
        """Initialize plugin: open session, register actions and hx callbacks."""
        if not idaapi.init_hexrays_plugin():
            logger.error("Failed to initialize Hex-Rays SDK")
            return int(idaapi.PLUGIN_SKIP)

        cls.session = Session()
        cls.session.open()

        # Register the 27 actions with IDA
        cls.actions = ActionRegistry(cls.session)
        cls.actions.register_all()

        # Install the 4 hx event handlers
        cls.hx_callbacks = HxCallbackManager()
        cls.hx_callbacks.install()
        cls.hx_callbacks.register(
            int(idaapi.hxe_double_click),
            MemberDoubleClick(cls.session),
        )
        cls.hx_callbacks.register(
            int(idaapi.hxe_maturity),
            PotentialNegativeCollector(cls.session),
        )
        cls.hx_callbacks.register(
            int(idaapi.hxe_maturity),
            StructXrefCollector(cls.session),
        )
        cls.hx_callbacks.register(
            int(idaapi.hxe_maturity),
            SilentIfSwapper(cls.session),
        )

        logger.info("HexRaysPyTools plugin initialized")
        return int(idaapi.PLUGIN_KEEP)

    @classmethod
    def run(cls, *args: object) -> None:
        """Run the plugin (no-op — actions handle their own execution)."""

    @classmethod
    def term(cls) -> None:
        """Terminate plugin: unregister actions, close session."""
        if cls.actions:
            cls.actions.unregister_all()
            cls.actions = None
        if cls.hx_callbacks:
            cls.hx_callbacks.detach_all()
            cls.hx_callbacks = None
        if cls.session:
            cls.session.close()
            cls.session = None
        idaapi.term_hexrays_plugin()
        logger.info("HexRaysPyTools plugin terminated")
