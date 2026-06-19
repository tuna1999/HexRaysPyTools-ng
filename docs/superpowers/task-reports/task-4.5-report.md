# Task 4.5 Report: 27 action classes across 13 files

## Status: DONE

## Commit
- **SHA:** `b4571a3`
- **Subject:** `feat(actions): add 27 action classes across 13 files`

## Files (28)
13 new source files + 13 new test files, plus 2 modified (registry.py, test_registry.py).

### Source files (13)
| # | Path | Classes | Count |
|---|------|---------|-------|
| 1 | `src/hexrays_pytools/domain/actions/form_requests.py` | ShowGraph, ShowClasses, ShowStructureBuilder | 3 |
| 2 | `src/hexrays_pytools/domain/actions/function_signature.py` | ConvertToUsercall, AddRemoveReturn, RemoveArgument | 3 |
| 3 | `src/hexrays_pytools/domain/actions/scanners.py` | ShallowScanVariable, DeepScanVariable, RecognizeShape, DeepScanReturn, DeepScanFunctions | 5 |
| 4 | `src/hexrays_pytools/domain/actions/struct_xref.py` | FindFieldXrefs | 1 |
| 5 | `src/hexrays_pytools/domain/actions/struct_creation.py` | CreateNewField, CreateVtable | 2 |
| 6 | `src/hexrays_pytools/domain/actions/structs_by_size.py` | GetStructureBySize | 1 |
| 7 | `src/hexrays_pytools/domain/actions/guess_allocation.py` | GuessAllocation | 1 |
| 8 | `src/hexrays_pytools/domain/actions/swap_if_action.py` | SwapThenElse | 1 |
| 9 | `src/hexrays_pytools/domain/actions/recast_action.py` | RecastItemLeft, RecastItemRight | 2 |
| 10 | `src/hexrays_pytools/domain/actions/rename_action.py` | RenameOther, RenameInside, RenameOutside, RenameMemberFromFunctionName, RenameUsingAssert, PropagateName | 6 |
| 11 | `src/hexrays_pytools/domain/actions/containing_structure.py` | SelectContainingStructure, ResetContainingStructure | 2 |
| 12 | `src/hexrays_pytools/domain/actions/member_double_click.py` | MemberDoubleClickAction | 1 |
| 13 | `src/hexrays_pytools/domain/actions/virtual_table.py` | CreateVtableAction | 1 |

**Total: 29 classes across 13 files.** Of these, **27 are registered** in `ActionRegistry.ACTION_CLASSES` (imported from files 1-11); the 2 in files 12-13 are out-of-registry extras (see Notes section 4).

### Test files (13)
One test file per source file, named `test_<module>.py`, covering: subclass relationship to the correct base (`Action` / `HexRaysPopupAction` / `HexRaysXrefAction`), `description` / `hotkey` class attributes, instantiation + `name` property format, `activate()` / `check()` do not raise, and session injection.

### Modified files (2)
| Path | Change |
|------|--------|
| `src/hexrays_pytools/domain/actions/registry.py` | Removed 11 `# type: ignore[import-untyped]` comments (now-unused — modules exist) + updated the explanatory comment block. Predicted by the Task 4.2 report. |
| `tests/domain/actions/test_registry.py` | Added 2 real-path integration tests (`test_registry_build_actions_real_path_returns_27`, `test_registry_build_actions_b10_fix_hotkey`) that exercise the previously-deferred real lazy-import path. |

## TDD Summary
- **RED:** Wrote all 13 test files first; ran pytest per file -> `ModuleNotFoundError` for each missing source module. Confirmed tests fail before implementation exists.
- **GREEN:** Wrote all 13 source files. All 96 actions tests pass.
- **REFACTOR:** Applied mechanical fixes required by the brief's "mypy/ruff clean" gate (see Deviations).

## Test Summary
| Scope | Count |
|-------|-------|
| New action tests (13 files) | 87 |
| New registry integration tests | 2 |
| Pre-existing actions tests (action, hx_callback, hx_events, registry) | 7 |
| **Total in `tests/domain/actions/`** | **96/96 passed** |
| Full suite regression | **273 passed** (was 203 after Task 4.4; +70 new) |

## Verification Gates
| Gate | Result |
|------|--------|
| `pytest tests/domain/actions/` (folder) | 96/96 passed |
| `mypy --strict src/hexrays_pytools/domain/actions/` | Success: no issues found (18 files) |
| `ruff check src/hexrays_pytools/domain/actions/ tests/domain/actions/` | All checks passed |
| Full suite regression | 273 passed |
| Project coverage | 87.22% (gate: ≥80%) |
| `ActionRegistry._build_actions()` real path | Returns 27 instances, spec order verified |

## Coverage

All 13 new action source files at **100%**. Pre-existing files in the dir:
- `action.py`: 81% (base-class `update()` branches not all hit)
- `hx_callback.py`: 93% (Task 4.3)
- `registry.py`: **95%** (up from 57% in Task 4.2 — the real `_build_actions` path is now exercised; uncovered: the warning branch at line 127 when count != 27, and the popup-handler debug log at line 142)

