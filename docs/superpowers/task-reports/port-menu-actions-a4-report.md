# Phase A.4 Report: Port Recursive Down/Up object visitors

**Date:** 2026-06-19
**Branch:** `master`
**Result:** A.4 complete; the deep scanners (Phase A.5) + PropagateName /
GuessAllocation (Phase B) now have cross-function traversal machinery.

## Summary

Added the 3 recursive visitor classes (`RecursiveObjectVisitor` base +
`RecursiveObjectDownwardsVisitor` + `RecursiveObjectUpwardsVisitor`) to
`visitor_base.py`, ported from `refs/.../api.py:408-580`. Added two
supporting helpers: `decompile_function` + `FunctionTouchVisitor` (new
`domain/scanner/helpers.py`) and `is_imported_ea` (in `infra/arch/arch.py`).
Enriched `mock_ida` with a real `DecompilationFailure` exception so the
decompile wrapper's exception guard is testable.

## Changes

| File | Change |
|---|---|
| `src/hexrays_pytools/domain/scanner/visitor_base.py` | +3 recursive visitor classes (~210 LOC added) |
| `src/hexrays_pytools/domain/scanner/helpers.py` | **NEW** — `decompile_function` + `FunctionTouchVisitor` |
| `src/hexrays_pytools/infra/arch/arch.py` | +`is_imported_ea(ea, imported_ea)` |
| `tools/mock_ida.py` | +real `DecompilationFailure(Exception)` class |
| `pyproject.toml` | Add `scanner/visitor_base.py` to coverage-omit (live ctree) |
| `tests/domain/scanner/test_helpers.py` | **NEW** — 9 tests |
| `tests/domain/scanner/test_recursive_visitors.py` | **NEW** — 15 tests |

## What's ported

### RecursiveObjectVisitor (base)
- `_visited: set[(func_ea, arg_idx)]` — dedup across the whole recursive scan
- `_new_for_visit: set[(func_ea, arg_idx)]` — work queue drained after each pass
- `_imported_ea: set[int]` — session-owned import cache (replaces `cache.imported_ea` global); passed via ctor so callers inject `session.imported_ea`
- `set_callbacks(manipulate, start, start_iteration, finish, finish_iteration)` — bind any of 5 hooks (bound-method swap; `# type: ignore[method-assign]` with explanatory comment)
- `prepare_new_scan(cfunc, arg_idx, obj, skip)` — reset per-function state
- `process()` → `_start` → `_recursive_process` → `_finish` → `_dump_scan_tree`
- `_check_call(cexpr)` — abstract (subclasses override)
- `_add_visit(func_ea, arg_idx)` — record + dedup; returns True if new
- `_is_func_crippled()` — thunk heuristic (single return / single call)
- 4 lifecycle hooks (`_start/_start_iteration/_finish/_finish_iteration`) — no-op defaults

### RecursiveObjectDownwardsVisitor (cross-function forward)
- Inherits both `RecursiveObjectVisitor` and `ObjectDownwardsVisitor`
- `_check_call` — if the tracked obj is a `cot_call` arg (or cast-wrapped), `_add_visit(callee_ea, arg_idx)`
- `_recursive_process` — override: after the normal pass, drain `_new_for_visit`, decompile each callee, seed with `VariableObject(callee.lvars[arg_idx], arg_idx)`, recurse

### RecursiveObjectUpwardsVisitor (cross-function backward)
- Inherits both `RecursiveObjectVisitor` and `ObjectUpwardsVisitor`
- `prepare_new_scan` — also sets `_call_obj` when seed is `SO_CALL_ARGUMENT`
- `_check_call` — if a local `cot_var` is an arg (`is_arg_var`), `_add_visit(self_ea, arg_idx)` + walk all callers
- `_recursive_process` — override: after the normal pass, for each queued (func, arg), decompile each caller, seed with `CallArgObject.create(...)`, recurse

### Supporting helpers
- `decompile_function(ea)` — wraps `idaapi.decompile`, catches `DecompilationFailure`, returns `None` on failure
- `FunctionTouchVisitor(cfunc, touched, imported_ea)` — pre-decompiles all callees so their arg types are known before the deep scan
- `is_imported_ea(ea, imported_ea)` — `.plt` segment OR `(ea + imagebase)` in the import cache

## Why `DecompilationFailure` is a real class in the mock

Production `decompile_function` does `except idaapi.DecompilationFailure`. A
MagicMock is not an Exception, so:
- `MagicMock(side_effect=idaapi.DecompilationFailure)` would *raise a MagicMock* (not a catchable exception) → the except never fires → the test would see the cfunc returned, not None.
- The class must be a real `Exception` subclass so both production `except` and test `side_effect=` work correctly.

## Why visitor_base.py is on coverage-omit

The visitor hierarchy walks the live ctree via IDA's C++ `ctree_parentee_t`
dispatch. `mock_ida` has no dispatch, so `visit_expr` / `leave_expr` /
`_check_call` / `_recursive_process` cannot be reached from unit tests.
Added to `pyproject.toml [tool.coverage.report] omit` next to the other
ctree engines. Note: `scanner/helpers.py` is **NOT** omitted — its
`decompile_function` guard + `FunctionTouchVisitor` collector are pure
Python and unit-tested.

