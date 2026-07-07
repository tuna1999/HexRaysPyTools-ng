"""Test XrefStorage."""
from hexrays_pytools.domain.xrefs.xref_storage import (
    OLD_ARRAY_NAME,
    XrefStorage,
)


def test_xref_storage_init() -> None:
    """A new XrefStorage has empty storage."""
    x = XrefStorage()
    assert x._storage == {}


def test_xref_storage_open_uses_netnode() -> None:
    """open() creates a Netnode for storage."""
    x = XrefStorage()
    x.open()
    assert x._node is not None


def test_xref_storage_update() -> None:
    """update() stores field xrefs for a function."""
    x = XrefStorage()
    x.update(func_offset=0x100, ordinal=42, field_xrefs=[(0x200, 1, "read")])
    assert x._storage[42][0x100] == [(0x200, 1, "read")]


def test_xref_storage_get_structure_info() -> None:
    """get_structure_info returns xrefs for known ordinal/func_offset."""
    x = XrefStorage()
    x.update(func_offset=0x100, ordinal=42, field_xrefs=[(0x200, 1, "read")])
    result = x.get_structure_info(ordinal=42, func_offset=0x100)
    assert result == [(0x200, 1, "read")]


def test_xref_storage_get_returns_empty_for_unknown() -> None:
    """get_structure_info returns empty list for unknown ordinal/func_offset."""
    x = XrefStorage()
    assert x.get_structure_info(ordinal=999, func_offset=0xFFF) == []


def test_old_array_name_constant() -> None:
    """OLD_ARRAY_NAME matches the original plugin's name (for migration)."""
    assert OLD_ARRAY_NAME == "$HexRaysPyTools-ng:XrefStorage"
