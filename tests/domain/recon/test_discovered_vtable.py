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


def test_discovered_vtable_size_is_native_pointer_width() -> None:
    idaapi = __import__("idaapi")
    idaapi.inf_is_64bit.return_value = True
    assert DiscoveredVTable(offset=0).size == 8
    idaapi.inf_is_64bit.return_value = False
    assert DiscoveredVTable(offset=0).size == 4


def test_virtual_function_default_fields() -> None:
    """VirtualFunction has sensible defaults."""
    vf = VirtualFunction(offset=0)
    assert vf.name == ""
    assert vf.func_ea == 0


def test_imported_virtual_function_default_fields() -> None:
    """ImportedVirtualFunction has sensible defaults."""
    vf = ImportedVirtualFunction(offset=0)
    assert vf.name == ""


def test_check_address_accepts_named_function_pointer_table() -> None:
    """A named non-code address followed by code pointers is a vtable candidate."""
    idaapi = __import__("idaapi")
    idaapi.get_name.return_value = "MyClass_vftable"
    idaapi.inf_is_64bit.return_value = False
    with patch(
        "hexrays_pytools.domain.recon.discovered_vtable.is_code_ea",
        side_effect=[False, True],
    ), patch(
        "hexrays_pytools.domain.recon.discovered_vtable.get_ptr",
        side_effect=[0x500000, 0],
    ):
        assert DiscoveredVTable.check_address(0x401000) is True


def test_check_address_returns_false_for_zero() -> None:
    """check_address returns False for zero EA."""
    assert DiscoveredVTable.check_address(0) is False


def test_import_to_structures_no_entries_returns_false() -> None:
    """import_to_structures returns False when no function pointers are found."""
    v = DiscoveredVTable(offset=0, address=0x401000)
    idaapi = __import__("idaapi")
    existing = MagicMock()
    existing.get_named_type.return_value = False
    idaapi.tinfo_t.return_value = existing

    with patch("hexrays_pytools.domain.recon.discovered_vtable.get_ptr", return_value=0):
        assert v.import_to_structures(ask=False) is False


def test_import_to_structures_calls_create_type_with_declaration() -> None:
    """import_to_structures builds the C declaration and calls create_type."""
    v = DiscoveredVTable(offset=0, address=0x401000)

    with patch(
         "hexrays_pytools.domain.recon.discovered_vtable.get_ptr",
         side_effect=[0x500000, 0x500100, 0],
         ) as mock_get_ptr, \
         patch("hexrays_pytools.domain.recon.discovered_vtable.is_code_ea", return_value=True), \
         patch(
             "hexrays_pytools.domain.til.type_library.create_type",
             return_value=True,
         ) as mock_create_type:
        idaapi = __import__("idaapi")
        idaapi.inf_is_64bit.return_value = False
        existing = MagicMock()
        existing.get_named_type.return_value = False
        idaapi.tinfo_t.return_value = existing

        result = v.import_to_structures(ask=False)
        assert result is True
        assert mock_create_type.called
        assert mock_get_ptr.call_args_list[0].args == (0x401000,)
        assert mock_get_ptr.call_args_list[1].args == (0x401004,)
        # First call args: (vtable_name, declaration)
        call_args = mock_create_type.call_args
        assert call_args[0][0].startswith("vtable_")
        assert "void* fn_0;" in call_args[0][1]
        assert "void* fn_4;" in call_args[0][1]


def test_import_to_structures_x64_advances_eight_bytes() -> None:
    """64-bit vtables read native pointers at 8-byte slot boundaries."""
    idaapi = __import__("idaapi")
    idaapi.inf_is_64bit.return_value = True
    existing = MagicMock()
    existing.get_named_type.return_value = False
    idaapi.tinfo_t.return_value = existing
    v = DiscoveredVTable(offset=0, address=0x140001000)

    with patch(
        "hexrays_pytools.domain.recon.discovered_vtable.get_ptr",
        side_effect=[0x140002000, 0x140003000, 0],
    ) as read_ptr, patch(
        "hexrays_pytools.domain.recon.discovered_vtable.is_code_ea", return_value=True
    ), patch("hexrays_pytools.domain.til.type_library.create_type", return_value=True):
        assert v.import_to_structures(ask=False) is True

    assert [c.args[0] for c in read_ptr.call_args_list] == [
        0x140001000,
        0x140001008,
        0x140001010,
    ]


def test_vtable_type_name_uses_table_address_not_struct_offset() -> None:
    v = DiscoveredVTable(offset=0, address=0x401000)
    assert v.type_name == "vtable_401000 *"
