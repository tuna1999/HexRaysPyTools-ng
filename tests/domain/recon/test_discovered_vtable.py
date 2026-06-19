"""Test DiscoveredVTable and friends."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from hexrays_pytools.domain.recon.discovered_vtable import (
    DiscoveredVTable,
    ImportedVirtualFunction,
    VirtualFunction,
)


def test_discovered_vtable_is_abstract_member() -> None:
    """DiscoveredVTable is a subclass of AbstractMember."""
    v = DiscoveredVTable(offset=0x100)
    assert v.offset == 0x100
    assert v.virtual_functions == []


def test_virtual_function_default_fields() -> None:
    """VirtualFunction has sensible defaults."""
    vf = VirtualFunction(offset=0)
    assert vf.name == ""
    assert vf.func_ea == 0


def test_imported_virtual_function_default_fields() -> None:
    """ImportedVirtualFunction has sensible defaults."""
    vf = ImportedVirtualFunction(offset=0)
    assert vf.name == ""


def test_check_address_returns_true_for_nonzero() -> None:
    """check_address returns True for non-zero EA (heuristic stub)."""
    assert DiscoveredVTable.check_address(0x401000) is True


def test_check_address_returns_false_for_zero() -> None:
    """check_address returns False for zero EA."""
    assert DiscoveredVTable.check_address(0) is False


def test_import_to_structures_no_entries_returns_false() -> None:
    """import_to_structures returns False when no function pointers are found."""
    v = DiscoveredVTable(offset=0)
    v.func_ea = 0x401000  # type: ignore[attr-defined]

    # Mock idc.get_wide_dword to return 0 → no entries → return False
    with patch("hexrays_pytools.domain.recon.discovered_vtable.idc") as mock_idc:
        mock_idc.get_wide_dword.return_value = 0
        assert v.import_to_structures(ask=False) is False


def test_import_to_structures_calls_create_type_with_declaration() -> None:
    """import_to_structures builds the C declaration and calls create_type."""
    v = DiscoveredVTable(offset=0)
    v.func_ea = 0x401000  # type: ignore[attr-defined]

    # Mock idc.get_wide_dword to return 2 valid pointers then 0 (stop).
    # Patch create_type at its source — the discovered_vtable module
    # imports it via `from ..til.type_library import create_type` so the
    # function lives in our namespace too. Patch there.
    with patch("hexrays_pytools.domain.recon.discovered_vtable.idc") as mock_idc, \
         patch("hexrays_pytools.domain.recon.discovered_vtable.idaapi") as mock_idaapi, \
         patch(
             "hexrays_pytools.domain.til.type_library.create_type",
             return_value=True,
         ) as mock_create_type:
        mock_idc.get_wide_dword.side_effect = [0x500000, 0x500100, 0]
        mock_idaapi.is_code.return_value = True
        mock_idaapi.get_64bit.return_value = False
        mock_idaapi.get_full_flags.return_value = 0

        result = v.import_to_structures(ask=False)
        assert result is True
        assert mock_create_type.called
        # First call args: (vtable_name, declaration)
        call_args = mock_create_type.call_args
        assert call_args[0][0].startswith("vtable_")
        assert "void* fn_0;" in call_args[0][1]
        assert "void* fn_4;" in call_args[0][1]
