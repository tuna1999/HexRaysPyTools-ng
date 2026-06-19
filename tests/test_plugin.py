"""Test plugin.py entry point with ActionRegistry + HxCallbackManager wired in.

These tests also guard the IDA 9.x plugin contract: ``init``/``run``/``term``
must be instance methods (not classmethods) and ``PLUGIN_ENTRY`` must be a
function returning a fresh instance. A classmethod override of the SWIG
virtual ``init`` caused a native crash at plugin discovery time — see the
``plugin.py`` module docstring for the contract details.
"""
import inspect

import idaapi

from hexrays_pytools.__main__ import PLUGIN_ENTRY
from hexrays_pytools.plugin import HexRaysPyToolsPlugin


def test_plugin_entry_is_callable_returning_instance() -> None:
    """PLUGIN_ENTRY is a function that returns a fresh plugin instance."""
    assert callable(PLUGIN_ENTRY)
    instance = PLUGIN_ENTRY()
    assert isinstance(instance, HexRaysPyToolsPlugin)
    # Each call returns a NEW instance (no shared mutable state across calls).
    other = PLUGIN_ENTRY()
    assert other is not instance


def test_plugin_class_has_required_attributes() -> None:
    """Plugin has flags, comment, help, wanted_name, wanted_hotkey."""
    assert HexRaysPyToolsPlugin.flags == 0
    assert HexRaysPyToolsPlugin.wanted_name == "HexRaysPyTools"
    assert HexRaysPyToolsPlugin.wanted_hotkey == ""


def test_init_run_term_are_instance_methods() -> None:
    """init/run/term MUST be instance methods (IDA 9.x SWIG contract).

    Regression guard for the native-crash bug: classmethod overrides of the
    virtual plugin_t methods caused a descriptor mismatch in IDA's C++
    dispatcher at discovery time.
    """
    for name in ("init", "run", "term"):
        method = getattr(HexRaysPyToolsPlugin, name)
        # Instance methods are NOT classmethods and NOT staticmethods.
        assert not isinstance(method, classmethod), f"{name} must not be a classmethod"
        assert not isinstance(
            method, staticmethod
        ), f"{name} must not be a staticmethod"
        sig = inspect.signature(method)
        assert "self" in sig.parameters, f"{name} must take self"


def test_plugin_run_no_op() -> None:
    """run() takes an arg and does nothing."""
    plugin = HexRaysPyToolsPlugin()
    plugin.run(0)


def test_plugin_term_without_state() -> None:
    """term() handles missing session/actions/hx_callbacks gracefully."""
    plugin = HexRaysPyToolsPlugin()
    plugin.term()  # freshly-constructed instance has all state as None


def test_plugin_instance_state_is_none_until_init() -> None:
    """A fresh instance has session/actions/hx_callbacks all None."""
    plugin = HexRaysPyToolsPlugin()
    assert plugin.session is None
    assert plugin.actions is None
    assert plugin.hx_callbacks is None


def test_plugin_init_wires_registry_and_callbacks() -> None:
    """init() creates session, actions, and hx_callbacks with all 4 event handlers."""
    plugin = HexRaysPyToolsPlugin()
    result = plugin.init()
    assert result == int(idaapi.PLUGIN_KEEP)
    assert plugin.session is not None
    assert plugin.actions is not None
    # 1 handler for hxe_double_click, 3 for hxe_maturity.
    assert plugin.hx_callbacks is not None
    assert len(plugin.hx_callbacks._handlers[idaapi.hxe_double_click]) == 1
    assert len(plugin.hx_callbacks._handlers[idaapi.hxe_maturity]) == 3
    # Terminate to clean up.
    plugin.term()
    assert plugin.session is None
    assert plugin.actions is None
    assert plugin.hx_callbacks is None


def test_plugin_entry_resolves_class_in_synthetic_namespace() -> None:
    """PLUGIN_ENTRY works even when IDA re-binds it into a synthetic namespace.

    Regression guard for the IDA 9.x discovery crash: IDA's plugin loader
    execs the entry file in a ``__plugins__<name>`` namespace and re-binds
    ``PLUGIN_ENTRY`` into it, so ``HexRaysPyToolsPlugin`` is NOT in the
    function's call-time globals. PLUGIN_ENTRY must resolve the class by
    import at call time rather than relying on module globals.
    """
    import types

    from hexrays_pytools.plugin import PLUGIN_ENTRY

    # Simulate IDA's re-binding: create a copy of PLUGIN_ENTRY whose
    # __globals__ is an empty synthetic namespace (no HexRaysPyToolsPlugin).
    synthetic = types.FunctionType(
        PLUGIN_ENTRY.__code__,
        {"__name__": "__plugins__hexrays_pytools"},
        PLUGIN_ENTRY.__name__,
    )
    # Must NOT raise NameError — and must return a real plugin instance.
    instance = synthetic()
    assert isinstance(instance, HexRaysPyToolsPlugin)
