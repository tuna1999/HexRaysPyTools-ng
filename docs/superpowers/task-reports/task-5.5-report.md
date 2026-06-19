# Task 5.5 Report: domain/actions/recast_action.py

## Status: DONE

## Commit
- **SHA:** `1ee76a0`
- **Subject:** `feat(actions): add RecastItemLeft/Right action wrappers`

## Files (2)
| Path | Purpose |
|------|---------|
| `src/hexrays_pytools/domain/actions/recast_action.py` | `RecastItemLeft` + `RecastItemRight` wrappers wired to `recast_item_left` / `recast_item_right` |
| `tests/domain/actions/test_recast_action.py` | 3 unit tests |

## TDD Summary
- **RED:** Test file rewritten to the brief's content first (3 tests).
- **GREEN:** `recast_action.py` rewritten per the brief: `activate()` now extracts the hx_view via `ctx.widget` and calls the ctree function on `hx_view.item` when present.
- **REFACTOR:** One mechanical ruff I001 fix (import order) — see Deviations.

## Tests (3/3)
| Test | Purpose |
|------|---------|
| `test_recast_left_init` | `RecastItemLeft().hotkey == "Shift+L"` |
| `test_recast_left_check` | `check(None) is False`; `check(MagicMock()) is True` |
| `test_recast_right_init` | `RecastItemRight().hotkey == "Shift+R"` |

## Verification Gates
| Gate | Result |
|------|--------|
| `PYTHONPATH=src pytest tests/domain/actions/test_recast_action.py -v` | 3/3 passed |
| `mypy --strict src/hexrays_pytools/domain/actions/recast_action.py` | Success: no issues found in 1 source file |
| `ruff check recast_action.py test_recast_action.py` | All checks passed |

## Notes / Deviations

### 1. Import path adapted to actual package layout
The brief's source uses `from ..action import HexRaysPopupAction` and `from ..ctree.recast import ...`, but `action.py` lives in the same `actions/` package as `recast_action.py` (sibling), so the real import is `from .action import HexRaysPopupAction`. The `..ctree.recast` import is correct as-is (sibling package under `domain/`). Same mechanical-adaptation precedent as Tasks 5.1-5.4.

### 2. ruff `I001` — import order
Ruff requires first-party imports sorted with the parent-relative form first: `from ..ctree.recast import ...` precedes `from .action import HexRaysPopupAction`. Applied `ruff --fix` ordering.

### 3. Description string change
Brief sets `description = "Recast Item (Left)"` / `"Recast Item (Right)"` (was `"Recast Item"` in the prior stub). Followed the brief verbatim. Note: the registry + IDA menu will now show the parenthesized labels.

### 4. `RecastItemRight` no longer subclasses `RecastItemLeft`
The brief defines both classes as direct subclasses of `HexRaysPopupAction`. The prior stub had `RecastItemRight(RecastItemLeft)`. Followed the brief; both now carry their own `_get_hx_view` / `activate` / `check`.

### 5. `MagicMock` import added to test
The brief's test body references `MagicMock()` without an import. Added `from unittest.mock import MagicMock` per the batched brief's instruction ("Add MagicMock imports as needed").

## Notes for Downstream Tasks
- Tasks 5.6/5.7/5.8 follow the same wrapper pattern against their respective ctree functions.
