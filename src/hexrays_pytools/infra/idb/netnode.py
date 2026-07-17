"""Typed wrapper around idaapi.netnode for IDB storage.

Replaces the original `helper.save_long_str_to_idb` / `load_long_str_from_idb`
which used `idc.create_array` (legacy API).

Netnode API:
- Create: `netnode("$name")` returns a `netnode` object
- Blob storage: `.supstr(idx)` get, `.supset(idx, str)` set
- Integer storage: `.altval(idx)` get, `.altset(idx, val)` set
"""

from __future__ import annotations

import idaapi  # type: ignore[import-not-found]


class Netnode:
    """Typed wrapper for a single named netnode in the IDB."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._node = idaapi.netnode(name)

    @property
    def exists(self) -> bool:
        """Return True if the netnode exists in the current IDB."""
        return bool(self._node != 0)

    def get_string(self, key: int = 0) -> str:
        """Get a string stored at `key` (default 0 for single-blob nodes)."""
        return self._node.supstr(key) or ""

    def set_string(self, value: str, key: int = 0) -> bool:
        """Store `value` at `key`. Returns True on success."""
        return bool(self._node.supset(key, value))

    def get_int(self, key: int) -> int:
        """Get an integer stored at `key`."""
        return int(self._node.altval(key))

    def set_int(self, key: int, value: int) -> None:
        """Store `value` at `key`."""
        self._node.altset(key, value)

    def delete(self) -> bool:
        """Delete this netnode from the IDB."""
        return bool(self._node.kill())
