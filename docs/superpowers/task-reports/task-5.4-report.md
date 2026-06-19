# Task 5.4 Report: domain/ctree/negative_offsets.py

## Status: DONE

## Commit
- **SHA:** `dd77a36`
- **Subject:** `feat(ctree): add negative_offsets logic (CONTAINING_RECORD)`

## Files (2)
| Path | Purpose |
|------|---------|
| `src/hexrays_pytools/domain/ctree/negative_offsets.py` | `select_containing_structure`, `reset_containing_structure` stubs |
| `tests/domain/ctree/test_negative_offsets.py` | 2 unit tests |

## Functions (2)
| Function | Docstring intent |
|----------|------------------|
| `select_containing_structure` | Prompt user to pick a containing structure + offset, set magic comment |
| `reset_containing_structure` | Remove the magic comment, reverting to pointer arithmetic |

## TDD Summary
- **RED:** Wrote `test_negative_offsets.py` first; ran pytest -> `ModuleNotFoundError: No module named 'hexrays_pytools.domain.ctree.negative_offsets'`. Confirmed test fails before implementation exists.
- **GREEN:** Wrote `negative_offsets.py` per the brief. Both tests pass.
- **REFACTOR:** Applied mechanical ruff fixes (see Deviations). No functional deviation.

## Tests (2/2)
| Test | Purpose |
|------|---------|
| `test_select_stub` | `select_containing_structure(None) is False` |
| `test_reset_stub` | `reset_containing_structure(None) is False` |

## Verification Gates
| Gate | Result |
|------|--------|
| `PYTHONPATH=src pytest tests/domain/ctree/test_negative_offsets.py -v` | 2/2 passed |
| `mypy --strict src/hexrays_pytools/domain/ctree/negative_offsets.py` | Success: no issues found in 1 source file |
| `ruff check src/hexrays_pytools/domain/ctree/negative_offsets.py tests/domain/ctree/test_negative_offsets.py` | All checks passed |
| `pytest tests/domain/ctree/` (folder, all 4 tasks) | 6/6 passed |
| `mypy --strict src/hexrays_pytools/domain/ctree/` (folder) | Success: no issues found in 5 source files |
| `ruff check src/hexrays_pytools/domain/ctree/ tests/domain/ctree/` (folder) | All checks passed |
| Full suite regression | **281 passed** (was 275 baseline; +6 new ctree tests) |
| Project coverage | **88.28%** (gate: ≥80%) |

## Notes / Deviations

### 1. ruff `I001` — import block formatting (both files)

Identical to Task 5.2. The brief's verbatim source triggers `I001` in both files:

- **`negative_offsets.py`:** Missing blank line between `from __future__ import annotations` and `from typing import Any`. Added.
- **`test_negative_offsets.py`:** Two-name import packed on one line with trailing comma:
  ```python
  from hexrays_pytools.domain.ctree.negative_offsets import (
      select_containing_structure, reset_containing_structure,
  )
  ```
  Ruff's isort (magic-trailing-comma) reformats to one-name-per-line, alphabetically sorted (`reset_containing_structure` before `select_containing_structure`). Applied. The test *body* still calls `select_containing_structure` first then `reset_containing_structure` in separate test functions — only the import block order changed, no behavioral effect.

Same mechanical-cleanup precedent as Tasks 4.3, 4.5, 5.1, 5.2, 5.3.

## Coverage Note

All 4 new ctree modules at **100%** except `swap_if.py` at **83%** (line 16 — the `return False` after the `None` guard, reachable only with a non-None `hx_view`; the single test passes `None`, exercising the guard). This is expected for a stub and will close automatically once Task 5.3's real branch-swap logic lands and a non-None `hx_view` test is added.

## Phase 5 ctree package — final state

The `domain/ctree/` package now contains all 4 logic modules from this batch:

| Module | Functions | Tests |
|--------|-----------|-------|
| `recast.py` | 2 (`recast_item_left`, `recast_item_right`) | 2 |
| `rename.py` | 6 (`rename_other`, `rename_inside`, `rename_outside`, `rename_member_from_function_name`, `rename_using_assert`, `propagate_name`) | 1 |
| `swap_if.py` | 1 (`swap_if_then_else`) | 1 |
| `negative_offsets.py` | 2 (`select_containing_structure`, `reset_containing_structure`) | 2 |
| **Total** | **11 functions** | **6 tests** |

All return `False` unconditionally (stubs). The action layer (Tasks 5.5-5.8) wraps these; the real ctree-walking implementations are deferred per the brief.

## Notes for Downstream Tasks
- **Task 5.8 (actions/containing_structure.py):** `SelectContainingStructure.activate()` and `ResetContainingStructure.activate()` are currently `pass`. Wire them to `select_containing_structure(cexpr)` / `reset_containing_structure(cexpr)` and propagate the bool return.
- **Task 5.9 (Phase 5 gate):** The gate should add one integration test wiring an action from 5.5-5.8 to its ctree logic function here, exercising the dispatch path end-to-end (action.activate -> ctree function -> bool return). All building blocks are in place after 5.5-5.8 land.
