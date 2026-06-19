# Task 2.4 Brief: domain/scanner/visitor_base.py

## Files

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\scanner\__init__.py` (empty)
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\scanner\visitor_base.py`
3. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\scanner\__init__.py` (empty)
4. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\scanner\test_visitor_base.py`

## Content (verbatim)

### `src/hexrays_pytools/domain/scanner/visitor_base.py`

```python
"""ctree visitor base classes for struct reconstruction.

Extracted from the original `api.py`. Provides ctree_parentee_t subclasses
that traverse a decompiled function and extract struct member candidates.
"""
from __future__ import annotations
import idaapi  # type: ignore[import-not-found]


class ObjectVisitor(idaapi.ctree_parentee_t):  # type: ignore[misc]
    """Base visitor: walk a cfunc and collect objects matching criteria.

    Subclasses override `_manipulate(cexpr, obj)` to react to expressions.
    The `_objects` list accumulates matched items.
    """
    def __init__(self, cfunc: idaapi.cfunc_t) -> None:  # type: ignore[name-defined]
        super().__init__()
        self._cfunc = cfunc
        self._objects: list = []
        self._init_obj: object | None = None
        self._start_ea: int = 0
        self._skip: bool = False
        self._data: object | None = None

    def process(self) -> None:
        """Run the visitor over the cfunc body."""
        self.apply_to(self._cfunc.body, None)

    @property
    def objects(self) -> list:
        """The list of objects found during traversal."""
        return list(self._objects)

    def _manipulate(self, cexpr: idaapi.cexpr_t, obj: object) -> None:  # type: ignore[name-defined]
        raise NotImplementedError("Subclasses must implement _manipulate")
```

### `tests/domain/scanner/test_visitor_base.py`

```python
"""Test ObjectVisitor."""
from hexrays_pytools.domain.scanner.visitor_base import ObjectVisitor


def test_visitor_process_calls_apply_to() -> None:
    """process() calls apply_to on the cfunc body."""
    idaapi = __import__("idaapi")
    cfunc = MagicMock()
    cfunc.body = "fake_body"
    v = ObjectVisitor(cfunc)
    v.process()
    v.apply_to.assert_called_with("fake_body", None)


def test_visitor_objects_initially_empty() -> None:
    """A new visitor has no objects."""
    idaapi = __import__("idaapi")
    cfunc = MagicMock()
    v = ObjectVisitor(cfunc)
    assert v.objects == []


def test_visitor_subclass_must_implement_manipulate() -> None:
    """ObjectVisitor._manipulate raises NotImplementedError."""
    idaapi = __import__("idaapi")
    cfunc = MagicMock()
    v = ObjectVisitor(cfunc)
    try:
        v._manipulate("expr", "obj")
        assert False, "should have raised"
    except NotImplementedError:
        pass
```

Add `from unittest.mock import MagicMock` to imports.

## Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/domain/scanner/test_visitor_base.py -v
python -m mypy --strict src/hexrays_pytools/domain/scanner/visitor_base.py
python -m ruff check src/hexrays_pytools/domain/scanner/ tests/domain/scanner/
```

## Commit

```bash
git add src/hexrays_pytools/domain/scanner/ tests/domain/scanner/
git commit -m "feat(scanner): add ObjectVisitor base (ctree_parentee_t)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-2.4-report.md`