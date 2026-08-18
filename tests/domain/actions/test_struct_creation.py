"""Test struct_creation actions (CreateNewField, CreateVtable).

The activate paths operate on a live cfunc/UDT and cannot be exercised with
mocks. These tests cover the constructible surface and the check() guards.
"""
from unittest.mock import MagicMock, patch

import idaapi

from hexrays_pytools.domain.actions.action import Action, HexRaysPopupAction
from hexrays_pytools.domain.actions.struct_creation import CreateNewField, CreateVtable


def test_create_new_field_is_popup_action() -> None:
    assert issubclass(CreateNewField, HexRaysPopupAction)
    assert CreateNewField.description == "Create New Field"
    assert CreateNewField.hotkey == "Ctrl+F"
    assert CreateNewField.menu_path == "HexRaysPyTools/Structure/"


def test_create_vtable_is_action() -> None:
    assert issubclass(CreateVtable, Action)
    assert CreateVtable.description == "Create Virtual Table"
    assert CreateVtable.hotkey == "V"


def test_both_accept_session() -> None:
    session = MagicMock()
    for cls in (CreateNewField, CreateVtable):
        a = cls(session=session)
        assert a._session is session


def test_create_new_field_check_false_for_none() -> None:
    assert CreateNewField().check(None) is False


def test_create_new_field_check_false_for_non_expr() -> None:
    hx = MagicMock()
    hx.item.citype = idaapi.VDI_LVAR
    assert CreateNewField().check(hx) is False


def test_create_vtable_check_true_for_valid_ea() -> None:
    """CreateVtable.check is True when ea != BADADDR and DiscoveredVTable.check_address passes."""
    idaapi = __import__("idaapi")
    idaapi.BADADDR = 0xFFFFFFFFFFFFFFFF
    with patch(
        "hexrays_pytools.domain.actions.struct_creation.DiscoveredVTable.check_address",
        return_value=True,
    ):
        assert CreateVtable.check(0x401000) is True


def test_create_vtable_check_false_for_badaddr() -> None:
    idaapi = __import__("idaapi")
    idaapi.BADADDR = 0xFFFFFFFFFFFFFFFF
    assert CreateVtable.check(idaapi.BADADDR) is False


def test_create_new_field_activate_with_mock_view_is_noop() -> None:
    """activate() does not raise when the view's check() guard fails."""
    ctx = MagicMock()
    vu = MagicMock()
    vu.item.citype = idaapi.VDI_LVAR  # fails the check() guard → early return
    idaapi.get_widget_vdui.return_value = vu
    CreateNewField().activate(ctx)  # must not raise


def test_create_vtable_activate_skips_when_check_fails() -> None:
    """activate() is a no-op when the ea check fails."""
    idaapi = __import__("idaapi")
    idaapi.BADADDR = 0xFFFFFFFFFFFFFFFF
    ctx = MagicMock()
    ctx.cur_ea = idaapi.BADADDR  # check fails → early return
    CreateVtable().activate(ctx)  # must not raise
