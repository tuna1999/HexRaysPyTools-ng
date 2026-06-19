"""Test plugin.py entry point with ActionRegistry + HxCallbackManager wired in."""
from hexrays_pytools.__main__ import PLUGIN_ENTRY
from hexrays_pytools.plugin import HexRaysPyToolsPlugin


def test_plugin_entry_is_class() -> None:
    """PLUGIN_ENTRY is the HexRaysPyToolsPlugin class."""
    assert PLUGIN_ENTRY is HexRaysPyToolsPlugin


def test_plugin_class_has_required_attributes() -> None:
    """Plugin has flags, comment, help, wanted_name, wanted_hotkey."""
    assert hasattr(HexRaysPyToolsPlugin, "flags")
    assert hasattr(HexRaysPyToolsPlugin, "wanted_name")
    assert HexRaysPyToolsPlugin.wanted_name == "HexRaysPyTools"
    assert HexRaysPyToolsPlugin.wanted_hotkey == ""


def test_plugin_run_no_op() -> None:
    """run() takes args and does nothing."""
    HexRaysPyToolsPlugin.run()
    HexRaysPyToolsPlugin.run(1, 2, 3)


def test_plugin_term_without_state() -> None:
    """term() handles missing session/actions/hx_callbacks gracefully."""
    HexRaysPyToolsPlugin.session = None
    HexRaysPyToolsPlugin.actions = None
    HexRaysPyToolsPlugin.hx_callbacks = None
    HexRaysPyToolsPlugin.term()


def test_plugin_class_has_action_registry_attribute() -> None:
    """Plugin class has actions and hx_callbacks attributes (set in init)."""
    assert hasattr(HexRaysPyToolsPlugin, "actions")
    assert hasattr(HexRaysPyToolsPlugin, "hx_callbacks")
    assert hasattr(HexRaysPyToolsPlugin, "session")


def test_plugin_init_wires_registry_and_callbacks() -> None:
    """init() creates session, actions, and hx_callbacks with all 4 event handlers."""
    HexRaysPyToolsPlugin.session = None
    HexRaysPyToolsPlugin.actions = None
    HexRaysPyToolsPlugin.hx_callbacks = None
    result = HexRaysPyToolsPlugin.init()
    assert result == int(__import__("idaapi").PLUGIN_KEEP)
    assert HexRaysPyToolsPlugin.session is not None
    assert HexRaysPyToolsPlugin.actions is not None
    # hx_callbacks should have 4 handlers registered (1 for hxe_double_click, 3 for hxe_maturity)
    assert HexRaysPyToolsPlugin.hx_callbacks is not None
    hx = HexRaysPyToolsPlugin.hx_callbacks
    idaapi = __import__("idaapi")
    assert len(hx._handlers[idaapi.hxe_double_click]) == 1
    assert len(hx._handlers[idaapi.hxe_maturity]) == 3
    # Terminate to clean up
    HexRaysPyToolsPlugin.term()
    assert HexRaysPyToolsPlugin.session is None
    assert HexRaysPyToolsPlugin.actions is None
    assert HexRaysPyToolsPlugin.hx_callbacks is None
