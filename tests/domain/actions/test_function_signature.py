"""Test function_signature actions (ConvertToUsercall, AddRemoveReturn, RemoveArgument).

The ``check``/``activate`` paths operate on a live Hex-Rays cfunc/func_type
and cannot be exercised with mocks. These tests cover the constructible
surface: metadata, the None-input guard, and that activate does not raise
when the view cannot be resolved.
"""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.action import HexRaysPopupAction
from hexrays_pytools.domain.actions.function_signature import (
    AddRemoveReturn,
    ConvertToUsercall,
    RemoveArgument,
)


def test_convert_to_usercall_is_popup_action() -> None:
    assert issubclass(ConvertToUsercall, HexRaysPopupAction)
    assert ConvertToUsercall.description == "Convert to __usercall"
    assert ConvertToUsercall.menu_path == "HexRaysPyTools/Function/"


def test_add_remove_return_is_popup_action() -> None:
    assert issubclass(AddRemoveReturn, HexRaysPopupAction)
    assert AddRemoveReturn.description == "Add/Remove Return"
    assert AddRemoveReturn.menu_path == "HexRaysPyTools/Function/"


def test_remove_argument_is_popup_action() -> None:
    assert issubclass(RemoveArgument, HexRaysPopupAction)
    assert RemoveArgument.description == "Remove Argument"
    assert RemoveArgument.menu_path == "HexRaysPyTools/Function/"


def test_all_three_accept_session() -> None:
    session = MagicMock()
    for cls in (ConvertToUsercall, AddRemoveReturn, RemoveArgument):
        a = cls(session=session)
        assert a._session is session


def test_check_returns_false_for_none_view() -> None:
    """check() returns False when there is no decompiler view."""
    assert ConvertToUsercall().check(None) is False
    assert AddRemoveReturn().check(None) is False
    assert RemoveArgument().check(None) is False


def test_convert_to_usercall_check_requires_func_item() -> None:
    """ConvertToUsercall.check is True only when the cursor is on the function."""
    import idaapi

    hx = MagicMock()
    hx.item.citype = idaapi.VDI_FUNC
    assert ConvertToUsercall().check(hx) is True
    hx.item.citype = idaapi.VDI_EXPR
    assert ConvertToUsercall().check(hx) is False


def test_add_remove_return_check_requires_func_item() -> None:
    """AddRemoveReturn.check is True only when the cursor is on the function."""
    import idaapi

    hx = MagicMock()
    hx.item.citype = idaapi.VDI_FUNC
    assert AddRemoveReturn().check(hx) is True
    hx.item.citype = idaapi.VDI_EXPR
    assert AddRemoveReturn().check(hx) is False


def test_remove_argument_check_requires_arg_lvar() -> None:
    """RemoveArgument.check is True only for an argument local variable."""
    import idaapi

    hx = MagicMock()
    hx.item.citype = idaapi.VDI_LVAR
    lvar = MagicMock()
    lvar.is_arg_var = True
    hx.item.get_lvar.return_value = lvar
    assert RemoveArgument().check(hx) is True
    lvar.is_arg_var = False
    assert RemoveArgument().check(hx) is False
    hx.item.citype = idaapi.VDI_EXPR
    assert RemoveArgument().check(hx) is False


def test_activate_with_mock_view_is_noop() -> None:
    """activate() does not raise when the view cannot be resolved / no func type."""
    ctx = MagicMock()
    import idaapi
    # get_widget_vdui returns a mock view whose cfunc.get_func_type fails → early return
    vu = MagicMock()
    vu.cfunc.get_func_type.return_value = False
    idaapi.get_widget_vdui.return_value = vu
    ConvertToUsercall().activate(ctx)  # must not raise
    AddRemoveReturn().activate(ctx)
    RemoveArgument().activate(ctx)
