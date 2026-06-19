# Task 2.5 Brief: domain/scanner/scanned_object.py

## Files

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\scanner\scanned_object.py`
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\scanner\test_scanned_object.py`

## Content (verbatim)

### `src/hexrays_pytools/domain/scanner/scanned_object.py`

```python
"""ScanObject hierarchy — represents items found during ctree traversal.

Extracted from the original `api.py`. Used by `ObjectVisitor` subclasses
to track which expressions/variables/functions to operate on.
"""
from __future__ import annotations
import idaapi  # type: ignore[import-not-found]


# Object kind constants (used by `ScanObject.create()` factory)
SO_LOCAL_VARIABLE = 1
SO_STRUCT_POINTER = 2
SO_STRUCT_REFERENCE = 3
SO_GLOBAL_OBJECT = 4
SO_CALL_ARGUMENT = 5
SO_MEMORY_ALLOCATOR = 6
SO_RETURNED_OBJECT = 7


class ScanObject:
    """Base class for a single scanned item."""

    def __init__(self, ea: int, name: str, tinfo: idaapi.tinfo_t, op: int) -> None:  # type: ignore[name-defined]
        self.ea = ea
        self.name = name
        self.tinfo = tinfo
        self.id = op

    def is_target(self, cexpr: idaapi.cexpr_t) -> bool:  # type: ignore[name-defined]
        """Return True if `cexpr` represents this object."""
        return cexpr.op == self.id

    def get_expression_address(self, cfunc: idaapi.cfunc_t, cexpr: idaapi.cexpr_t) -> int:  # type: ignore[name-defined]
        """Walk up ctree parents to find a real address for `cexpr`."""
        while cexpr and cexpr.ea == idaapi.BADADDR:  # type: ignore[attr-defined]
            parent = cfunc.body.find_parent_of(cexpr)
            if not parent:
                return idaapi.BADADDR  # type: ignore[attr-defined]
            cexpr = parent.cexpr
        return cexpr.ea if cexpr else idaapi.BADADDR  # type: ignore[attr-defined]
```

### `tests/domain/scanner/test_scanned_object.py`

```python
"""Test ScanObject hierarchy."""
from hexrays_pytools.domain.scanner.scanned_object import (
    ScanObject, SO_LOCAL_VARIABLE,
)


def test_scan_object_stores_fields() -> None:
    """ScanObject stores ea, name, tinfo, id."""
    tinfo = MagicMock()
    obj = ScanObject(0x1000, "foo", tinfo, SO_LOCAL_VARIABLE)
    assert obj.ea == 0x1000
    assert obj.name == "foo"
    assert obj.tinfo is tinfo
    assert obj.id == SO_LOCAL_VARIABLE


def test_is_target_matches_op() -> None:
    """is_target returns True when cexpr.op == self.id."""
    obj = ScanObject(0x1000, "foo", MagicMock(), SO_LOCAL_VARIABLE)
    cexpr = MagicMock()
    cexpr.op = SO_LOCAL_VARIABLE
    assert obj.is_target(cexpr) is True


def test_is_target_rejects_other_op() -> None:
    """is_target returns False when cexpr.op != self.id."""
    obj = ScanObject(0x1000, "foo", MagicMock(), SO_LOCAL_VARIABLE)
    cexpr = MagicMock()
    cexpr.op = 999
    assert obj.is_target(cexpr) is False
```

Add `from unittest.mock import MagicMock` to imports.

## Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/domain/scanner/test_scanned_object.py -v
python -m mypy --strict src/hexrays_pytools/domain/scanner/scanned_object.py
python -m ruff check src/hexrays_pytools/domain/scanner/scanned_object.py tests/domain/scanner/test_scanned_object.py
```

## Commit

```bash
git add src/hexrays_pytools/domain/scanner/scanned_object.py tests/domain/scanner/test_scanned_object.py
git commit -m "feat(scanner): add ScanObject base (ea, name, tinfo, is_target)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-2.5-report.md`