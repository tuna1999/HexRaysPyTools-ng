# Task 1.2 Brief: infra/idb/netnode.py

## Files to Create

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\infra\idb\__init__.py` (empty)
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\infra\idb\netnode.py`
3. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\infra\test_netnode.py`

## Required Content (verbatim)

### `src/hexrays_pytools/infra/idb/netnode.py`

```python
"""Typed wrapper around idaapi.netnode for IDB storage.

Replaces the original `helper.save_long_str_to_idb` / `load_long_str_from_idb`
which used `idc.create_array` (legacy API).

Netnode API:
- Create: `netnode("$name")` returns a `netnode` object
- Blob storage: `.supstr(idx)` get, `.supset(idx, str)` set
- Integer storage: `.altval(idx)` get, `.altset(idx, val)` set
"""
from __future__ import annotations
import idaapi


class Netnode:
    """Typed wrapper for a single named netnode in the IDB."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._node = idaapi.netnode(name)

    @property
    def exists(self) -> bool:
        """Return True if the netnode exists in the current IDB."""
        return self._node != 0

    def get_string(self, key: int = 0) -> str:
        """Get a string stored at `key` (default 0 for single-blob nodes)."""
        return self._node.supstr(key) or ""

    def set_string(self, value: str, key: int = 0) -> bool:
        """Store `value` at `key`. Returns True on success."""
        return self._node.supset(key, value)

    def get_int(self, key: int) -> int:
        """Get an integer stored at `key`."""
        return self._node.altval(key)

    def set_int(self, key: int, value: int) -> None:
        """Store `value` at `key`."""
        self._node.altset(key, value)

    def delete(self) -> bool:
        """Delete this netnode from the IDB."""
        return self._node.kill()
```

### `tests/infra/test_netnode.py`

```python
"""Test Netnode wrapper."""
from unittest.mock import MagicMock
from hexrays_pytools.infra.idb.netnode import Netnode


def test_netnode_creates_with_name() -> None:
    """Netnode(name) creates a netnode via idaapi.netnode(name)."""
    netnode = Netnode("$test_name")
    idaapi = __import__("idaapi")
    idaapi.netnode.assert_called_with("$test_name")


def test_netnode_exists_property() -> None:
    """exists property returns True if node value is not 0."""
    __import__("idaapi").netnode.return_value = 42
    netnode = Netnode("$test")
    assert netnode.exists is True


def test_netnode_get_string_returns_empty_when_none() -> None:
    """get_string() returns empty string if supstr returns None."""
    __import__("idaapi").netnode.return_value.supstr.return_value = None
    netnode = Netnode("$test")
    assert netnode.get_string() == ""


def test_netnode_set_string_calls_supset() -> None:
    """set_string calls node.supset with the value."""
    __import__("idaapi").netnode.return_value.supset.return_value = True
    netnode = Netnode("$test")
    result = netnode.set_string("hello world")
    __import__("idaapi").netnode.return_value.supset.assert_called_with(0, "hello world")
    assert result is True


def test_netnode_delete_calls_kill() -> None:
    """delete() calls node.kill() and returns its result."""
    mock_node = __import__("idaapi").netnode.return_value
    mock_node.kill.return_value = True
    netnode = Netnode("$test")
    assert netnode.delete() is True
    mock_node.kill.assert_called_once()
```

## Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/infra/test_netnode.py -v
python -m mypy --strict src/hexrays_pytools/infra/idb/netnode.py
python -m ruff check src/hexrays_pytools/infra/idb/ tests/infra/
```

## Commit

```bash
git add src/hexrays_pytools/infra/idb/ tests/infra/test_netnode.py
git commit -m "feat(infra): add Netnode wrapper for IDB storage (replaces idc.create_array)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-1.2-report.md`

Apply minimal lint fixes (mypy type ignore, ruff F401 unused imports) and document in DONE_WITH_CONCERNS.
