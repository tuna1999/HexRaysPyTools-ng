# Task 5.2 Report: domain/ctree/rename.py

## Status: DONE

## Commit
- **SHA:** `ac1d224`
- **Subject:** `feat(ctree): add rename logic stubs (6 rename operations)`

## Files (2)
| Path | Purpose |
|------|---------|
| `src/hexrays_pytools/domain/ctree/rename.py` | 6 rename stub functions |
| `tests/domain/ctree/test_rename.py` | 1 unit test exercising all 6 stubs |

## Functions (6)
| Function | Docstring intent |
|----------|------------------|
| `rename_other` | Take the other variable's name in an assignment (a = b → a becomes b's name) |
| `rename_inside` | Push var name into the function parameter (caller's arg) |
| `rename_outside` | Take function parameter name for a variable in a call site |
| `rename_member_from_function_name` | Infer struct member name from getter/setter (getXxx → m_xxx) |
| `rename_using_assert` | Rename all callers of an assert-like function by argument |
| `propagate_name` | Propagate name to all references (deep recursive) |

## TDD Summary
- **RED:** Wrote `test_rename.py` first; ran pytest -> `ModuleNotFoundError: No module named 'hexrays_pytools.domain.ctree.rename'`. Confirmed test fails before implementation exists.
- **GREEN:** Wrote `rename.py` per the brief. Test passes.
- **REFACTOR:** Applied mechanical ruff fixes (see Deviations). No functional deviation.

## Tests (1/1)
| Test | Purpose |
|------|---------|
| `test_all_rename_stubs_return_false` | All 6 functions return `False` for `None` input |

## Verification Gates
| Gate | Result |
|------|--------|
| `PYTHONPATH=src pytest tests/domain/ctree/test_rename.py -v` | 1/1 passed |
| `mypy --strict src/hexrays_pytools/domain/ctree/rename.py` | Success: no issues found in 1 source file |
| `ruff check src/hexrays_pytools/domain/ctree/rename.py tests/domain/ctree/test_rename.py` | All checks passed |

## Notes / Deviations

### 1. ruff `I001` — import block formatting (both files)

The brief's verbatim source triggers `I001` (import block un-sorted / un-formatted) in both files:

- **`rename.py`:** `from __future__ import annotations` immediately followed by `from typing import Any` with no blank line. Ruff's isort requires a blank line separating the `__future__` block from the third-party/stdlib block. Added the blank line.

- **`test_rename.py`:** The brief's multi-name import is packed three-per-line with trailing commas:
  ```python
  from hexrays_pytools.domain.ctree.rename import (
      rename_other, rename_inside, rename_outside,
      rename_member_from_function_name, rename_using_assert, propagate_name,
  )
  ```
  Ruff's isort (magic-trailing-comma) reformats to one-name-per-line, alphabetically sorted. Applied the reformat. The test *body* still asserts in the original semantic order (other, inside, outside, member_from_function_name, using_assert, propagate) — only the import block order changed, which has no behavioral effect.

This matches the same mechanical-cleanup pattern as Tasks 4.3, 4.5, and 5.1.

## Notes for Downstream Tasks
- **Task 5.6 (actions/rename_action.py):** The 6 rename action classes (`RenameOther`, `RenameInside`, `RenameOutside`, `RenameMemberFromFunctionName`, `RenameUsingAssert`, `PropagateName`) currently have `activate() -> pass`. Once these stubs grow real bodies, wire each action's `activate()` to the matching `rename_*` function here. The 1:1 name mapping is already established.
- **B10 note carried forward:** `RenameMemberFromFunctionName` action uses hotkey `Ctrl+Alt+N` (not `Ctrl+N`, taken by `RenameOther`). The `rename_member_from_function_name` logic function here is hotkey-agnostic; the B10 fix lives entirely in the action layer.
