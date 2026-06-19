# Phase A.3 Report: Port ObjectDownwardsVisitor + ObjectUpwardsVisitor

**Date:** 2026-06-19
**Branch:** `master`
**Result:** A.3 complete; the two non-recursive visitors + the real
`ObjectVisitor` base are in place for the SearchVisitor (Phase A.5).

## Summary

Replaced the 38-LOC `visitor_base.py` stub with the full hierarchy from
`refs/.../api.py:211-405`: `ObjectVisitor` (real base with `set_callbacks`,
`_get_line`, `_manipulate` delegation, `_skip` mode), `ObjectDownwardsVisitor`
(forward assignment tracking), and `ObjectUpwardsVisitor` (two-stage
prepare→parse with transitive-closure graph). Added `cv_flags`/`parents`/
`apply_to` to the `ctree_parentee_t` mock so the visitors construct under
test.

## Changes

| File | Change |
|---|---|
| `src/hexrays_pytools/domain/scanner/visitor_base.py` | **REWRITE** — `ObjectVisitor` + `ObjectDownwardsVisitor` + `ObjectUpwardsVisitor` (~290 LOC) |
| `tools/mock_ida.py` | `ctree_parentee_t` gets `cv_flags`/`parents`/`apply_to` so `cv_flags |= CV_POST` and `self.parents` work under mock |
| `tests/domain/scanner/test_visitor_base.py` | **REWRITE** — 25 tests (was 3 stub tests) |
| `tests/domain/scanner/test_member_extractor.py` | Updated 2 tests to the 4-arg base signature (Phase A.5 will own the real rewrite) |

## What's ported (class by class)

### ObjectVisitor (base)
- Real `__init__(cfunc, obj, data, skip_until_object)` — initializes `_objects`, `_init_obj`, `_start_ea`, `_skip`, `crippled`, `_user_manipulate`
- `process()` — `apply_to(cfunc.body, None)`
- `set_callbacks(manipulate)` — binds a function as an instance method so it receives `self` first
- `_get_line()` — walks `self.parents` to the first citem, returns `tag_remove(print1(...))`; returns `""` (not AssertionError) if the parent stack is all cexprs
- `_manipulate(cexpr, obj)` — delegates to `_user_manipulate`
- `_default_manipulate` — debug-log fallback
- `_is_initial_object(cexpr)` — `is_target` + EA match against `_start_ea`
- `objects` read-only property (returns a copy)

### ObjectDownwardsVisitor (forward)
- `cv_flags |= CV_POST` in `__init__`
- `visit_expr` — on `cot_asg`: if `x` matches a tracked obj → check overwrite (maybe drop); if `y` matches → derive a new ScanObject for `x` and append
- `leave_expr` — for each tracked obj, fire `_manipulate` (except `SO_RETURNED_OBJECT`)
- `_is_initial_object` — handles `cot_asg` and `cot_cast` shapes so the seek mode starts at the right expr
- `_is_object_overwritten` — `len(_objects) < 2` short-circuits; returns False if the RHS is a call to a still-tracked object

### ObjectUpwardsVisitor (backward, two-stage)
- `STAGE_PREPARE` / `STAGE_PARSING` constants
- `_stage`, `_tree`, `_call_obj` instance state
- `process()` — PREPARE pass (no CV_POST), then `_prepare()` (closure), then PARSING pass (with CV_POST)
- `visit_expr` — PREPARE-only: builds `from_obj → {to_obj}` graph for every `cot_asg`; also handles `_call_obj.create_scan_obj` for `SO_CALL_ARGUMENT` seeds
- `leave_expr` — PARSING-only: fires `_manipulate` for any tracked obj (or for `_init_obj` in skip mode)
- `_prepare` — BFS through `_tree` to compute the transitive closure of objects feeding the seed; clears `_tree` after

## Why `cv_flags`/`parents`/`apply_to` on the mock

Production visitors read `self.parents`, OR-assign `self.cv_flags`, and call
`self.apply_to(body, parent)`. The previous `ctree_parentee_t` mock was
`class ... pass` — bare. So `ObjectDownwardsVisitor.__init__` raised
`AttributeError: ... has no attribute 'cv_flags'` the moment it tried
`self.cv_flags |= CV_POST`. Adding instance state to the mock makes the
constructors work; tests can still set `v.parents = [...]` directly to
control the parent stack.

## Tests added (25 new)

### ObjectVisitor base (9)
- `test_visitor_process_calls_apply_to`
- `test_visitor_initial_objects_contains_init_obj`
- `test_visitor_objects_is_readonly_copy`
- `test_visitor_set_callbacks_overrides_manipulate` (verifies the bound-method `self` is the visitor)
- `test_visitor_default_manipulate_logs_only`
- `test_visitor_get_line_returns_first_citem_text`
- `test_visitor_get_line_returns_empty_when_no_citem`
- `test_visitor_skip_initially_false_when_ea_valid`
- `test_visitor_skip_false_when_start_ea_is_badaddr`

