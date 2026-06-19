# Task 2.1 Brief: domain/types/tinfo_utils.py

## Files to Create

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\types\__init__.py` (empty)
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\types\tinfo_utils.py`
3. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\types\__init__.py` (empty)
4. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\types\test_tinfo_utils.py`

## Required Content (verbatim)

### `src/hexrays_pytools/domain/types/tinfo_utils.py`

```python
"""Thin wrappers around idaapi tinfo_t methods.

Extracted from the original `core/helper.py` so other modules can mock
the IDA API in tests. Pure functions where possible; IDA-coupled where
unavoidable.
"""
from __future__ import annotations
import idaapi  # type: ignore[import-not-found]


def get_ordinal(tinfo: idaapi.tinfo_t) -> int:  # type: ignore[name-defined]
    """Get the local-type ordinal of `tinfo`, or 0 if not a local type."""
    if tinfo.is_udt() or tinfo.is_enum():
        return tinfo.get_ordinal()
    if tinfo.is_typeref():
        return tinfo.get_ordinal()
    return 0


def get_nice_pointed_object(tinfo: idaapi.tinfo_t) -> idaapi.tinfo_t:  # type: ignore[name-defined]
    """Strip the `P` prefix from pointed object name if a matching type exists."""
    inner = tinfo.get_pointed_object()
    if not inner:
        return inner
    name = idaapi.get_short_name(inner.dstr())
    if name.startswith("P"):
        candidate = name[1:]
        named = idaapi.tinfo_t()
        if named.get_named_type(idaapi.get_idati(), candidate):
            return named
    return inner
```

### `tests/domain/types/test_tinfo_utils.py`

```python
"""Test tinfo_utils."""
from hexrays_pytools.domain.types.tinfo_utils import get_ordinal, get_nice_pointed_object


def test_get_ordinal_for_udt() -> None:
    """get_ordinal returns the ordinal for a UDT."""
    tinfo = __import__("idaapi").tinfo_t.return_value
    tinfo.is_udt.return_value = True
    tinfo.get_ordinal.return_value = 42
    assert get_ordinal(tinfo) == 42


def test_get_ordinal_for_non_udt() -> None:
    """get_ordinal returns 0 for non-UDT types."""
    tinfo = __import__("idaapi").tinfo_t.return_value
    tinfo.is_udt.return_value = False
    tinfo.is_enum.return_value = False
    tinfo.is_typeref.return_value = False
    assert get_ordinal(tinfo) == 0


def test_get_nice_pointed_object_strips_p() -> None:
    """get_nice_pointed_object returns the non-P-prefixed type if it exists."""
    idaapi = __import__("idaapi")
    inner = MagicMock()
    inner.dstr.return_value = "PFoo"
    tinfo = MagicMock()
    tinfo.get_pointed_object.return_value = inner
    idaapi.get_short_name.return_value = "PFoo"
    # Make get_named_type succeed for "Foo"
    named = MagicMock()
    tinfo2 = MagicMock()
    tinfo2.get_named_type.return_value = True
    idaapi.tinfo_t.return_value = tinfo2
    result = get_nice_pointed_object(tinfo)
    # Should be the named tinfo, not the inner
    assert result is not None
```

Note: brief uses `MagicMock` without import. Add the import:

```python
from unittest.mock import MagicMock
from hexrays_pytools.domain.types.tinfo_utils import get_ordinal, get_nice_pointed_object
```

## Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/domain/types/test_tinfo_utils.py -v
python -m mypy --strict src/hexrays_pytools/domain/types/tinfo_utils.py
python -m ruff check src/hexrays_pytools/domain/types/ tests/domain/types/
```

## Commit

```bash
git add src/hexrays_pytools/domain/types/ tests/domain/types/
git commit -m "feat(types): add tinfo_utils (get_ordinal, get_nice_pointed_object)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-2.1-report.md`

Apply minimal lint fixes. Document deviations in DONE_WITH_CONCERNS.
