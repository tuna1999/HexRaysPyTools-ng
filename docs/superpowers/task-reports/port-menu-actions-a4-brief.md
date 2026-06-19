# Phase A.4 Brief: Port Recursive Down/Up object visitors

**Date:** 2026-06-19
**Phase:** A.4 of port-menu-actions research
**Goal:** Add the 3 recursive visitor classes to
`src/hexrays_pytools/domain/scanner/visitor_base.py` so the deep scanners
(Phase A.5) and PropagateName / GuessAllocation (Phase B) can walk across
function boundaries.

## Source

`refs/HexRaysPyTools/HexRaysPyTools/api.py:408-580` (~170 LOC).

## What's ported

### RecursiveObjectVisitor (base — NEW class)

Base for cross-function walking. Adds a `_visited` set (to avoid infinite
recursion) and a `_new_for_visit` queue (collected during one pass,
recursed into afterward).

| Method | Purpose |
|---|---|
| `__init__(cfunc, obj, data, skip_until_object, visited=None)` | Calls `super().__init__`, sets `_visited`, `_new_for_visit`, `_arg_idx=-1`, debug-tree state |
| `process()` | `_start()` → `_recursive_process()` → `_finish()` → `dump_scan_tree()` |
| `set_callbacks(manipulate, start, start_iteration, finish, finish_iteration)` | Bind any of the 5 hooks |
| `prepare_new_scan(cfunc, arg_idx, obj, skip=False)` | Reset per-call state for a fresh function |
| `_recursive_process()` | `_start_iteration()` → `super().process()` → `_finish_iteration()` |
| `_manipulate(cexpr, obj)` | Calls `_check_call(cexpr)` then `super()._manipulate` |
| `_check_call(cexpr)` | Abstract — subclasses implement to detect calls worth recursing into |
| `_add_visit(func_ea, arg_idx)` | Add to `_visited` + `_new_for_visit` if not already seen |
| `_add_scan_tree_info(func_ea, arg_idx)` | Build the debug tree (for logging) |
| `_start/_start_iteration/_finish/_finish_iteration` | No-op hooks (subclasses override) |
| `_is_func_crippled()` | True if the function body is just a thunk (single return / single call) |

The 4 lifecycle hooks (`_start`, `_start_iteration`, `_finish`,
`_finish_iteration`) are how subclasses inject per-function setup/teardown
without overriding `process()`.

### RecursiveObjectDownwardsVisitor (cross-function forward)

Recurses into callees. When the tracked object is passed as an argument to
a call, decompile the callee and scan it too (the callee's first-arg lvar
becomes the new seed).

- `_check_call(cexpr)` — detect when the tracked object is an argument of
  a `cot_call`; if so, `_add_visit(callee_ea, arg_idx)`.
- `_recursive_process()` — override: after the normal pass, pop
  `_new_for_visit` entries, decompile each callee, prepare a new scan with
  `VariableObject(cfunc.get_lvars()[arg_idx], arg_idx)`, recurse.

### RecursiveObjectUpwardsVisitor (cross-function backward)

Recurses into callers. When the tracked object is a function argument,
decompile each caller and scan it too.

- `prepare_new_scan` — override to also set `_call_obj`.
- `_check_call(cexpr)` — detect when a local var is `is_arg_var`; if so,
  `_add_visit(func_ea, arg_idx)` + walk all callers.
- `_recursive_process()` — override: after the normal pass, for each
  `(func_ea, arg_idx)` in `_new_for_visit`, decompile each caller, prepare
  a new scan with `CallArgObject.create(...)`, recurse.

## Supporting helpers ported (NEW to `infra/arch/` + `domain/scanner/`)

| Helper | Location | Source |
|---|---|---|
| `is_imported_ea(ea, imported_ea)` | `infra/arch/arch.py` | `helper.py:17` |
| `decompile_function(ea)` | `domain/scanner/helpers.py` (NEW) | `helper.py:390` |
| `FunctionTouchVisitor` | `domain/scanner/helpers.py` (NEW) | `helper.py:291` |

`is_imported_ea` takes the `imported_ea` set as a parameter (no globals —
the original read `cache.imported_ea`, a module global).

`decompile_function` wraps `idaapi.decompile(ea)` and catches
`DecompilationFailure`, logging a warning + returning `None`.

`FunctionTouchVisitor` pre-decompiles all callees of a function so their
arg types are known before the deep scan. Used by `DeepScanVariable`
action.

## Tests

The recursive visitors are hard to test end-to-end (need real ctree
dispatch + decompilation), so tests focus on the Python-level state:

### RecursiveObjectVisitor base
1. `test_recursive_init_visited_empty` — `_visited` is empty by default
2. `test_recursive_prepare_new_scan_resets_state` — sets `_cfunc`,
   `_arg_idx`, `_objects`, `_skip=False`
3. `test_recursive_add_visit_dedupes` — `_add_visit(ea, idx)` returns True
   the first time, False the second
4. `test_recursive_add_visit_grows_new_for_visit` — the new entry appears
   in `_new_for_visit` (the work queue)
5. `test_recursive_is_func_crippled_thunk` — single-call body → True
6. `test_recursive_is_func_crippled_complex` — multi-statement body → False

### RecursiveObjectDownwardsVisitor
7. `test_recursive_downwards_inherits_recursive_visitor`
8. `test_recursive_downwards_check_call_records_callee` — patched to
   detect a call → `_new_for_visit` grows

### RecursiveObjectUpwardsVisitor
9. `test_recursive_upwards_inherits_recursive_visitor`
10. `test_recursive_upwards_prepare_sets_call_obj` —
    `prepare_new_scan` sets `_call_obj` when seed is `SO_CALL_ARGUMENT`

### Helpers
11. `test_decompile_function_returns_cfunc` — happy path
12. `test_decompile_function_returns_none_on_failure` — catches
    `DecompilationFailure`
13. `test_is_imported_ea_plt_segment` — `.plt` segment → True
14. `test_is_imported_ea_in_cache` — ea in the set → True
15. `test_function_touch_visitor_collects_calls` — `visit_expr` adds call
    targets

## Field-name mapping

All `__double` attrs → `_single` (consistent with Phase A.3).

## Quality gates

- `pytest tests/domain/scanner/` — pass
- `mypy --strict` on `visitor_base.py` + `helpers.py` — clean
- `ruff check` — clean
- Full `pytest` — still passes, 80%+ coverage

## Out of scope

- `dump_scan_tree` / `__prepare_debug_message` — the original's fancy
  scan-tree logging. We keep a stub `_debug_scan_tree` dict but don't port
  the pretty-printer; that can come later if anyone needs it for debugging.
