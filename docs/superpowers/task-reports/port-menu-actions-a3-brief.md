# Phase A.3 Brief: Port ObjectDownwardsVisitor + ObjectUpwardsVisitor

**Date:** 2026-06-19
**Phase:** A.3 of port-menu-actions research
**Goal:** Add the 2 non-recursive visitor classes to
`src/hexrays_pytools/domain/scanner/visitor_base.py` so the SearchVisitor
(Phase A.5) has a base to build on.

## Source

`refs/HexRaysPyTools/HexRaysPyTools/api.py:211-405` (~195 LOC).

## What's ported

### ObjectVisitor base (already exists as 38-LOC stub)

The current stub in `visitor_base.py` has the right skeleton but no
`_manipulate`, no `set_callbacks`, no `_get_line`. The rewrite adds these.

### ObjectDownwardsVisitor

Forward visitor: follows the data flow *down* the assignment chain. When
a `cot_asg` assigns the tracked object to a new name, the new name becomes
a tracked object too. When the ctree leaves a tracked expression,
`_manipulate` fires.

Key behavior (mirrors `api.py:253-296`):
- `cv_flags |= idaapi.CV_POST` so `visit_expr` AND `leave_expr` are called
- `visit_expr` fires on `cot_asg` only:
  - If `x` matches a tracked obj → check `__is_object_overwritten` → maybe drop
  - If `y` matches a tracked obj → derive a new `ScanObject` for `x` and track it
- `leave_expr` fires when leaving any expression:
  - If a tracked obj matches `cexpr` (and is not `RETURNED_OBJECT`) → `_manipulate`
- `_is_initial_object(cexpr)` — used by `_skip` to start tracking at the user's
  selected expression.

### ObjectUpwardsVisitor

Backward visitor: builds an assignment *graph* in the prepare stage, then
visits it again to find which expressions feed the tracked object. Two passes:
1. **STAGE_PREPARE** — for each `cot_asg`, build a `from_obj → {to_obj}` graph
   starting from the initial object.
2. **STAGE_PARSING** — re-traverse the ctree; `leave_expr` fires `_manipulate`
   for any expression matching a tracked obj.

Key behavior (mirrors `api.py:323-405`):
- `process()` runs `STAGE_PREPARE` pass first (no `CV_POST`), then `STAGE_PARSING`
  pass with `CV_POST` enabled.
- `_call_obj` (used by `RecursiveObjectUpwardsVisitor` in Phase A.4) — None for
  the standalone ObjectUpwardsVisitor.
- `_stage`, `_tree` are instance state.
- `__prepare()` uses BFS through the graph to compute the closure of objects
  that transitively feed the initial object.

## Visitor base — required methods

| Method | Purpose |
|---|---|
| `process()` | Run the visitor over `cfunc.body` |
| `set_callbacks(manipulate)` | Override `_manipulate` dynamically |
| `_get_line()` | Walk parents to find the enclosing citem, return its `print1()` text |
| `_manipulate(cexpr, obj)` | Per-item callback (default: log only; subclasses override) |

## Tests (added to existing `test_visitor_base.py`)

The existing 3 tests verify the base class skeleton. New tests:

### ObjectDownwardsVisitor

1. `test_downwards_inherits_from_object_visitor` — isinstance check
2. `test_downwards_visit_expr_on_asg_tracks_rhs` — `a = tracked; cexpr.y`
   matches → new ScanObject for `a` is added
3. `test_downwards_visit_expr_on_asg_removes_lhs_when_overwritten` — `tracked
   = something_untracked` removes `tracked` from `_objects`
4. `test_downwards_leave_expr_calls_manipulate` — when leaving a tracked expr,
   the subclass's `_manipulate` fires
5. `test_downwards_skipped_until_initial_object` — when `_skip=True`, does not
   track or fire `_manipulate` until the initial object is encountered
6. `test_downwards_does_not_manipulate_returned_object` — `SO_RETURNED_OBJECT`
   matches in `leave_expr` but does NOT fire `_manipulate`

### ObjectUpwardsVisitor

7. `test_upwards_inherits_from_object_visitor` — isinstance check
8. `test_upwards_process_runs_two_stages` — after `process()`, `_stage` ended in
   `STAGE_PARSING`
9. `test_upwards_visit_expr_builds_assignment_graph` — assigning from `a` to `b`
   puts `a → b` in `_tree` during STAGE_PREPARE
10. `test_upwards_leave_expr_calls_manipulate_for_tracked` — when the closure
    contains the expression's obj, `_manipulate` fires in STAGE_PARSING

### ObjectVisitor base

11. `test_object_visitor_set_callbacks_overrides_manipulate` — set_callbacks
    swaps the default `_manipulate` for a custom one
12. `test_object_visitor_get_line_returns_parent_text` — when the parent stack
    has a citem, `_get_line()` returns its `tag_remove(print1(...))`

## Out of scope (Phase A.4)

- `RecursiveObjectVisitor` (base for cross-function)
- `RecursiveObjectDownwardsVisitor` (downward + callees)
- `RecursiveObjectUpwardsVisitor` (upward + callers)
- `_check_call`, `_recursive_process`, `_visited` set, `_new_for_visit` queue

## Field-name mapping

Original uses both `__private` (double underscore) and `__weakref__`-style
attributes. The new code uses single-underscore `_private` because we are
not in a multiple-inheritance MRO trap, and single-underscore is the more
common Python idiom. Renamed:

| Original | New | Reason |
|---|---|---|
| `self.__manipulate` | `self._manipulate` | single-underscore convention |
| `self.__call_obj` | `self._call_obj` | same |
| `self.__is_object_overwritten` | `self._is_object_overwritten` | same |
| `self.__add_object_assignment` | `self._add_object_assignment` | same |
| `self.__prepare` | `self._prepare` | same |
| `self.__recursive_process` | `self._recursive_process` | same |
| `self.__iter_callers` | `self._iter_callers` | same |
| `self.__is_func_crippled` | `self._is_func_crippled` | same |

`__cfunc`, `__function_address`, `__result`, `__storage`, `__get_line`,
`__get_type`, `__find_ref_address`, `__prepare_debug_message` are not in
this phase (they live on `StructXrefCollectorVisitor` from
`callbacks/struct_xref_collector.py`, which is Phase C — not yet started).

## Quality gates

- `pytest tests/domain/scanner/test_visitor_base.py` — pass
- `mypy --strict src/hexrays_pytools/domain/scanner/visitor_base.py` — clean
- `ruff check` — clean
- Full `pytest` — still passes, 80%+ coverage
