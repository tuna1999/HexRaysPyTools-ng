"""Test SwapThenElse action.

The ``check``/``activate`` paths walk a real Hex-Rays ctree, so they cannot
be unit-tested with mocks (they need a live decompiler view). These tests
cover the constructible surface: metadata and the None-input guard.
"""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.swap_if_action import SwapThenElse


def test_swap_then_else_init() -> None:
    a = SwapThenElse()
    assert a.hotkey == "Shift+Alt+S"
    assert a.menu_path == "HexRaysPyTools/"


def test_swap_then_else_check_none_returns_false() -> None:
    """check() returns False when there is no decompiler view."""
    assert SwapThenElse().check(None) is False


def test_swap_then_else_activate_with_mock_view_is_noop() -> None:
    """activate() does not raise when the view cannot be resolved."""
    ctx = MagicMock()
    import idaapi
    idaapi.get_widget_vdui.return_value = MagicMock()
    SwapThenElse().activate(ctx)  # must not raise
