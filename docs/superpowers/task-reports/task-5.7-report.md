# Task 5.7 Report: domain/actions/swap_if_action.py

## Status: DONE

## Commit
- **SHA:** `11d1693`
- **Subject:** `feat(actions): add SwapThenElse action wrapper`

## Files (2)
| Path | Purpose |
|------|---------|
| `src/hexrays_pytools/domain/actions/swap_if_action.py` | `SwapThenElse` wrapper wired to `swap_if_then_else` |
| `tests/domain/actions/test_swap_if_action.py` | 2 unit tests |

## TDD Summary
- **RED:** Test file rewritten to the brief's content (2 tests).
- **GREEN:** `swap_if_action.py` rewritten per the brief: `activate()` extracts `ctx.widget` and calls `swap_if_then_else(hx_view)` when present; `check()` returns `hx_view is not None`.
- **REFACTOR:** None required — passed all gates first try.

## Tests (2/2)
| Test | Purpose |
|------|---------|
| `test_swap_then_else_init` | `SwapThenElse().hotkey == "Shift+Alt+S"` |
| `test_swap_then_else_check` | `check(MagicMock()) is True` |

## Verification Gates
| Gate | Result |
|------|--------|
| `PYTHONPATH=src pytest tests/domain/actions/test_swap_if_action.py -v` | 2/2 passed |
| `mypy --strict src/hexrays_pytools/domain/actions/swap_if_action.py` | Success: no issues found in 1 source file |
| `ruff check swap_if_action.py test_swap_if_action.py` | All checks passed |

## Notes / Deviations

### 1. Import path adapted to actual package layout
The brief uses `from ..action import HexRaysPopupAction` and `from ..ctree.swap_if import ...`. `action.py` is a sibling, so the real import is `from .action import HexRaysPopupAction`; `..ctree.swap_if` is correct as written. Same adaptation precedent as Tasks 5.1-5.6.

### 2. `activate()` passes `hx_view`, not `hx_view.item`
Per the brief, `swap_if_then_else(hx_view)` is called with the view object (matching the ctree function's `swap_if_then_else(hx_view: Any)` signature and its B8 docstring note about `hx_view.refresh_view(True)`). This differs from the recast/rename actions, which pass `hx_view.item`. Followed the brief verbatim.

### 3. Description string change
Brief sets `description = "Swap if/then/else branches"` (was `"Swap then/else"` in the prior stub). Followed the brief verbatim.

### 4. `MagicMock` import added to test
The brief's test body references `MagicMock()` without an import. Added `from unittest.mock import MagicMock` per the batched brief's instruction.

## Notes for Downstream Tasks
- Task 5.8 (`containing_structure.py`) follows the same wrapper pattern for `SelectContainingStructure` / `ResetContainingStructure`.
