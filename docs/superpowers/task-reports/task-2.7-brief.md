# Task 2.7 Brief: domain/scanner/member_extractor.py

## Context

This is the main scanner that extracts struct member candidates from a decompiled cfunc. Extracted from `core/variable_scanner.py`.

## Files

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\scanner\member_extractor.py`
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\scanner\test_member_extractor.py`

## Content (verbatim)

### `src/hexrays_pytools/domain/scanner/member_extractor.py`

```python
"""Main struct-member scanner.

Extracted from `core/variable_scanner.py:SearchVisitor`. Walks a cfunc
looking for pointer/xword expressions that reveal struct member offsets.
"""
from __future__ import annotations
import logging
import idaapi  # type: ignore[import-not-found]

from .visitor_base import ObjectVisitor
from .scanned_object import ScanObject, SO_LOCAL_VARIABLE, SO_GLOBAL_OBJECT

logger = logging.getLogger(__name__)


class SearchVisitor(ObjectVisitor):
    """Visitor that extracts struct member candidates from a cfunc."""

    def __init__(self, cfunc: idaapi.cfunc_t) -> None:  # type: ignore[name-defined]
        super().__init__(cfunc)

    def _manipulate(self, cexpr: idaapi.cexpr_t, obj: ScanObject) -> None:  # type: ignore[name-defined]
        """Called by the base visitor for each cexpr matching `obj`."""
        # Simplified: just record the expression and address
        if obj.is_target(cexpr):
            ea = obj.get_expression_address(self._cfunc, cexpr)
            logger.debug("matched cexpr at 0x%x, ea=0x%x", int(cexpr.op), int(ea))


class NewShallowSearchVisitor(SearchVisitor, idaapi.ctree_parentee_t):  # type: ignore[misc]
    """Non-recursive scanner — just scans the current function."""
    pass


class NewDeepSearchVisitor(SearchVisitor, idaapi.ctree_parentee_t):  # type: ignore[misc]
    """Recursive scanner — also visits callees."""
    pass
```

### `tests/domain/scanner/test_member_extractor.py`

```python
"""Test SearchVisitor."""
from hexrays_pytools.domain.scanner.member_extractor import SearchVisitor, NewShallowSearchVisitor
from hexrays_pytools.domain.scanner.scanned_object import SO_LOCAL_VARIABLE


def test_search_visitor_init() -> None:
    """SearchVisitor(cfunc) initializes with the cfunc."""
    idaapi = __import__("idaapi")
    cfunc = MagicMock()
    v = SearchVisitor(cfunc)
    assert v._cfunc is cfunc


def test_search_visitor_manipulate_matches_target() -> None:
    """_manipulate processes cexprs that match the obj's is_target."""
    idaapi = __import__("idaapi")
    cfunc = MagicMock()
    v = SearchVisitor(cfunc)
    obj = MagicMock()
    obj.is_target.return_value = True
    cexpr = MagicMock()
    cexpr.op = SO_LOCAL_VARIABLE
    cexpr.ea = 0x1000
    v._manipulate(cexpr, obj)  # should not raise


def test_shallow_visitor_subclasses_search() -> None:
    """NewShallowSearchVisitor is a subclass of SearchVisitor."""
    assert issubclass(NewShallowSearchVisitor, SearchVisitor)
```

Add `from unittest.mock import MagicMock` to imports.

## Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/domain/scanner/test_member_extractor.py -v
python -m mypy --strict src/hexrays_pytools/domain/scanner/member_extractor.py
python -m ruff check src/hexrays_pytools/domain/scanner/member_extractor.py tests/domain/scanner/test_member_extractor.py
```

## Commit

```bash
git add src/hexrays_pytools/domain/scanner/member_extractor.py tests/domain/scanner/test_member_extractor.py
git commit -m "feat(scanner): add SearchVisitor (main member extractor)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-2.7-report.md`