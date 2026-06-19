"""Test ScannedObject (with 'd') hierarchy.

ScannedObject is what the SearchVisitor **produces** when it finds a match —
it wraps the matching ScanObject with the expression address, the function EA,
an origin offset, and an apply_type() callback.

End-to-end behaviour is verified in real IDA via idat headless (see brief
A.5); these tests cover the Python-level state and the apply_type() bodies
that don't need a live ctree.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from hexrays_pytools.domain.scanner.scanned_object import (
    SO_GLOBAL_OBJECT,
    SO_LOCAL_VARIABLE,
    SO_STRUCT_POINTER,
    SO_STRUCT_REFERENCE,
    ScannedGlobalObject,
    ScannedObject,
    ScannedStructureMemberObject,
    ScannedVariableObject,
)


def _make_tinfo() -> Any:
    """Create a MagicMock tinfo_t (just needs to be a unique object)."""
    return MagicMock(name="tinfo_t")


def _patch_idc_func_attr(mock_idc: Any) -> Any:
    """Default the mocked idc.get_func_attr to return 0x100 for any ea."""
    mock_idc.get_func_attr.return_value = 0x100
    return mock_idc


def test_scanned_object_creation_sets_fields() -> None:
    """ScannedObject stores name, expression_address, func_ea, origin, _applicable."""
    with patch("hexrays_pytools.domain.scanner.scanned_object.idc") as mock_idc:
        _patch_idc_func_attr(mock_idc)
        obj = ScannedObject("foo", 0x1000, 0x8, True)
        assert obj.name == "foo"
        assert obj.expression_address == 0x1000
        assert obj.func_ea == 0x100
        assert obj.origin == 0x8
        assert obj._applicable is True


def test_scanned_object_equality_by_func_ea_name_ea() -> None:
    """Two ScannedObjects with same (func_ea, name, expression_address) are equal."""
    with patch("hexrays_pytools.domain.scanner.scanned_object.idc") as mock_idc:
        _patch_idc_func_attr(mock_idc)
        a = ScannedObject("foo", 0x1000, 8, True)
        b = ScannedObject("foo", 0x1000, 16, True)
        c = ScannedObject("bar", 0x1000, 8, True)
        assert a == b
        assert hash(a) == hash(b)
        assert a != c


def test_scanned_object_to_list_format() -> None:
    """to_list produces a 4-element list for the chooser viewer."""
    with patch("hexrays_pytools.domain.scanner.scanned_object.idc") as mock_idc, \
         patch("hexrays_pytools.domain.scanner.scanned_object.idaapi") as mock_idaapi, \
         patch("hexrays_pytools.domain.scanner.scanned_object.to_hex") as mock_to_hex:
        _patch_idc_func_attr(mock_idc)
        mock_idaapi.get_short_name.return_value = "my_func"
        mock_to_hex.return_value = "0x00001000"
        obj = ScannedObject("foo", 0x1000, 8, True)
        result = obj.to_list()
        assert result == ["0x0008", "my_func", "foo", "0x00001000"]


def test_scanned_object_factory_dispatches_global() -> None:
    """ScannedObject.create → ScannedGlobalObject when obj.id == SO_GLOBAL_OBJECT."""
    with patch("hexrays_pytools.domain.scanner.scanned_object.idc") as mock_idc:
        _patch_idc_func_attr(mock_idc)
        scan_obj = MagicMock()
        scan_obj.id = SO_GLOBAL_OBJECT
        scan_obj.ea = 0x2000
        scan_obj.name = "g_var"
        result = ScannedObject.create(scan_obj, 0x1000, 8, True)
        assert isinstance(result, ScannedGlobalObject)
        assert result.name == "g_var"


def test_scanned_object_factory_dispatches_local_variable() -> None:
    """ScannedObject.create → ScannedVariableObject when obj.id == SO_LOCAL_VARIABLE."""
    with patch("hexrays_pytools.domain.scanner.scanned_object.idc") as mock_idc:
        _patch_idc_func_attr(mock_idc)
        scan_obj = MagicMock()
        scan_obj.id = SO_LOCAL_VARIABLE
        scan_obj.lvar = MagicMock()
        scan_obj.name = "local"
        result = ScannedObject.create(scan_obj, 0x1000, 8, True)
        assert isinstance(result, ScannedVariableObject)
        assert result.name == "local"


def test_scanned_object_factory_dispatches_struct_member() -> None:
    """Factory dispatches to ScannedStructureMemberObject for struct ptr/ref."""
    with patch("hexrays_pytools.domain.scanner.scanned_object.idc") as mock_idc:
        _patch_idc_func_attr(mock_idc)
        for so_id in (SO_STRUCT_POINTER, SO_STRUCT_REFERENCE):
            scan_obj = MagicMock()
            scan_obj.id = so_id
            scan_obj.struct_name = "Foo"
            scan_obj.offset = 0x10
            scan_obj.name = "field"
            result = ScannedObject.create(scan_obj, 0x1000, 8, True)
            assert isinstance(result, ScannedStructureMemberObject), f"id={so_id}"


def test_scanned_object_factory_asserts_unknown_id() -> None:
    """Factory raises AssertionError for unrecognised obj.id."""
    with patch("hexrays_pytools.domain.scanner.scanned_object.idc") as mock_idc:
        _patch_idc_func_attr(mock_idc)
        scan_obj = MagicMock()
        scan_obj.id = 999  # not in {GLOBAL, LOCAL, STRUCT_*}
        with pytest.raises(AssertionError):
            ScannedObject.create(scan_obj, 0x1000, 8, True)


def test_scanned_global_apply_type_calls_set_tinfo() -> None:
    """ScannedGlobalObject.apply_type invokes idaapi.set_tinfo(obj_ea, tinfo)."""
    with patch("hexrays_pytools.domain.scanner.scanned_object.idc") as mock_idc, \
         patch("hexrays_pytools.domain.scanner.scanned_object.idaapi") as mock_idaapi:
        _patch_idc_func_attr(mock_idc)
        mock_idaapi.set_tinfo = MagicMock()
        scan_obj = MagicMock()
        scan_obj.id = SO_GLOBAL_OBJECT
        scan_obj.ea = 0x2000
        scan_obj.name = "g"
        obj = ScannedObject.create(scan_obj, 0x1000, 8, True)
        assert isinstance(obj, ScannedGlobalObject)
        tinfo = _make_tinfo()
        obj.apply_type(tinfo)
        mock_idaapi.set_tinfo.assert_called_once_with(0x2000, tinfo)


def test_scanned_global_apply_type_skipped_when_not_applicable() -> None:
    """apply_type is a no-op when _applicable is False (crippled function)."""
    with patch("hexrays_pytools.domain.scanner.scanned_object.idc") as mock_idc, \
         patch("hexrays_pytools.domain.scanner.scanned_object.idaapi") as mock_idaapi:
        _patch_idc_func_attr(mock_idc)
        mock_idaapi.set_tinfo = MagicMock()
        scan_obj = MagicMock()
        scan_obj.id = SO_GLOBAL_OBJECT
        scan_obj.ea = 0x2000
        scan_obj.name = "g"
        obj = ScannedObject.create(scan_obj, 0x1000, 8, False)  # not applicable
        obj.apply_type(_make_tinfo())
        mock_idaapi.set_tinfo.assert_not_called()


def test_scanned_variable_apply_type_finds_lvar_in_pseudocode() -> None:
    """ScannedVariableObject.apply_type finds the lvar by locator and sets type."""
    with patch("hexrays_pytools.domain.scanner.scanned_object.idc") as mock_idc, \
         patch("hexrays_pytools.domain.scanner.scanned_object.idaapi") as mock_idaapi:
        _patch_idc_func_attr(mock_idc)
        mock_hx_view = MagicMock()
        # lvar_t comparison with lvar_locator_t: returns True when locator matches
        mock_lvar = MagicMock()
        type(mock_lvar).__eq__ = lambda self, other: True  # noqa: E731 - test override
        mock_hx_view.cfunc.get_lvars.return_value = [mock_lvar]
        mock_hx_view.set_lvar_type = MagicMock()
        mock_idaapi.open_pseudocode.return_value = mock_hx_view
        mock_idaapi.lvar_locator_t = MagicMock()

        scan_obj = MagicMock()
        scan_obj.id = SO_LOCAL_VARIABLE
        scan_obj.lvar = MagicMock(location=MagicMock(), defea=0x100)
        scan_obj.name = "local"
        obj = ScannedObject.create(scan_obj, 0x1000, 8, True)
        assert isinstance(obj, ScannedVariableObject)

        obj.apply_type(_make_tinfo())
        mock_hx_view.set_lvar_type.assert_called_once()


def test_scanned_variable_apply_type_logs_warning_when_lvar_missing() -> None:
    """When lvar not in current pseudocode's lvars, log warning (no crash)."""
    with patch("hexrays_pytools.domain.scanner.scanned_object.idc") as mock_idc, \
         patch("hexrays_pytools.domain.scanner.scanned_object.idaapi") as mock_idaapi, \
         patch("hexrays_pytools.domain.scanner.scanned_object.logger") as mock_logger:
        _patch_idc_func_attr(mock_idc)
        mock_hx_view = MagicMock()
        # lvars is empty → lvar not found
        mock_hx_view.cfunc.get_lvars.return_value = []
        mock_hx_view.set_lvar_type = MagicMock()
        mock_idaapi.open_pseudocode.return_value = mock_hx_view
        mock_idaapi.lvar_locator_t = MagicMock()

        scan_obj = MagicMock()
        scan_obj.id = SO_LOCAL_VARIABLE
        scan_obj.lvar = MagicMock(location=MagicMock(), defea=0x100)
        scan_obj.name = "local"
        obj = ScannedObject.create(scan_obj, 0x1000, 8, True)
        obj.apply_type(_make_tinfo())
        mock_hx_view.set_lvar_type.assert_not_called()
        # logger.warning was called (warn was deprecated in Py3.7+)
        assert mock_logger.warning.called


def test_scanned_member_apply_type_logs_not_implemented() -> None:
    """ScannedStructureMemberObject.apply_type logs warning (not yet implemented)."""
    with patch("hexrays_pytools.domain.scanner.scanned_object.idc") as mock_idc, \
         patch("hexrays_pytools.domain.scanner.scanned_object.logger") as mock_logger:
        _patch_idc_func_attr(mock_idc)
        scan_obj = MagicMock()
        scan_obj.id = SO_STRUCT_POINTER
        scan_obj.struct_name = "Foo"
        scan_obj.offset = 0x10
        scan_obj.name = "field"
        obj = ScannedObject.create(scan_obj, 0x1000, 8, True)
        assert isinstance(obj, ScannedStructureMemberObject)
        obj.apply_type(_make_tinfo())
        assert mock_logger.warning.called
