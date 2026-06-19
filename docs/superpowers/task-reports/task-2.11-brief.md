# Task 2.11 Brief: domain/xrefs/xref_storage.py

## Context

Replaces `core/struct_xrefs.py` (107 LOC). The original used `idc.create_array` for storage (legacy API). The rewrite uses `Netnode` from `infra/idb/netnode.py`. This is a planned bug fix (B12 in spec).

Also adds auto-migrate from old format if present (per spec D10).

## Files

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\xrefs\__init__.py` (empty)
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\xrefs\xref_storage.py`
3. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\xrefs\__init__.py` (empty)
4. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\xrefs\test_xref_storage.py`

## Content (verbatim)

### `src/hexrays_pytools/domain/xrefs/xref_storage.py`

```python
"""Struct field cross-reference storage.

Replaces `core/struct_xrefs.py`. Uses `Netnode` (idb netnode-backed) instead
of `idc.create_array` (legacy). Auto-migrates data from the old format if
present in the IDB.
"""
from __future__ import annotations
import json
import logging
import idaapi  # type: ignore[import-not-found]

from ...infra.idb.netnode import Netnode

logger = logging.getLogger(__name__)

# Old array name from the original plugin (for auto-migrate)
OLD_ARRAY_NAME = "$HexRaysPyTools:XrefStorage"
# New netnode name
NODE_NAME = "$hexrays_pytools/xref_storage"


class XrefStorage:
    """In-memory cache of struct field xrefs, persisted via netnode."""

    def __init__(self) -> None:
        self._storage: dict[int, dict[int, list[tuple]]] = {}
        self._node: Netnode | None = None

    def open(self) -> None:
        """Open the netnode and load existing data (auto-migrate from old format)."""
        self._node = Netnode(NODE_NAME)
        if self._node.exists:
            raw = self._node.get_string()
            if raw:
                try:
                    self._storage = json.loads(raw, object_hook=lambda d: {int(k): v for k, v in d.items()})
                except (ValueError, TypeError) as e:
                    logger.warning("Failed to parse xref storage: %s. Resetting.", e)
                    self._storage = {}
        # Auto-migrate from old array format if present
        self._migrate_from_legacy()

    def close(self) -> None:
        """Persist data to the netnode."""
        if self._node:
            self._node.set_string(json.dumps(self._storage))

    def flush(self) -> None:
        """Alias for close() — called by Session.close()."""
        self.close()

    def _migrate_from_legacy(self) -> None:
        """Read old idc.create_array format and merge into storage.

        No-op if the old array doesn't exist (idc API not available in tests).
        """
        try:
            import idc  # type: ignore[import-not-found]
            array_id = idc.get_array_id(OLD_ARRAY_NAME)
            if array_id == idaapi.BADORD:  # type: ignore[attr-defined]
                return
            logger.info("Migrating xref storage from legacy array format")
            last = idc.get_last_index(idc.AR_STR, array_id)
            chunks = []
            for i in range(0, last + 1):
                chunks.append(idc.get_array_element(idc.AR_STR, array_id, i))
            raw = b"".join(chunks).decode("utf-8", errors="replace")
            old = json.loads(raw)
            # Merge: legacy takes precedence for matching ordinals
            for ord_key, funcs in old.items():
                ord_key = int(ord_key)
                self._storage.setdefault(ord_key, {})
                for func_off, fields in funcs.items():
                    func_off = int(func_off)
                    if func_off not in self._storage[ord_key]:
                        self._storage[ord_key][func_off] = fields
            # Delete old array after successful migration
            idc.delete_array(array_id)
        except (ImportError, AttributeError, ValueError, TypeError) as e:
            logger.debug("Legacy xref storage migration skipped: %s", e)

    def update(self, func_offset: int, ordinal: int, field_xrefs: list[tuple]) -> None:
        """Update storage for a function at `func_offset`."""
        if ordinal not in self._storage:
            self._storage[ordinal] = {}
        self._storage[ordinal][func_offset] = field_xrefs

    def get_structure_info(self, ordinal: int, func_offset: int) -> list[tuple]:
        """Get field xrefs for the given ordinal and func_offset."""
        return self._storage.get(ordinal, {}).get(func_offset, [])
```

### `tests/domain/xrefs/test_xref_storage.py`

```python
"""Test XrefStorage."""
from hexrays_pytools.domain.xrefs.xref_storage import XrefStorage, OLD_ARRAY_NAME


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
    assert OLD_ARRAY_NAME == "$HexRaysPyTools:XrefStorage"
```

## Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/domain/xrefs/test_xref_storage.py -v
python -m mypy --strict src/hexrays_pytools/domain/xrefs/xref_storage.py
python -m ruff check src/hexrays_pytools/domain/xrefs/ tests/domain/xrefs/
```

## Commit

```bash
git add src/hexrays_pytools/domain/xrefs/ tests/domain/xrefs/
git commit -m "feat(xrefs): add XrefStorage (netnode-backed, auto-migrate from legacy)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-2.11-report.md`