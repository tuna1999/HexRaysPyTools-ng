"""Test plugin.py and __main__.py entry points."""
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
    HexRaysPyToolsPlugin.run()  # should not raise
    HexRaysPyToolsPlugin.run(1, 2, 3)  # should not raise


def test_plugin_term_without_session() -> None:
    """term() handles missing session gracefully."""
    HexRaysPyToolsPlugin.session = None
    HexRaysPyToolsPlugin.term()  # should not raise
    assert HexRaysPyToolsPlugin.session is None
