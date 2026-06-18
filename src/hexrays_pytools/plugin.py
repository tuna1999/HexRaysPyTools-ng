"""IDA plugin entry point.

Defines `HexRaysPyToolsPlugin` (idaapi.plugin_t subclass) that manages the
plugin lifecycle: init/run/term. All state lives in class attributes (per
plugin instance, not module global).
"""
from __future__ import annotations

import logging

import idaapi  # type: ignore[import-not-found]

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

    @classmethod
    def init(cls) -> int:
        """Initialize plugin: open session, return PLUGIN_KEEP."""
        if not idaapi.init_hexrays_plugin():
            logger.error("Failed to initialize Hex-Rays SDK")
            return int(idaapi.PLUGIN_SKIP)

        cls.session = Session()
        cls.session.open()
        # ActionRegistry and HxCallbackRegistry will be wired in Phase 4
        logger.info("HexRaysPyTools plugin initialized")
        return int(idaapi.PLUGIN_KEEP)

    @classmethod
    def run(cls, *args: object) -> None:
        """Run the plugin (no-op — actions handle their own execution)."""

    @classmethod
    def term(cls) -> None:
        """Terminate plugin: close session."""
        if cls.session:
            cls.session.close()
            cls.session = None
        idaapi.term_hexrays_plugin()
        logger.info("HexRaysPyTools plugin terminated")
