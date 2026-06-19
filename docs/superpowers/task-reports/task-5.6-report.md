# Task 5.6 Report: domain/actions/rename_action.py

## Status: DONE

## Commit
- **SHA:** `5896963`
- **Subject:** `feat(actions): add 6 rename action wrappers (B10 verified)`

## Files (2)
| Path | Purpose |
|------|---------|
| `src/hexrays_pytools/domain/actions/rename_action.py` | 6 rename action classes via `_make_rename_action` factory, each wired to its ctree function |
| `tests/domain/actions/test_rename_action.py` | 3 unit tests incl. B10 hotkey-collision regression |

## TDD Summary
- **RED:** Test file rewritten to the brief's content (3 tests).
- **GREEN:** `rename_action.py` rewritten per the brief using the `_make_rename_action` factory; each class's `activate()` extracts `ctx.widget` and calls the wrapped ctree function on `hx_view.item`.
- **REFACTOR:** One mechanical mypy fix + ruff import-order fix (see Deviations).

## Tests (3/3)
| Test | Purpose |
|------|---------|
| `test_all_rename_classes_exist` | All 6 factory-built classes are importable |
| `test_b10_hotkey_collision_fix` | `RenameMemberFromFunctionName.hotkey == "Ctrl+Alt+N"` (not `Ctrl+N`) — regression guard |
| `test_all_rename_can_instantiate` | All 6 classes instantiate with no args |

## Verification Gates
| Gate | Result |
|------|--------|
| `PYTHONPATH=src pytest tests/domain/actions/test_rename_action.py -v` | 3/3 passed |
| `mypy --strict src/hexrays_pytools/domain/actions/rename_action.py` | Success: no issues found in 1 source file |
| `ruff check rename_action.py test_rename_action.py` | All checks passed |
| `PYTHONPATH=src pytest tests/domain/actions/` (full suite) | 88/88 passed |

## Notes / Deviations

### 1. Import path adapted to actual package layout
The brief uses `from ..action import HexRaysPopupAction` and `from ..ctree.rename import ...`. `action.py` is a sibling of `rename_action.py`, so the real import is `from .action import HexRaysPopupAction`; the `..ctree.rename` import is correct as written. Same adaptation precedent as Tasks 5.1-5.5.

### 2. mypy `arg-type` — `None` hotkey for `RenameUsingAssert`
The brief's factory signature is `hotkey: str`, but the brief itself calls it with `hotkey=None` for `RenameUsingAssert` (matching the base class `Action.hotkey: str | None`). Under `--strict` mypy rejected `Argument 3 ... has incompatible type "None"; expected "str"`. Widened the param to `hotkey: str | None` — a pure type annotation change, no behavioral effect; `None` was always the intended value.

### 3. ruff `I001` — import order (src + test)
Ruff alphabetized the `..ctree.rename` import list and ordered the test imports. Applied `ruff --fix`.

### 4. Factory preserves registry contract
The registry (`actions/registry.py`) and `test_registry.py` import the 6 classes by name. The factory sets `_RenameAction.__name__ = name`, so `type(action).__name__` (used by `Action.name`) returns the correct `"RenameOther"` etc. Full actions suite (88 tests) passes, confirming the registry still resolves all 6 classes.

### 5. Description strings differ from prior stub
The brief's descriptions (e.g. `"Take other name"`, `"Push var name into arg"`) replace the prior stub's wording. Followed the brief verbatim. B10 hotkey assignments unchanged from the prior stub and re-verified by `test_b10_hotkey_collision_fix`.

## Notes for Downstream Tasks
- Tasks 5.7/5.8 follow the same wrapper pattern (direct subclass, no factory needed for single-class files).
