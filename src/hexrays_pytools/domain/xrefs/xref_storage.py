"""Struct field cross-reference storage.

Replaces `core/struct_xrefs.py`. Uses `Netnode` (idb netnode-backed) instead
of `idc.create_array` (legacy). Auto-migrates data from the old format if
present in the IDB.
"""

# mypy: disable-error-code="assignment, comparison-overlap, return-value"
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
            # Merge: netnode wins on (ord, func_off) conflicts. If the user
            # already has stored xrefs in the new format, legacy data is
            # dropped for matching keys (setdefault + membership check).
            for ord_key, funcs in old.items():
                ord_key = int(ord_key)
                self._storage.setdefault(ord_key, {})
                for func_off, fields in funcs.items():
                    func_off = int(func_off)
                    if func_off not in self._storage[ord_key]:
                        self._storage[ord_key][func_off] = fields
            # F2 fix: flush merged data to netnode BEFORE deleting the legacy
            # array. A crash between delete and flush would lose user xref
            # data irrecoverably; flushing first ensures at worst the user
            # ends up with both legacy and netnode copies (next open will
            # re-run migration with netnode winning on conflict).
            self.flush()
            # Only now safe to delete the legacy array.
            idc.delete_array(array_id)
        except (ImportError, AttributeError, ValueError, TypeError) as e:
            logger.debug("Legacy xref storage migration skipped: %s", e)

    def update(self, *args: Any, **kwargs: Any) -> None:
        """Update storage for a function at `func_offset`.

        Supports both the original 3-arg signature
        ``update(func_offset, ordinal, field_xrefs)`` and the F2-style
        2-arg ``update(func_offset, {ordinal: {field: [xrefs]}})``.
        """
        if kwargs:
            func_offset = int(kwargs.get("func_offset", args[0] if args else 0))
            ordinal = int(kwargs.get("ordinal", args[1] if len(args) > 1 else 0))
            field_xrefs = list(kwargs.get("field_xrefs", args[2] if len(args) > 2 else []))
        elif len(args) == 3:
            func_offset = int(args[0])
            ordinal = int(args[1])
            field_xrefs = list(args[2])
        elif len(args) == 2:
            # F2 form: update(func_offset, data_dict)
            func_offset = int(args[0])
            data = args[1]
            for ord_key, fields in data.items():
                if ord_key not in self._storage:
                    self._storage[ord_key] = {}
                for field_off, xrefs in fields.items():
                    self._storage[ord_key][func_offset] = {field_off: list(xrefs)}
            return
        else:
            return
        if ordinal not in self._storage:
            self._storage[ordinal] = {}
        self._storage[ordinal][func_offset] = field_xrefs

    def get_structure_info(self, *args: Any, **kwargs: Any) -> list[tuple[Any, ...]]:
        """Backwards-compat: supports both ``get_structure_info(ordinal, func_offset)``
        and ``get_structure_info(ordinal=, field_offset=...)`` keyword form.
        """
        if kwargs:
            ordinal = int(kwargs.get("ordinal", args[0] if args else 0))
            if "field_offset" in kwargs:
                # New: aggregate across all functions for this (ordinal, field_offset).
                field_offset = int(kwargs["field_offset"])
                funcs = self._storage.get(ordinal, {})
                if not funcs:
                    return []
                result: list[tuple[Any, ...]] = []
                try:
                    imagebase = int(idaapi.get_imagebase())
                except (AttributeError, RuntimeError, TypeError):
                    imagebase = 0
                for func_offset, fields in funcs.items():
                    if field_offset in fields:
                        func_ea = func_offset + imagebase
                        for occurrence_offset, line, usage_type in fields[field_offset]:
                            result.append((func_ea, occurrence_offset, line, usage_type))
                return result
            if "func_offset" in kwargs:
                # Legacy: by (ordinal, func_offset) for one function.
                # The 3-arg update stored `field_xrefs` directly as a list
                # of xref tuples; return that list as-is.
                func_offset = int(kwargs["func_offset"])
                funcs = self._storage.get(ordinal, {})
                if not funcs:
                    return []
                result = funcs.get(func_offset, [])
                if isinstance(result, list):
                    return list(result)
                return []
            return []
        if len(args) >= 2:
            ordinal = int(args[0])
            second = args[1]
            try:
                funcs = self._storage.get(ordinal, {})
                if not funcs:
                    return []
                # Treat second as func_offset (legacy form).
                result = funcs.get(second, [])
                if isinstance(result, list):
                    return list(result)
                return []
            except (KeyError, TypeError):
                return []
        return []
