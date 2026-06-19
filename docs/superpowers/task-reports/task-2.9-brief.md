# Task 2.9 Brief: domain/recon/discovered_vtable.py

## Files (2)
1. `src/hexrays_pytools/domain/recon/discovered_vtable.py`
2. `tests/domain/recon/test_discovered_vtable.py`

## `discovered_vtable.py` (verbatim, renamed from VirtualTable to avoid collision)

```python
"""Discovered vtable — found during struct reconstruction.

Renamed from `core/temporary_structure.VirtualTable` to avoid collision
with `core/classes.VirtualTable` (a different concept: a registered vtable
in Local Types).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

import idaapi  # type: ignore[import-not-found]

from .member import AbstractMember


@dataclass
class VirtualFunction:
    """A single virtual function entry in a vtable."""
    offset: int
    tinfo: Any = None
    name: str = ""
    func_ea: int = 0


@dataclass
class ImportedVirtualFunction:
    """Virtual function imported from a type library (no decompile)."""
    offset: int
    tinfo: Any = None
    name: str = ""


@dataclass
class DiscoveredVTable(AbstractMember):
    """A vtable discovered while scanning a struct.

    A working copy — different from the registered vtable in Local Types
    (see `domain/browser/registered_vtable.py`).
    """
    virtual_functions: list = field(default_factory=list)

    @staticmethod
    def check_address(ea: int) -> bool:
        """Return True if `ea` looks like a vtable (heuristic)."""
        # Stub: real impl requires reading struct at ea
        return ea > 0
```

## `test_discovered_vtable.py` (verbatim)

```python
"""Test DiscoveredVTable and friends."""
from hexrays_pytools.domain.recon.discovered_vtable import (
    DiscoveredVTable, VirtualFunction, ImportedVirtualFunction,
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
```

## Verification
```bash
PYTHONPATH=src pytest tests/domain/recon/test_discovered_vtable.py -v
python -m mypy --strict src/hexrays_pytools/domain/recon/discovered_vtable.py
python -m ruff check src/hexrays_pytools/domain/recon/discovered_vtable.py tests/domain/recon/test_discovered_vtable.py
```

## Commit
```bash
git add src/hexrays_pytools/domain/recon/discovered_vtable.py tests/domain/recon/test_discovered_vtable.py
git commit -m "feat(recon): add DiscoveredVTable (renamed from VirtualTable to disambiguate)"
```

## Report
`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-2.9-report.md`