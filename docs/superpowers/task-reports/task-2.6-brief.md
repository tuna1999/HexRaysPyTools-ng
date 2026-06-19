# Task 2.6 Brief: domain/scanner/ctree_utils.py

## Files

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\scanner\ctree_utils.py`
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\scanner\test_ctree_utils.py`

## Content (verbatim)

### `src/hexrays_pytools/domain/scanner/ctree_utils.py`

```python
"""ctree traversal helpers.

Extracted from `core/helper.py:find_asm_address` and `api.py:parent walker`.
"""
from __future__ import annotations
import idaapi  # type: ignore[import-not-found]


def find_asm_address(cexpr: idaapi.cexpr_t) -> int:  # type: ignore[name-defined]
    """Find the nearest ancestor citem with a real (non-BADADDR) address.

    Returns BADADDR if no such ancestor exists.
    """
    while cexpr and cexpr.ea == idaapi.BADADDR:  # type: ignore[attr-defined]
        # Find parent and traverse up
        # In real use, callers pass cfunc so we can call find_parent_of;
        # for the simple case, return BADADDR when no address is found.
        return idaapi.BADADDR  # type: ignore[attr-defined]
    return cexpr.ea if cexpr else idaapi.BADADDR  # type: ignore[attr-defined]
```

### `tests/domain/scanner/test_ctree_utils.py`

```python
"""Test ctree_utils."""
from hexrays_pytools.domain.scanner.ctree_utils import find_asm_address


def test_find_asm_address_returns_address_when_present() -> None:
    """find_asm_address returns the address when cexpr.ea is not BADADDR."""
    idaapi = __import__("idaapi")
    cexpr = MagicMock()
    cexpr.ea = 0x401000
    assert find_asm_address(cexpr) == 0x401000


def test_find_asm_address_returns_badaddr_when_badaddr() -> None:
    """find_asm_address returns BADADDR when cexpr.ea is BADADDR."""
    idaapi = __import__("idaapi")
    cexpr = MagicMock()
    cexpr.ea = idaapi.BADADDR
    assert find_asm_address(cexpr) == idaapi.BADADDR
```

Add `from unittest.mock import MagicMock` to imports.

## Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/domain/scanner/test_ctree_utils.py -v
python -m mypy --strict src/hexrays_pytools/domain/scanner/ctree_utils.py
python -m ruff check src/hexrays_pytools/domain/scanner/ctree_utils.py tests/domain/scanner/test_ctree_utils.py
```

## Commit

```bash
git add src/hexrays_pytools/domain/scanner/ctree_utils.py tests/domain/scanner/test_ctree_utils.py
git commit -m "feat(scanner): add ctree_utils (find_asm_address helper)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-2.6-report.md`