### ObjectDownwardsVisitor (9)
- `test_downwards_inherits_from_object_visitor`
- `test_downwards_enables_cv_post_flag`
- `test_downwards_visit_expr_on_asg_tracks_rhs` (a = tracked → new obj for `a`)
- `test_downwards_visit_expr_no_match_does_nothing`
- `test_downwards_skip_mode_passes_until_initial`
- `test_downwards_leave_expr_skipped_in_skip_mode`
- `test_downwards_leave_expr_does_not_manipulate_returned` (SO_RETURNED_OBJECT guard)
- `test_downwards_is_object_overwritten_simple`
- `test_downwards_is_object_overwritten_call_to_tracked`

### ObjectUpwardsVisitor (7)
- `test_upwards_inherits_from_object_visitor`
- `test_upwards_initial_stage_is_prepare`
- `test_upwards_visit_expr_in_parsing_is_noop`
- `test_upwards_visit_expr_adds_assignment_to_tree`
- `test_upwards_process_runs_two_stages` (apply_to called twice)
- `test_upwards_prepare_computes_transitive_closure` (a→b→c closure)
- `test_upwards_call_arg_obj_uses_create_scan_obj`

## Quality gates

| Gate | Result |
|---|---|
| `pytest tests/domain/scanner/test_visitor_base.py` | **25 passed** |
| `pytest tests/domain/scanner/` (all) | **28 passed** |
| Full `pytest` suite | **390 passed** (was 368 — +24 net after stub tests removed/added) |
| Coverage | **83.76%** (gate met) |
| `mypy --strict` on changed files | Clean |
| `ruff check` on changed files | Clean |

## Design decisions

1. **Single-underscore `_private`** — the original used `__double` (name-mangled). Single-underscore is the common Python idiom and we are not in a fragile multiple-inheritance MRO trap. All `__private` attrs renamed to `_private`.

2. **Magic numbers guarded** — `_is_object_overwritten` and `_prepare` use literal `5` (= `SO_CALL_ARGUMENT`) where the original did. Added inline comments. Could import the constant, but the original used the literal and the value is part of the on-disk contract.

3. **`_get_line` returns `""` not AssertionError** — the original raised `AssertionError(...)` (a typo — they wrote `AssertionError` instead of `raise AssertionError`). We return an empty string sentinel so a malformed ctree shape doesn't crash the whole scan; callers log and continue.

4. **`set_callbacks` binds to `type(self)`** — the original hardcoded `ObjectDownwardsVisitor` as the bind target, which broke for `ObjectUpwardsVisitor` subclasses. We use `type(self)` so any subclass gets the right bound method.

5. **`_call_obj` uses `obj.id == 5`** with a comment — matches the original `obj.id == SO_CALL_ARGUMENT`. Phase A.4's recursive visitor sets `_call_obj` from its own seed construction.

## What this unlocks

- **Phase A.4 (recursive visitors)** can subclass `ObjectDownwardsVisitor` / `ObjectUpwardsVisitor` and add `_check_call` + `_recursive_process`.
- **Phase A.5 (SearchVisitor)** can subclass `ObjectDownwardsVisitor` and override `_manipulate` with the real extraction logic.
- **Phase B.7 (GuessAllocation)** can use `RecursiveObjectUpwardsVisitor` (Phase A.4) directly.

## Files touched

```
src/hexrays_pytools/domain/scanner/visitor_base.py       (REWRITE, ~290 LOC)
tools/mock_ida.py                                        (MODIFIED, +14 LOC)
tests/domain/scanner/test_visitor_base.py                (REWRITE, 25 tests)
tests/domain/scanner/test_member_extractor.py            (MODIFIED, 2 tests adapted)
docs/superpowers/task-reports/port-menu-actions-a3-brief.md
docs/superpowers/task-reports/port-menu-actions-a3-report.md  (this file)
```

## Deviations from brief

- The brief's `set_callbacks` test used a 2-arg callback; the actual bound-method
  semantics require 3 args (self, cexpr, obj). Adjusted the test.
- `_is_object_overwritten` test needed 2 tracked objects (the `len(_objects) < 2`
  guard is faithful to the original); adjusted the test setup.
- Added the `cv_flags`/`parents`/`apply_to` mock enrichment — not in the brief,
  but required for the visitors to construct under mock_ida. Documented in
  the report.

## Risks / Notes

- The real traversal (visit_expr / leave_expr dispatch) only happens inside
  IDA's ctree-parentee-t C++ machinery. Under mock_ida there is no dispatch,
  so these tests verify construction + the Python-level methods
  (`visit_expr`/`leave_expr`/`_is_object_overwritten`/`_prepare`) called
  directly with mocked cexprs. The end-to-end behavior is verified in real
  IDA via idat headless (Phase A.5+).
- `visitor_base.py` is on the coverage-omit list in `pyproject.toml` for the
  same reason — the dispatch paths can't be reached by mocks.
