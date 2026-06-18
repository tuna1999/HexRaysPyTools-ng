"""Test DiscoveredVTable and friends."""
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
