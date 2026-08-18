"""Test struct_xref action (FindFieldXrefs)."""
from unittest.mock import MagicMock, patch

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


def test_activate_local_types_uses_ida9_type_ref() -> None:
    """BWN_TILIST reads the selected UDT member from ctx.type_ref on IDA 9."""
    storage = MagicMock()
    storage.get_structure_info.return_value = []
    session = MagicMock()
    session.xrefs = storage

    ctx = MagicMock()
    ctx.widget_type = idaapi.BWN_LOCTYPS
    ctx.type_ref.on_member.return_value = True
    ctx.type_ref.is_udt.return_value = True
    ctx.type_ref.ordinal = 23
    ctx.type_ref.udm.offset = 0x18 * 8
    ctx.type_ref.udm.name = "field_18"
    ctx.type_ref.tif.dstr.return_value = "MyStruct"

    with patch("hexrays_pytools.domain.actions.struct_xref.MyChoose") as chooser:
        chooser.return_value.Show.return_value = -1
        FindFieldXrefs(session=session).activate(ctx)

    storage.get_structure_info.assert_called_once_with(ordinal=23, field_offset=0x18)


def test_activate_local_types_requires_member() -> None:
    session = MagicMock()
    ctx = MagicMock()
    ctx.widget_type = idaapi.BWN_LOCTYPS
    ctx.type_ref.on_member.return_value = False

    FindFieldXrefs(session=session).activate(ctx)
    session.xrefs.get_structure_info.assert_not_called()
