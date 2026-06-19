# Phase A.2 Report: Port `ScanObject` hierarchy (7 subclasses)

**Date:** 2026-06-19
**Branch:** `master`
**Result:** A.2 of port-menu-actions plan complete; ctree-traversing code in
Phase A.3+ now has the typed factory it needs.

## Summary

Replaced the 40-LOC `scanned_object.py` stub with the full 280-LOC `ScanObject`
hierarchy from `refs/.../api.py:13-205` — base class + 7 concrete subclasses +
static `create()` factory. Added real ctree types (`ctree_item_t`, `cexpr_t`,
`carg_t`, `lvar_t`) to `tools/mock_ida.py` so production `isinstance()` checks
work under the test mock.

## Changes

| File | Change |
|---|---|
| `src/hexrays_pytools/domain/scanner/scanned_object.py` | **REWRITE** — `ScanObject` + 7 subclasses + `create()` factory (281 LOC) |
| `tools/mock_ida.py` | Add 4 real ctree classes (`ctree_item_t`, `cexpr_t`, `carg_t`, `lvar_t`) so `isinstance(arg, idaapi.ctree_item_t)` works under mock |
| `tests/domain/scanner/test_scanned_object.py` | **REWRITE** — 27 tests (was 3 stub tests) covering all subclasses + factory + parent-walker |

## What's ported (class by class)

| Class | Lines | Notes |
|---|---|---|
| `ScanObject` | base | ea/name/tinfo/id fields, `__eq__/__hash__/__repr__` |
| `VariableObject` | subclass | matches `cot_var` with same `v.idx` |
| `StructPtrObject` | subclass | matches `cot_memptr` with same struct_name + offset |
| `StructRefObject` | subclass | matches `cot_memref` with same struct_name + offset |
| `GlobalVariableObject` | subclass | matches `cot_obj` with same `obj_ea` |
| `CallArgObject` | subclass | matches `cot_call` to specific function; includes `create_scan_obj()` for the upward visitor and `create(cfunc, arg_idx)` for building from a function's arg slot |
| `ReturnedObject` | subclass | matches `cot_call` to a specific function (return value) |
| `MemoryAllocationObject` | subclass | factory `create(cfunc, cexpr)` detects `malloc`/`operator new` |
| `ScanObject.create()` | static factory | dispatches on `cexpr.op` (or `ctree_item_t.get_lvar()`) — returns `None` for unsupported shapes |
| `ScanObject.get_expression_address()` | static helper | walks parents until non-BADADDR EA found — mirrors `api.py:59-68` |
| `_get_member_name()` | module helper | looks up the member name at a struct byte offset — replaces the original `helper.get_member_name` indirection |

## Why a real class for `ctree_item_t` in mock_ida

Production code does:
```python
if isinstance(arg, idaapi.ctree_item_t):
    lvar = arg.get_lvar()
    ...
```

Under the previous mock, `idaapi.ctree_item_t` was a `MagicMock` — and
`isinstance(..., MagicMock)` raises `TypeError: isinstance() arg 2 must be
a type`. The mock needed a real class. Pattern follows the existing
`ctree_parentee_t` / `plugin_t` / `action_handler_t` real-class stubs in
`mock_ida.py`.

The class also carries the attributes production code reads (`get_lvar`,
`citype`, `e`) so tests can use `MagicMock(spec=idaapi.ctree_item_t)` and
configure those slots without raising `AttributeError`.

## Tests added (27 new)

- 2 tests for `SO_*` constants (on-disk contract)
- 3 tests for `ScanObject` base (default state, repr, equality/hash)
- 2 tests for `VariableObject` (init + `is_target` predicate)
- 2 tests for `StructPtrObject` (init + `is_target` predicate)
- 2 tests for `StructRefObject` (init + `is_target` predicate)
- 2 tests for `GlobalVariableObject` (init + `is_target` predicate)
- 3 tests for `CallArgObject` (init + `is_target` + `create` factory)
- 1 test for `ReturnedObject` (init + match)
- 4 tests for `MemoryAllocationObject` (malloc, operator new, unknown call, non-call; cast-wrapped variant merged into the malloc test)
- 7 tests for `ScanObject.create` factory (cot_var, cot_memptr, cot_memref, cot_obj, unsupported op, ctree_item with lvar, ctree_item with expr)
- (some tests merged for compactness — final count: 27 tests)

