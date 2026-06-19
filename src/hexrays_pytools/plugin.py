"""IDA plugin entry point.

Defines `HexRaysPyToolsPlugin` (idaapi.plugin_t subclass) that manages the
plugin lifecycle: init/run/term.

IDA 9.x contract (confirmed against IDA 9.3 official examples
`auto_instantiate_widget_plugin.py` and `py_mex1.py`, and the working
`rikugan` plugin):

  * `init`/`run`/`term` are **instance methods** (take ``self``). IDA's C++
    dispatcher calls them through a SWIG virtual-method binding that expects
    an instance descriptor; overriding them with ``@classmethod`` produces a
    descriptor mismatch and a native crash at plugin discovery time.
  * `init` may return ``None``/``PLUGIN_SKIP`` for a non-MULTI plugin, or a
    ``plugmod_t`` instance for ``PLUGIN_MULTI``. We use the legacy non-MULTI
    form (``flags = 0``) which matches `auto_instantiate_widget_plugin.py`.
  * ``PLUGIN_ENTRY`` is a **function** returning a plugin instance.

All mutable state lives on the instance, not module globals.
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

    def __init__(self) -> None:
        # Per-instance state (not module-level globals, not class attributes).
        self.session: Session | None = None
        self.actions: ActionRegistry | None = None
        self.hx_callbacks: HxCallbackManager | None = None

    def init(self) -> int:
        """Initialize plugin: open session, register actions and hx callbacks.

        Returns PLUGIN_KEEP on success, PLUGIN_SKIP if Hex-Rays SDK is missing.
        """
        if not idaapi.init_hexrays_plugin():
            logger.error("Failed to initialize Hex-Rays SDK")
            return int(idaapi.PLUGIN_SKIP)

        self.session = Session()
        self.session.open()

        # Register the 27 actions with IDA
        self.actions = ActionRegistry(self.session)
        self.actions.register_all()

        # Install the 4 hx event handlers
        self.hx_callbacks = HxCallbackManager()
        self.hx_callbacks.install()
        self.hx_callbacks.register(
            int(idaapi.hxe_double_click),
            MemberDoubleClick(self.session),
        )
        self.hx_callbacks.register(
            int(idaapi.hxe_maturity),
            PotentialNegativeCollector(self.session),
        )
        self.hx_callbacks.register(
            int(idaapi.hxe_maturity),
            StructXrefCollector(self.session),
        )
        self.hx_callbacks.register(
            int(idaapi.hxe_maturity),
            SilentIfSwapper(self.session),
        )

        logger.info("HexRaysPyTools plugin initialized")
        return int(idaapi.PLUGIN_KEEP)

    def run(self, arg: int) -> None:
        """Run the plugin (no-op — actions handle their own execution)."""

    def term(self) -> None:
        """Terminate plugin: unregister actions, close session."""
        if self.actions is not None:
            self.actions.unregister_all()
            self.actions = None
        if self.hx_callbacks is not None:
            self.hx_callbacks.detach_all()
            self.hx_callbacks = None
        if self.session is not None:
            self.session.close()
            self.session = None
        idaapi.term_hexrays_plugin()
        logger.info("HexRaysPyTools plugin terminated")


def PLUGIN_ENTRY() -> HexRaysPyToolsPlugin:  # noqa: N802 - IDA contract
    """IDA entry point — returns a fresh plugin instance."""
    return HexRaysPyToolsPlugin()
