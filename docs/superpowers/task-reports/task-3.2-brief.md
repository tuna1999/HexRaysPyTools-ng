# Task 3.2 Brief: domain/browser/registered_vtable.py

## Files (2)
1. `src/hexrays_pytools/domain/browser/registered_vtable.py`
2. `tests/domain/browser/test_registered_vtable.py`

## `registered_vtable.py` (verbatim)

```python
"""RegisteredVTable — a vtable that exists in Local Types (not discovered).

Renamed from `core/classes.VirtualTable` to disambiguate from
`recon.DiscoveredVTable` (the working-copy vtable from scanning).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

import idaapi  # type: ignore[import-not-found]


@dataclass
class VirtualMethod:
    """A single method in a registered vtable."""
    name: str
    tinfo: Any = None
    address: int = 0
    parents: list = field(default_factory=list)  # parent vtable ordinals (for multi-inheritance)


@dataclass
class RegisteredVTable:
    """A vtable that lives in Local Types."""
    name: str
    ordinal: int = 0
    class_name: str = ""
    offset: int = 0
    virtual_functions: list = field(default_factory=list)  # list[VirtualMethod]
    tinfo: Any = None

    def tooltip(self) -> str:
        """Return a hover hint for the vtable."""
        if self.tinfo is not None and hasattr(self.tinfo, "dstr"):
            return str(self.tinfo.dstr())
        return f"{self.class_name}::{self.name}@+0x{self.offset:x}"
```

## `test_registered_vtable.py` (verbatim)

```python
"""Test RegisteredVTable."""
from hexrays_pytools.domain.browser.registered_vtable import (
    RegisteredVTable, VirtualMethod,
)


def test_registered_vtable_defaults() -> None:
    v = RegisteredVTable(name="vtable", ordinal=42)
    assert v.name == "vtable"
    assert v.ordinal == 42
    assert v.virtual_functions == []


def test_virtual_method_defaults() -> None:
    m = VirtualMethod(name="foo")
    assert m.name == "foo"
    assert m.address == 0
    assert m.parents == []


def test_tooltip_with_tinfo() -> None:
    v = RegisteredVTable(name="vtable", class_name="Foo")
    v.tinfo = MagicMock()
    v.tinfo.dstr.return_value = "struct Foo_vtable { void(*bar)(); }"
    assert "Foo_vtable" in v.tooltip()


def test_tooltip_without_tinfo() -> None:
    v = RegisteredVTable(name="vtable", class_name="Foo", offset=0x10)
    hint = v.tooltip()
    assert "Foo" in hint
    assert "vtable" in hint
    assert "0x10" in hint
```

Add `from unittest.mock import MagicMock` to imports.

## Verification
```bash
PYTHONPATH=src pytest tests/domain/browser/test_registered_vtable.py -v
python -m mypy --strict src/hexrays_pytools/domain/browser/registered_vtable.py
python -m ruff check src/hexrays_pytools/domain/browser/registered_vtable.py tests/domain/browser/test_registered_vtable.py
```

## Commit
```bash
git add src/hexrays_pytools/domain/browser/registered_vtable.py tests/domain/browser/test_registered_vtable.py
git commit -m "feat(browser): add RegisteredVTable (renamed from classes.VirtualTable)"
```

## Report
`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-3.2-report.md`