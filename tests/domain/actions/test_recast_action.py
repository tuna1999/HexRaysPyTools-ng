"""Test RecastItemLeft/Right actions.

The ``check``/``activate`` paths walk a real Hex-Rays ctree, so they cannot
be unit-tested with mocks (they need a live decompiler view). These tests
cover the constructible, mockable surface: metadata, the None-input guard,
and that the action imports its engine cleanly.
"""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.recast_action import RecastItemLeft, RecastItemRight


def test_recast_left_init() -> None:
    a = RecastItemLeft()
    assert a.hotkey == "Shift+L"
    assert a.menu_path == "HexRaysPyTools-ng/"


def test_recast_right_init() -> None:
    a = RecastItemRight()
    assert a.hotkey == "Shift+R"
    assert a.menu_path == "HexRaysPyTools-ng/"


def test_recast_left_check_none_returns_false() -> None:
    """check() returns False when there is no decompiler view."""
    assert RecastItemLeft().check(None) is False


def test_recast_right_check_none_returns_false() -> None:
    """check() returns False when there is no decompiler view."""
    assert RecastItemRight().check(None) is False


def test_recast_left_activate_with_none_view_is_noop() -> None:
    """activate() does not raise when the view cannot be resolved."""
    # ctx.widget resolves to a MagicMock; get_widget_vdui returns a MagicMock
    # view whose ctree-walk yields None -> apply not called. No exception.
    ctx = MagicMock()
    import idaapi
    idaapi.get_widget_vdui.return_value = MagicMock()
    RecastItemLeft().activate(ctx)  # must not raise


def test_recast_right_activate_with_none_view_is_noop() -> None:
    ctx = MagicMock()
    import idaapi
    idaapi.get_widget_vdui.return_value = MagicMock()
    RecastItemRight().activate(ctx)  # must not raise
