"""Test struct_xref action (FindFieldXrefs).

The activate path queries the XrefStorage and opens a chooser; it cannot be
exercised with mocks. These tests cover the constructible surface and the
check() guard.
"""
from unittest.mock import MagicMock

import idaapi

from hexrays_pytools.domain.actions.action import HexRaysXrefAction
from hexrays_pytools.domain.actions.struct_xref import FindFieldXrefs


def test_find_field_xrefs_is_xref_action() -> None:
    assert issubclass(FindFieldXrefs, HexRaysXrefAction)
    assert FindFieldXrefs.description == "Field Xrefs"
    assert FindFieldXrefs.hotkey == "Ctrl+X"
    assert FindFieldXrefs.menu_path == "HexRaysPyTools/Structure/"


def test_find_field_xrefs_accepts_session() -> None:
    session = MagicMock()
    a = FindFieldXrefs(session=session)
    assert a._session is session


def test_check_false_for_none() -> None:
    assert FindFieldXrefs().check(None) is False


def test_check_true_for_memptr() -> None:
    """check() is True when the cursor is on a struct pointer access (->)."""
    hx = MagicMock()
    hx.item.citype = idaapi.VDI_EXPR
    hx.item.it.to_specific_type.op = idaapi.cot_memptr
    assert FindFieldXrefs().check(hx) is True


def test_check_true_for_memref() -> None:
    """check() is True when the cursor is on a struct value access (.)."""
    hx = MagicMock()
    hx.item.citype = idaapi.VDI_EXPR
    hx.item.it.to_specific_type.op = idaapi.cot_memref
    assert FindFieldXrefs().check(hx) is True


def test_check_false_for_var() -> None:
    """check() is False for a plain variable."""
    hx = MagicMock()
    hx.item.citype = idaapi.VDI_EXPR
    hx.item.it.to_specific_type.op = idaapi.cot_var
    assert FindFieldXrefs().check(hx) is False
