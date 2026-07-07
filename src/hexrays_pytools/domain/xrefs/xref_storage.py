"""Struct field cross-reference storage.

Replaces `core/struct_xrefs.py`. Uses `Netnode` (idb netnode-backed) instead
of `idc.create_array` (legacy). Auto-migrates data from the old format if
present in the IDB.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import idaapi  # type: ignore[import-not-found]
import idc  # type: ignore[import-not-found]

from ...infra.idb.netnode import Netnode

logger = logging.getLogger(__name__)

# Old array name from the original plugin (for auto-migrate)
OLD_ARRAY_NAME = "$HexRaysPyTools-ng:XrefStorage"
# New netnode name
NODE_NAME = "$hexrays_pytools_ng/xref_storage"


class XrefStorage:
    """In-memory cache of struct field xrefs, persisted via netnode."""

    def __init__(self) -> None:
        self._storage: dict[int, dict[int, list[tuple[Any, ...]]]] = {}
        self._node: Netnode | None = None

    def open(self) -> None:
        """Open the netnode and load existing data (auto-migrate from old format)."""
        self._node = Netnode(NODE_NAME)
        if self._node.exists:
            raw = self._node.get_string()
            if raw:
                try:
                    self._storage = json.loads(
                        raw, object_hook=lambda d: {int(k): v for k, v in d.items()}
                    )
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
            array_id = idc.get_array_id(OLD_ARRAY_NAME)
            if array_id == idaapi.BADORD:
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

    def update(self, func_offset: int, ordinal: int, field_xrefs: list[tuple[Any, ...]]) -> None:
        """Update storage for a function at `func_offset`."""
        if ordinal not in self._storage:
            self._storage[ordinal] = {}
        self._storage[ordinal][func_offset] = field_xrefs

    def get_structure_info(self, ordinal: int, func_offset: int) -> list[tuple[Any, ...]]:
        """Get field xrefs for the given ordinal and func_offset."""
        return self._storage.get(ordinal, {}).get(func_offset, [])
