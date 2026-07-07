"""Test XrefStorage."""
from unittest.mock import patch

import idaapi  # type: ignore[import-not-found]

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


# ---------------------------------------------------------------------------
# F2: Migration atomicity + correct "netnode wins" comment
# ---------------------------------------------------------------------------


def test_migrate_from_legacy_writes_to_netnode_before_delete() -> None:
    """F2: flush merged data to netnode BEFORE idc.delete_array.

    A crash between delete and flush would lose user xref data irrecoverably.
    Order in source code is the contract.
    """
    import inspect

    from hexrays_pytools.domain.xrefs.xref_storage import XrefStorage

    source = inspect.getsource(XrefStorage._migrate_from_legacy)
    # The flush must happen BEFORE delete_array in source order
    flush_pos = source.find("self.flush()")
    delete_pos = source.find("idc.delete_array")
    assert flush_pos != -1, "self.flush() not found in _migrate_from_legacy"
    assert delete_pos != -1, "idc.delete_array not found in _migrate_from_legacy"
    assert flush_pos < delete_pos, (
        "F2 violation: idc.delete_array is called before self.flush() — "
        "a crash between the two would lose user data irrecoverably"
    )


def test_migrate_comment_documents_netnode_wins_semantic() -> None:
    """F2: comment in _migrate_from_legacy must say 'netnode wins'."""
    import inspect

    from hexrays_pytools.domain.xrefs.xref_storage import XrefStorage

    source = inspect.getsource(XrefStorage._migrate_from_legacy)
    assert "legacy takes precedence" not in source.lower(), (
        "F2 violation: comment says legacy takes precedence but code makes netnode win"
    )
    assert "netnode wins" in source.lower(), (
        "F2: comment should explicitly state 'netnode wins' semantic"
    )


def test_migrate_noop_when_legacy_absent() -> None:
    """If idc.get_array_id returns BADORD, no migration + no delete happens."""
    from hexrays_pytools.domain.xrefs.xref_storage import XrefStorage

    x = XrefStorage()
    with patch("hexrays_pytools.domain.xrefs.xref_storage.idc") as mock_idc, \
         patch("hexrays_pytools.domain.xrefs.xref_storage.Netnode"):
        mock_idc.get_array_id.return_value = idaapi.BADORD
        x._migrate_from_legacy()
        mock_idc.delete_array.assert_not_called()
        mock_idc.get_array_element.assert_not_called()


def test_migrate_merges_when_netnode_empty() -> None:
    """If netnode storage is empty, legacy data is loaded into it."""
    from hexrays_pytools.domain.xrefs.xref_storage import XrefStorage

    x = XrefStorage()
    x._storage = {}
    legacy_data = {"42": {"256": [["field_a", 0, "read"]]}}

    with patch("hexrays_pytools.domain.xrefs.xref_storage.idc") as mock_idc, \
         patch("hexrays_pytools.domain.xrefs.xref_storage.Netnode"), \
         patch("hexrays_pytools.domain.xrefs.xref_storage.json") as mock_json:
        mock_idc.get_array_id.return_value = 999
        mock_idc.get_last_index.return_value = 1
        mock_idc.get_array_element.return_value = b'{"42": {"256": [["field_a", 0, "read"]]}}'
        mock_json.loads.return_value = legacy_data

        x._migrate_from_legacy()

    # Legacy data merged into netnode storage
    assert 42 in x._storage
    assert 256 in x._storage[42]
    assert x._storage[42][256] == [["field_a", 0, "read"]]
    # Legacy array deleted after migration
    mock_idc.delete_array.assert_called_once()


def test_migrate_netnode_wins_on_conflict() -> None:
    """If netnode already has data for (ord, func_off), legacy is dropped."""
    from hexrays_pytools.domain.xrefs.xref_storage import XrefStorage

    x = XrefStorage()
    # Netnode already has data for (42, 256)
    x._storage = {42: {256: [["netnode_value", 0, "read"]]}}
    legacy_data = {"42": {"256": [["legacy_value", 0, "read"]]}}

    with patch("hexrays_pytools.domain.xrefs.xref_storage.idc") as mock_idc, \
         patch("hexrays_pytools.domain.xrefs.xref_storage.Netnode"), \
         patch("hexrays_pytools.domain.xrefs.xref_storage.json") as mock_json:
        mock_idc.get_array_id.return_value = 999
        mock_idc.get_last_index.return_value = 1
        mock_idc.get_array_element.return_value = b'{"42": {"256": [["legacy_value", 0, "read"]]}}'
        mock_json.loads.return_value = legacy_data

        x._migrate_from_legacy()

    # Netnode value wins — legacy dropped for conflicting key
    assert x._storage[42][256] == [["netnode_value", 0, "read"]]
