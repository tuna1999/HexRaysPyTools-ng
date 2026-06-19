"""Test structs_by_size action (GetStructureBySize).

The activate path operates on a live cfunc number-format and cannot be
exercised with mocks. These tests cover the constructible surface and the
check() guard logic.
"""
from unittest.mock import MagicMock

import idaapi

from hexrays_pytools.domain.actions.action import HexRaysPopupAction
from hexrays_pytools.domain.actions.structs_by_size import GetStructureBySize


def test_get_structure_by_size_is_popup_action() -> None:
    assert issubclass(GetStructureBySize, HexRaysPopupAction)
    assert GetStructureBySize.description == "Structures with this size"
    assert GetStructureBySize.menu_path == "HexRaysPyTools/Structure/"


def test_get_structure_by_size_accepts_session() -> None:
    session = MagicMock()
    a = GetStructureBySize(session=session)
    assert a._session is session


def test_check_returns_false_for_none_view() -> None:
    """check() returns False when there is no decompiler view."""
    assert GetStructureBySize().check(None) is False


def test_check_true_for_number_expression() -> None:
    """check() is True when the cursor is on a number literal."""
    hx = MagicMock()
    hx.item.citype = idaapi.VDI_EXPR
    hx.item.e.op = idaapi.cot_num
    assert GetStructureBySize().check(hx) is True


def test_check_false_for_non_number_expression() -> None:
    """check() is False for non-number expressions."""
    hx = MagicMock()
    hx.item.citype = idaapi.VDI_EXPR
    hx.item.e.op = idaapi.cot_var  # not a number
    assert GetStructureBySize().check(hx) is False


def test_check_false_for_non_expr_item() -> None:
    """check() is False when the cursor is not on an expression."""
    hx = MagicMock()
    hx.item.citype = idaapi.VDI_LVAR
    assert GetStructureBySize().check(hx) is False


def test_activate_with_mock_view_is_noop() -> None:
    """activate() does not raise when the view cannot be resolved."""
    ctx = MagicMock()
    vu = MagicMock()
    vu.item.citype = idaapi.VDI_LVAR  # fails the check() guard → early return
    idaapi.get_widget_vdui.return_value = vu
    GetStructureBySize().activate(ctx)  # must not raise