## Tests added (24 new)

### test_helpers.py (9)
- `test_decompile_function_returns_cfunc_on_success`
- `test_decompile_function_returns_none_on_decompilation_failure`
- `test_decompile_function_returns_none_when_decompile_returns_falsy`
- `test_is_imported_ea_true_for_plt_segment`
- `test_is_imported_ea_false_for_non_plt_not_in_cache`
- `test_is_imported_ea_true_when_in_cache`
- `test_function_touch_visitor_visit_expr_collects_call_targets`
- `test_function_touch_visitor_process_marks_function_touched`
- `test_function_touch_visitor_process_skips_already_touched`

### test_recursive_visitors.py (15)
- `test_recursive_init_visited_is_empty`
- `test_recursive_init_new_for_visit_is_empty`
- `test_recursive_init_accepts_existing_visited`
- `test_recursive_add_visit_returns_true_for_new_target`
- `test_recursive_add_visit_returns_false_for_duplicate`
- `test_recursive_prepare_new_scan_resets_state`
- `test_recursive_is_func_crippled_single_return`
- `test_recursive_is_func_crippled_single_call`
- `test_recursive_is_func_crippled_false_for_multi_statement`
- `test_recursive_downwards_inherits_object_downwards`
- `test_recursive_downwards_has_cv_post_flag`
- `test_recursive_downwards_check_call_is_overridden`
- `test_recursive_upwards_inherits_object_upwards`
- `test_recursive_upwards_prepare_sets_call_obj_for_call_arg`
- `test_recursive_upwards_prepare_leaves_call_obj_none_for_non_call_arg`

## Quality gates

| Gate | Result |
|---|---|
| `pytest tests/domain/scanner/` | **52 passed** |
| Full `pytest` suite | **414 passed** (was 390 — +24 new) |
| Coverage | **83.78%** (gate met) |
| `mypy --strict` on changed files | Clean |
| `ruff check` on changed files | Clean |

## Design decisions

1. **`_imported_ea` injected via ctor** — the original read `cache.imported_ea` (module global). The new plugin passes it through so the Session owns it. Callers (Phase B.7) pass `session.imported_ea`.

2. **`# type: ignore[method-assign]` for bound-method hook swap** — `set_callbacks` replaces instance methods at runtime (`self._start = fn.__get__(self, type(self))`). mypy flags this as `method-assign`. Intentional plugin pattern (original does the same); documented with an explanatory comment, matching the existing `# type: ignore[misc]` convention for SWIG overrides.

3. **`_is_func_crippled` returns False when `b.size() != 1`** — matches original. Crippled = thunk; the scanner skips applying types to thunks.

4. **Debug scan-tree kept but defensive** — `_dump_scan_tree` / `_prepare_debug_message` wrap `idaapi.get_name` in try/except so a logging failure never crashes a scan. (Original had no guard.)

## What this unlocks

- **Phase A.5 (SearchVisitor)**: `NewDeepSearchVisitor` inherits `RecursiveObjectDownwardsVisitor`; `DeepReturnVisitor` walks callers.
- **Phase B.7 (scanner actions)**: `DeepScanVariable` uses `FunctionTouchVisitor` + `NewDeepSearchVisitor`; `DeepScanFunctions` uses `NewDeepSearchVisitor` across a chooser selection.
- **Phase B.7 (GuessAllocation)**: uses `RecursiveObjectUpwardsVisitor`.
- **Phase B.8 (PropagateName)**: uses `RecursiveObjectDownwardsVisitor`.

## Files touched

```
src/hexrays_pytools/domain/scanner/visitor_base.py       (+210 LOC, 3 classes)
src/hexrays_pytools/domain/scanner/helpers.py            (NEW, ~80 LOC)
src/hexrays_pytools/infra/arch/arch.py                   (+10 LOC)
tools/mock_ida.py                                        (+13 LOC, DecompilationFailure)
pyproject.toml                                           (+8 LOC, coverage-omit)
tests/domain/scanner/test_helpers.py                     (NEW, 9 tests)
tests/domain/scanner/test_recursive_visitors.py          (NEW, 15 tests)
docs/superpowers/task-reports/port-menu-actions-a4-brief.md
docs/superpowers/task-reports/port-menu-actions-a4-report.md  (this file)
```

## Deviations from brief

- Added `_imported_ea` to the recursive-visitor ctor (not in the original,
  which used a global). This is the Session-owned variant of the B11 fix.
- Kept the debug scan-tree (`_debug_scan_tree` / `_dump_scan_tree`) rather
  than stubbing it — it's cheap logging and helps future debugging of deep
  scans. Added a defensive try/except.
- `_check_call` in `RecursiveObjectDownwardsVisitor` guards against
  `parent_expr()` returning None and parents.size() < 2 (the original
  would crash on malformed ctree). No behavioral change for valid input.
