# Phase A.2 Brief: Port `ScanObject` hierarchy (7 subclasses)

**Date:** 2026-06-19
**Phase:** A.2 of port-menu-actions research
**Goal:** Rewrite `src/hexrays_pytools/domain/scanner/scanned_object.py` with
the full `ScanObject` factory hierarchy from `refs/.../api.py`.

## Source

`refs/HexRaysPyTools/HexRaysPyTools/api.py` lines 13–205 (~190 LOC).

## Why this matters

Every scanner (Phase A.5), every `ScannedObject` wrapper (Phase A.6), and
every action in Phase B depends on a factory that converts a `cexpr_t` (or
`ctree_item_t`) into a typed object whose `is_target(cexpr)` knows how to
recognize it during ctree traversal. The current stub `scanned_object.py`
has only the constants — no factory, no subclasses. Porting the hierarchy
unblocks Phase A.5 directly.

## What's ported

### Base + factory
- `ScanObject` base class (no-arg `__init__` like original; `ea/name/tinfo/id` fields)
- Static `ScanObject.create(cfunc, arg)` factory that dispatches on `cexpr.op`:
  - `cot_var` → `VariableObject`
  - `cot_memptr` → `StructPtrObject`
  - `cot_memref` → `StructRefObject`
  - `cot_obj` → `GlobalVariableObject`
  - else → `None`
- Special-case: when `arg` is a `ctree_item_t`, peek at `arg.get_lvar()` /
  `arg.citype == VDI_EXPR` and dispatch accordingly.

### Subclasses (7)

| Class | id | is_target predicate |
|---|---|---|
| `VariableObject(lvar, index)` | `SO_LOCAL_VARIABLE` | `cexpr.op == cot_var and cexpr.v.idx == index` |
| `StructPtrObject(struct_name, offset)` | `SO_STRUCT_POINTER` | `cexpr.op == cot_memptr and cexpr.m == offset and cexpr.x.type.get_pointed_object().dstr() == struct_name` |
| `StructRefObject(struct_name, offset)` | `SO_STRUCT_REFERENCE` | `cexpr.op == cot_memref and cexpr.m == offset and cexpr.x.type.dstr() == struct_name` |
| `GlobalVariableObject(obj_ea)` | `SO_GLOBAL_OBJECT` | `cexpr.op == cot_obj and obj_ea == cexpr.obj_ea` |
| `CallArgObject(func_ea, arg_idx)` | `SO_CALL_ARGUMENT` | `cexpr.op == cot_call and cexpr.x.obj_ea == func_ea` |
| `ReturnedObject(func_ea)` | `SO_RETURNED_OBJECT` | `cexpr.op == cot_call and cexpr.x.obj_ea == func_ea` |
| `MemoryAllocationObject(name, size)` | `SO_MEMORY_ALLOCATOR` | factory `MemoryAllocationObject.create(cfunc, cexpr)` (checks `malloc`/`operator new` in function name) |

### Static helpers
- `ScanObject.get_expression_address(cfunc, cexpr)` — walks parents until a non-BADADDR `cexpr.ea` is found. Mirrors `api.py:59-68`.
- `CallArgObject.create(cfunc, arg_idx)` — special factory: builds a `CallArgObject` from a function's arg slot.
- `CallArgObject.create_scan_obj(cfunc, cexpr)` — drill through `cot_cast/cot_ref/cot_add/cot_sub/cot_idx` to find the underlying `ScanObject` for the arg.

## What is NOT ported here

- The `ScannedObject` (with 'd') hierarchy + `apply_type()` machinery → Phase A.6
- The `SearchVisitor` engine that consumes `ScanObject` → Phase A.5
- The `ASSIGNMENT_LEFT` / `ASSIGNMENT_RIGHT` constants → only used by Phase A.5

## Field-name mapping

Original used snake_case attributes (`obj_ea`, `arg_idx`, etc.). The new
plugin keeps the same names for cross-plugin continuity (anyone who knows
the original api.py recognizes these).

## Tests

1. `test_so_constants_match_original` — verify `SO_*` constants unchanged
   (1, 2, 3, 4, 5, 6, 7) — guards against accidental renumbering (would
   break saved netnodes).
2. `test_scan_object_default_constructor` — `ScanObject()` returns instance
   with `ea=BADADDR, name=None, tinfo=None, id=0`.
3. `test_variable_object_init` — `VariableObject(lvar_mock, 5)` sets
   `id=SO_LOCAL_VARIABLE, index=5, tinfo=lvar.type()`.
4. `test_variable_object_is_target` — matches `cot_var` with same index, not
   `cot_var` with different index.
5. `test_struct_ptr_object_is_target` — matches `cot_memptr` with matching
   struct_name + offset.
6. `test_struct_ref_object_is_target` — matches `cot_memref` with matching
   struct_name + offset.
7. `test_global_variable_object_is_target` — matches `cot_obj` with matching
   obj_ea.
8. `test_call_arg_object_is_target` — matches `cot_call` with matching
   func_ea.
9. `test_returned_object_is_target` — matches `cot_call` to returned func.
10. `test_memory_allocation_object_create_for_malloc` — factory returns
    instance when function name contains "malloc".
11. `test_memory_allocation_object_create_for_new` — factory returns instance
    for "operator new".
12. `test_memory_allocation_object_create_for_unknown` — factory returns None
    for non-allocating call.
13. `test_scan_object_create_for_var_expr` — factory returns
    `VariableObject` for a `cot_var` cexpr.
14. `test_scan_object_create_for_memptr_expr` — factory returns
    `StructPtrObject` for `cot_memptr` cexpr.
15. `test_scan_object_create_returns_none_for_unsupported` — factory returns
    `None` for `cot_num` cexpr.

All tests use `mock_ida` — the `ctree_item_t` / `cexpr_t` / `tinfo_t` mocks
return MagicMocks that can be configured per-test.

## Quality gates

- `pytest tests/domain/scanner/test_scanned_object.py` — pass
- `mypy --strict src/hexrays_pytools/domain/scanner/scanned_object.py` — clean
- `ruff check` — clean
- Full `pytest` suite — still passes, 80%+ coverage

## Out-of-scope notes

The existing 40-LOC `scanned_object.py` has a `ScanObject.__init__(ea, name, tinfo, op)`
constructor and a `get_expression_address` instance method. These conflict with
the original signature `ScanObject.__init__(self)` (no-arg) + static
`ScanObject.get_expression_address`. The rewrite replaces both. This is a
**breaking change** but there are no existing callers of the new signature
(constants are used but no subclasses yet), so no other files need updating.