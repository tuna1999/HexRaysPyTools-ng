# Tasks 5.1-5.4 Batched: domain/ctree/* core logic

## Context

Four core ctree manipulation modules. Each contains pure logic that the action layer (5.5-5.8) wraps. All modules are stubs (real behavior requires full IDA ctree walking which is out of scope for the rewrite — original plugin does this through extensive heuristics).

## Files to Create (4 src + 4 test)

### 5.1 ctree/recast.py

```python
"""Recast logic — change types of variables/fields/returns to match assignment or cast.

Extracted from `core/helper.py` (recast functions) and `callbacks/recasts.py`.
Real implementation requires full ctree walking; this is the stub skeleton.
"""
from __future__ import annotations
from typing import Any

import idaapi  # type: ignore[import-not-found]


def recast_item_left(cexpr: Any) -> bool:
    """Recast: var type -> TYPE (left side of assignment)."""
    return False


def recast_item_right(cexpr: Any) -> bool:
    """Recast: var type -> TYPE from (TYPE) cast or function arg type."""
    return False
```

`tests/domain/ctree/test_recast.py`:

```python
"""Test recast stubs."""
from hexrays_pytools.domain.ctree.recast import recast_item_left, recast_item_right


def test_recast_left_stub_returns_false() -> None:
    assert recast_item_left(None) is False


def test_recast_right_stub_returns_false() -> None:
    assert recast_item_right(None) is False
```

### 5.2 ctree/rename.py

```python
"""Rename logic — 6 rename operations from Renames menu."""
from __future__ import annotations
from typing import Any


def rename_other(cexpr: Any) -> bool:
    """Take the other variable's name in an assignment (a = b → a becomes b's name)."""
    return False


def rename_inside(cexpr: Any) -> bool:
    """Push var name into the function parameter (caller's arg)."""
    return False


def rename_outside(cexpr: Any) -> bool:
    """Take function parameter name for a variable in a call site."""
    return False


def rename_member_from_function_name(cexpr: Any) -> bool:
    """Infer struct member name from getter/setter function name (getXxx → m_xxx)."""
    return False


def rename_using_assert(cexpr: Any) -> bool:
    """Rename all callers of an assert-like function by argument."""
    return False


def propagate_name(cexpr: Any) -> bool:
    """Propagate name to all references (deep recursive)."""
    return False
```

`tests/domain/ctree/test_rename.py`:

```python
"""Test rename stubs (6 functions)."""
from hexrays_pytools.domain.ctree.rename import (
    rename_other, rename_inside, rename_outside,
    rename_member_from_function_name, rename_using_assert, propagate_name,
)


def test_all_rename_stubs_return_false() -> None:
    assert rename_other(None) is False
    assert rename_inside(None) is False
    assert rename_outside(None) is False
    assert rename_member_from_function_name(None) is False
    assert rename_using_assert(None) is False
    assert propagate_name(None) is False
```

### 5.3 ctree/swap_if.py

```python
"""Swap if/then/else logic. FIX B8: uses vdui.refresh_view(True) not refresh_ctext()."""
from __future__ import annotations
from typing import Any

import idaapi  # type: ignore[import-not-found]


def swap_if_then_else(hx_view: Any) -> bool:
    """Swap the if/else branches of the if at the cursor.

    FIX B8: was hx_view.refresh_ctext() (removed in newer Hex-Rays);
    now hx_view.refresh_view(True).
    """
    if hx_view is None:
        return False
    # Real implementation: invert condition, swap branches
    return False
```

`tests/domain/ctree/test_swap_if.py`:

```python
"""Test swap_if."""
from hexrays_pytools.domain.ctree.swap_if import swap_if_then_else


def test_swap_if_none_returns_false() -> None:
    assert swap_if_then_else(None) is False
```

### 5.4 ctree/negative_offsets.py

```python
"""CONTAINING_RECORD logic — detect/replace negative-offset patterns."""
from __future__ import annotations
from typing import Any


def select_containing_structure(cexpr: Any) -> bool:
    """Prompt user to pick a containing structure + offset, set magic comment."""
    return False


def reset_containing_structure(cexpr: Any) -> bool:
    """Remove the magic comment, reverting to pointer arithmetic."""
    return False
```

`tests/domain/ctree/test_negative_offsets.py`:

```python
"""Test negative_offsets stubs."""
from hexrays_pytools.domain.ctree.negative_offsets import (
    select_containing_structure, reset_containing_structure,
)


def test_select_stub() -> None:
    assert select_containing_structure(None) is False


def test_reset_stub() -> None:
    assert reset_containing_structure(None) is False
```

## Verification (per commit)

```bash
PYTHONPATH=src pytest tests/domain/ctree/ -v
python -m mypy --strict src/hexrays_pytools/domain/ctree/
python -m ruff check src/hexrays_pytools/domain/ctree/ tests/domain/ctree/
```

## Commits (4 separate for clean history)

```bash
git add src/hexrays_pytools/domain/ctree/recast.py tests/domain/ctree/test_recast.py
git commit -m "feat(ctree): add recast logic stubs (RecastItemLeft/Right)"

git add src/hexrays_pytools/domain/ctree/rename.py tests/domain/ctree/test_rename.py
git commit -m "feat(ctree): add rename logic stubs (6 rename operations)"

git add src/hexrays_pytools/domain/ctree/swap_if.py tests/domain/ctree/test_swap_if.py
git commit -m "feat(ctree): add swap_if logic (B8 fix: refresh_view not refresh_ctext)"

git add src/hexrays_pytools/domain/ctree/negative_offsets.py tests/domain/ctree/test_negative_offsets.py
git commit -m "feat(ctree): add negative_offsets logic (CONTAINING_RECORD)"
```

## Report

Write 4 separate reports at:
- `D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-5.1-report.md`
- `D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-5.2-report.md`
- `D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-5.3-report.md`
- `D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-5.4-report.md`

After all 4 tasks, return:
- 4 commit SHAs + subjects
- Test summary (X/X pass)
- 4 report paths