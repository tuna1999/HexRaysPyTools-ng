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
  * ``PLUGIN_ENTRY`` is a **function** returning a plugin instance.
  * ``PLUGIN_ENTRY`` must resolve ``HexRaysPyToolsPlugin`` by **import at call
    time**, not via module globals: IDA's plugin loader execs the entry file
    in a synthetic ``__plugins__<name>`` namespace and re-binds ``PLUGIN_ENTRY``
    into it, so the class is absent from the function's call-time globals. A
    bare ``return HexRaysPyToolsPlugin()`` raised ``NameError`` at discovery.

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
from .domain.browser.proxy_model import ProxyModel
from .domain.browser.tree_model import TreeModel
from .domain.session import Session
from .ui.widgets.class_viewer import ClassViewer
from .ui.widgets.graph_viewer import StructureGraphViewer
from .ui.widgets.structure_builder import StructureBuilder

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

        # F1.b: wire widget factories into Session. This is the only legal
        # UI→domain wiring point in the 5-layer architecture. Domain actions
        # call these factories instead of importing widget classes directly.
        self.session.class_viewer_factory = lambda: ClassViewer(ProxyModel(), TreeModel())
        self.session.structure_graph_viewer_factory = lambda graph: StructureGraphViewer("Structure Graph", graph)
        self.session.structure_builder_factory = lambda workspace: StructureBuilder(workspace.model if workspace is not None else None)

        # Install the hx event dispatcher first — ActionRegistry needs it to
        # attach popup actions to hxe_populating_popup.
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

        # Register the 27 actions with IDA. Popup actions are auto-attached
        # to the right-click menu via the hx_callbacks dispatcher.
        self.actions = ActionRegistry(self.session, self.hx_callbacks)
        self.actions.register_all()

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
    """IDA entry point — returns a fresh plugin instance.

    Note: IDA's plugin loader execs the entry file in a synthetic
    ``__plugins__<name>`` namespace and re-binds this function into it, so
    ``__globals__`` at call time is that synthetic namespace — not the module
    where ``HexRaysPyToolsPlugin`` is defined. Resolve the class by import at
    call time instead of relying on module globals.
    """
    from hexrays_pytools.plugin import HexRaysPyToolsPlugin

    return HexRaysPyToolsPlugin()