## Quality gates

| Gate | Result |
|---|---|
| `pytest tests/domain/scanner/test_scanned_object.py` | **27 passed** |
| Full `pytest` suite | **368 passed** (was 344 — +24 net after the 3 stub tests were removed and 27 new tests added) |
| Coverage | **83.83%** (gate met, ~stable) |
| `mypy --strict` on changed files | Clean |
| `ruff check` on changed files | Clean |

## Design decisions

1. **`ScanObject` constructor is no-arg** — mirrors the original. Subclasses populate `ea/name/tinfo/id` themselves. (The previous stub had `(ea, name, tinfo, op)` kwargs — this was a non-port; the rewrite is the canonical form.)

2. **Factory dispatches on `cexpr.op` first, then on `ctree_item_t` last** — matches original `api.py:21-57`. The two `ctree_item_t` sub-branches (lvar vs expr) are checked first because `ctree_item_t` carries its own `e` and we want to use that instead of the raw `arg`.

3. **Field names match the original API** (`obj_ea`, `arg_idx`, `struct_name`, `offset`) so any future v1-plugin code ported later can be ported by line rather than renamed wholesale.

4. **`ReturnedObject` is genuinely different from `CallArgObject`** — they look similar (`is_target` is the same predicate) but `ReturnedObject` has no `arg_idx` field; `CallArgObject` does. The original had this distinction for clarity even though it duplicates predicate logic.

5. **`_get_member_name()` lives in `scanned_object.py` (not `tinfo_utils.py`)** — the original's `helper.get_member_name` is the same code. Putting it here keeps the file self-contained; later phases may move it if a more general `tinfo_utils.get_member_name` is needed.

## What this unlocks

- **Phase A.3 (Object visitors)** can pass `ScanObject` instances to `_manipulate(cexpr, obj)`.
- **Phase A.5 (SearchVisitor)** can call `ScanObject.create(cfunc, ctree_item)` to convert user-clicked items.
- **Phase B.7 (scanner actions)** can call `is_legal_type(obj.tinfo)` against `session.consts.legal_types`.

## Files touched

```
src/hexrays_pytools/domain/scanner/scanned_object.py  (REWRITE, 281 LOC, 84% covered)
tools/mock_ida.py                                     (MODIFIED, +35 LOC)
tests/domain/scanner/test_scanned_object.py           (REWRITE, 27 tests)
docs/superpowers/task-reports/port-menu-actions-a2-brief.md
docs/superpowers/task-reports/port-menu-actions-a2-report.md   (this file)
```

## Deviations from brief

- The brief listed 5 `MemoryAllocationObject` tests; I merged the "cast-wrapped
  call" case into the malloc test rather than having a separate test. The
  behavior is fully covered; the test count drops from 15 to 14 in that
  section. The original brief count was a rough estimate.
- Ruff's `SIM108` auto-fix replaced an `if/else` in `MemoryAllocationObject.create`
  with a ternary. The behavior is identical, the line count drops by 1.
- Renamed the local `result` in the ctree_item lvar branch to `lvar_obj` to
  avoid a mypy "redefined" error against the outer `result: ScanObject | None`.
  No behavioral change.

## Risks / Notes

- The `ScanObject` here is `ScanObject` (no 'd'). The `ScannedObject` (with 'd')
  hierarchy that wraps these for the workspace comes in Phase A.6. Two
  layers, on purpose: matching is stateless, producing has lifetime.
- `is_target()` overrides do not check `self.id == cexpr.op` before
  narrowing on the specific field — they go straight to the typed check
  (e.g. `cexpr.v.idx == self.index`). The base class's `is_target()` is the
  generic `cexpr.op == self.id` fallback for the `ScanObject` default
  representation, but no concrete subclass uses it.