## Notes / Deviations

The brief's "verbatim" source did not satisfy the `mypy --strict` / `ruff check` / runtime import gates as-is. Fixes below are mechanical; no functional deviation from the brief's intent.

### 1. CRITICAL: Wrong relative import depth (`from ..action` -> `from .action`)

The brief's sample pattern uses `from ..action import Action, HexRaysPopupAction` and `from ...session import Session`. This is **wrong** for modules inside `domain/actions/`: `action.py` and `session` are reached with **one fewer dot**:
- `from ..action import` resolves to `hexrays_pytools.domain.action` (does not exist) -> `ModuleNotFoundError` at runtime.
- Correct: `from .action import` (sibling module within `actions/`).
- Likewise `from ...session import` -> `from ..session import` (`session.py` is in the parent `domain/` package).

Confirmed at runtime: `python -c "from hexrays_pytools.domain.actions.form_requests import ShowGraph"` raised `ModuleNotFoundError: No module named 'hexrays_pytools.domain.action'`. Fixed in all 13 files. This matches the import style already used in `registry.py` (`from .action import HexRaysPopupAction`).

### 2. mypy `[assignment]` on `Scanner.hotkey`

The brief's pattern sets `hotkey = None` in the `Scanner` base class. mypy infers the attribute type as `None`, so subclasses assigning `hotkey = "F"` trigger `[assignment]` (incompatible: `str` vs `None`). Fixed by annotating the base explicitly: `hotkey: str | None = None`. This matches the parent `Action.hotkey: str | None = None` declaration in `action.py`.

### 3. registry.py: 11 now-unused `[import-untyped]` ignores removed

Task 4.2's report explicitly stated: *"Once the 11 action modules are created with a `py.typed` marker, remove the 11 `# type: ignore[import-untyped]` comments... Under `warn_unused_ignores = true`, leaving them will fail mypy."* That prediction materialized exactly: with the modules present, mypy reported `[unused-ignore]` for all 11. Removed them and refreshed the explanatory comment block. No behavior change.

### 4. Two out-of-registry extra files (member_double_click.py, virtual_table.py)

The brief lists 13 files but the `ActionRegistry` (Task 4.2, committed) only imports from 11 of them. The 2 extras:

- **`member_double_click.py`** — `MemberDoubleClickAction` (a `HexRaysPopupAction`). The actual `hxe_double_click` logic lives in the `MemberDoubleClick` **event handler** in `hx_events.py` (Task 4.4), which is registered via `HxCallbackManager`, not the action registry. This action class is a hotkey-triggered wrapper retained per the brief's file list; it is **not** in `ACTION_CLASSES`. Documented in the module docstring.
- **`virtual_table.py`** — `CreateVtableAction` (an `Action`). The registered class is `CreateVtable` in `struct_creation.py` (per the registry). The design spec §6.1 row 21 maps `CreateVtable` to `actions/virtual_table.py`, but the implemented registry imports it from `struct_creation.py`. This `CreateVtableAction` is a naming-parity alias retained per the brief's file list; it is **not** in `ACTION_CLASSES`. Documented in the module docstring.

This reconciles the brief's "27 actions total" (the registered count) with the 29 classes across 13 files (27 registered + 2 extras). Both extras are fully tested.

### 5. B10 fix verified end-to-end

`RenameMemberFromFunctionName.hotkey = "Ctrl+Alt+N"` (not `Ctrl+N`, which collides with `RenameOther`). Verified at three layers:
1. Class attribute (test_rename_action.py::test_rename_member_from_function_name_b10_fix)
2. Registry build output (test_registry.py::test_registry_build_actions_b10_fix_hotkey)
3. Direct instantiation script

### 6. ruff `N802` — test function names with uppercase letters

Initial test names like `test_rename_other_hotkey_ctrl_N` and `test_shallow_scan_variable_hotkey_F` violated `N802` (function names must be lowercase). Renamed to lowercase (`..._ctrl_n`, `..._hotkey_f`, etc.). The assertions inside still check the exact uppercase hotkey strings (`"Ctrl+N"`, `"F"`).

## Notes for Downstream Tasks

- **Task 4.6 (Phase 4 gate):** The full action subsystem now exists and is unit-tested. The gate should add one integration test wiring `ActionRegistry.register_all` + `HxCallbackManager.install` + a real event handler from Task 4.4, exercising the dispatch path end-to-end. All building blocks are in place.
- **Phase 5 (ctree logic):** Every action's `activate()` is currently a `pass` stub. Real ctree-scanning / renaming / recasting logic lands in Phase 5 (`ctree/*.py` per the design spec); the action classes here are the registration shell. The `check()` methods uniformly return `True` for now — real visibility logic also lands in Phase 5.
- **Design spec vs registry drift:** `CreateVtable` lives in `struct_creation.py` (registry) but the spec maps it to `virtual_table.py`. Either move the class in Phase 5 or update the spec; current state is internally consistent (registry imports what exists).
