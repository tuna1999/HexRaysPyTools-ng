# Task 3.1 Brief: domain/browser/registered_class.py

## Files (3)
1. `src/hexrays_pytools/domain/browser/__init__.py` (empty)
2. `src/hexrays_pytools/domain/browser/registered_class.py`
3. `tests/domain/browser/__init__.py` (empty)
4. `tests/domain/browser/test_registered_class.py`

## `registered_class.py` (verbatim — simplified from core/classes.py:Class)

```python
"""Class — a struct/class with virtual tables, registered in Local Types.

Extracted from `core/classes.py:Class`. Represents a single class discovered
in Local Types that has one or more vtable fields.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

import idaapi  # type: ignore[import-not-found]


@dataclass
class Class:
    """A struct/class with vtable fields."""
    name: str
    ordinal: int = 0
    tinfo: Any = None
    vtables: dict[int, Any] = field(default_factory=dict)  # offset -> RegisteredVTable
    selected: bool = False

    @staticmethod
    def create(ordinal: int) -> "Class | None":
        """Factory: read a Local Type and return a Class if it has a vtable field.

        Returns None if the type is not a class with vtables.
        """
        tinfo = idaapi.tinfo_t()
        tinfo.get_numbered_type(idaapi.get_idati(), ordinal)
        if not tinfo or not tinfo.is_udt():
            return None
        udt = idaapi.udt_type_data_t()
        tinfo.get_udt_details(udt)
        # Heuristic: if any field is a ptr-to-struct-of-funcptrs, it's a vtable
        has_vtable = False
        for member in udt:
            mt = member.type
            if mt.is_ptr():
                pointed = mt.get_pointed_object()
                if pointed and pointed.is_funcptr():
                    has_vtable = True
                    break
        if not has_vtable:
            return None
        return Class(
            name=str(tinfo.dstr()) if hasattr(tinfo, "dstr") else "",
            ordinal=ordinal,
            tinfo=tinfo,
        )

    def has_function(self, name_regex: str) -> bool:
        """Return True if any vtable contains a function matching `name_regex`."""
        import re
        for vtable in self.vtables.values():
            for vf in getattr(vtable, "virtual_functions", []):
                if re.search(name_regex, getattr(vf, "name", "")):
                    return True
        return False
```

## `test_registered_class.py` (verbatim)

```python
"""Test Class."""
from hexrays_pytools.domain.browser.registered_class import Class


def test_class_init_default_fields() -> None:
    cls = Class(name="Foo")
    assert cls.name == "Foo"
    assert cls.ordinal == 0
    assert cls.vtables == {}
    assert cls.selected is False


def test_class_has_function_empty() -> None:
    """has_function returns False when vtables is empty."""
    cls = Class(name="Foo")
    assert cls.has_function("anything") is False


def test_class_has_function_matches() -> None:
    """has_function returns True when a vtable function name matches."""
    cls = Class(name="Foo")
    vf = MagicMock()
    vf.name = "doSomething"
    vtable = MagicMock()
    vtable.virtual_functions = [vf]
    cls.vtables[0] = vtable
    assert cls.has_function("doSomething") is True


def test_class_has_function_no_match() -> None:
    """has_function returns False when no vtable function name matches."""
    cls = Class(name="Foo")
    vf = MagicMock()
    vf.name = "doSomething"
    vtable = MagicMock()
    vtable.virtual_functions = [vf]
    cls.vtables[0] = vtable
    assert cls.has_function("doNothing") is False


def test_class_repr_doesnt_crash() -> None:
    """Class() doesn't have a custom __repr__; default is fine (not 'class_name' in output)."""
    cls = Class(name="Foo")
    r = repr(cls)
    assert "Foo" in r
```

Add `from unittest.mock import MagicMock` to imports.

## Verification
```bash
PYTHONPATH=src pytest tests/domain/browser/test_registered_class.py -v
python -m mypy --strict src/hexrays_pytools/domain/browser/registered_class.py
python -m ruff check src/hexrays_pytools/domain/browser/ tests/domain/browser/
```

## Commit
```bash
git add src/hexrays_pytools/domain/browser/ tests/domain/browser/
git commit -m "feat(browser): add Class (was core/classes.Class)"
```

## Report
`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-3.1-report.md`