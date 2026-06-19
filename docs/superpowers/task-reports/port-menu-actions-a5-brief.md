# Phase A.5 Brief: Port SearchVisitor + ScannedObject hierarchy

**Date:** 2026-06-19
**Phase:** A.5 of port-menu-actions research
**Goal:** Real struct-member extraction engine. Replace the 41-LOC stub
`member_extractor.py` with the full 337-LOC original, plus port the
`ScannedObject` (with 'd') hierarchy that SearchVisitor produces.

## Source

`refs/HexRaysPyTools/HexRaysPyTools/core/variable_scanner.py` (337 LOC).
The `ScannedObject` hierarchy lives at the top of the same file (lines 19-114).

## What's ported

### ScannedObject hierarchy (lines 19-114) — NEW file

A `ScannedObject` (with 'd') is what the scanner **produces** — it wraps the
matching `ScanObject` (without 'd') with the expression address, the function EA,
an origin offset, and an `apply_type()` callback. Lifetime-based: you build one
when the scanner finds a match, then call `apply_type()` later from the UI.

| Class | `apply_type()` body |
|---|---|
| `ScannedObject` (base) | raises `NotImplementedError` |
| `ScannedGlobalObject` | `idaapi.set_tinfo(self.__obj_ea, tinfo)` |
| `ScannedVariableObject` | Open pseudocode, find lvar by `lvar_locator_t`, `hx_view.set_lvar_type(lvar, tinfo)` |
| `ScannedStructureMemberObject` | Log a warning ("not yet implemented") |

Static factory `ScannedObject.create(obj, expression_address, origin, applicable)`
dispatches on `obj.id` to the right subclass.

### SearchVisitor (lines 117-296) — rewrite stub

Real `_manipulate(cexpr, obj)`:
1. Reject if `obj.tinfo` is not `is_legal_type` (skips weird tinfos).
2. If `cexpr.type.is_ptr()` → `__extract_member_from_pointer`.
3. Else → `__extract_member_from_xword`.
4. If a member is produced → `temporary_structure.add_row(member)`.

Helpers (all ported):
- `_get_member(offset, cexpr, obj, tinfo, obj_ea)` — builds the right
  `Member`/`VoidMember`/`VirtualTable` for the offset.
- `_parse_call(call_cexpr, arg_cexpr, offset)` — pulls a tinfo from the
  called function's arg via `get_func_argument_info`.
- `__extract_member_from_pointer` / `__extract_member_from_xword` — walks
  the parents stack to decode `idx`/`add`/`cast`/`asg` shapes.
- `__extract_member` — the main state machine: walks parents, picks a
  default tinfo (`const.PX_WORD_TINFO`), dereferences, builds member.
- `__extract_obj_ea(cexpr)` — strip `cot_ref` / read `cot_obj.obj_ea`.
- `__deref_tinfo(tinfo)` — strip one pointer level; `char*` → `char`,
  1-byte `void*` → `None` (becomes VoidMember).

### Three concrete visitors (lines 299-337)

| Visitor | Mixin | Purpose |
|---|---|---|
| `NewShallowSearchVisitor` | `ObjectDownwardsVisitor` | Non-recursive: only this function |
| `NewDeepSearchVisitor` | `RecursiveObjectDownwardsVisitor` | Recursive: also walks callees |
| `DeepReturnVisitor` | inherits `NewDeepSearchVisitor` | Recursive + iterates callers via `_start`/`_finish` |

All three call `SearchVisitor(cfunc, origin, obj, temporary_structure)`
in their `__init__`. The "temporary_structure" argument is the
`StructureModel` (or `ReconWorkspace`) — the new design threads this via
`Session.workspace.model` so callers don't pass it.

## Constructor signature change

The original `SearchVisitor(cfunc, origin, obj, temporary_structure)` becomes
`SearchVisitor(cfunc, origin, obj, workspace)`. The `workspace` is the
`ReconWorkspace` dataclass; the visitor reads `workspace.model` to call
`add_row()`.

## Tests

The visitor body uses live ctree dispatch — not unit-testable end-to-end with
mocks (same exclusion list as `visitor_base.py`). Tests focus on the Python-
level state + pure helpers:

### ScannedObject (with 'd')
1. `test_scanned_object_creation_sets_fields` — name, expression_address,
   func_ea, origin, _applicable stored
2. `test_scanned_object_func_ea_is_idc_get_func_attr` — func_ea computed via
   `idc.get_func_attr` (mocked)
3. `test_scanned_object_equality_by_func_ea_name_ea` — `__eq__` / `__hash__`
4. `test_scanned_object_factory_dispatches_on_obj_id` — covers all 4 subclasses
5. `test_scanned_global_apply_type_calls_set_tinfo` — `apply_type` invokes
   `idaapi.set_tinfo(obj_ea, tinfo)`
6. `test_scanned_global_apply_type_skipped_when_not_applicable`
7. `test_scanned_variable_apply_type_finds_lvar_in_pseudocode` — happy path
8. `test_scanned_variable_apply_type_logs_warning_when_lvar_missing`
9. `test_scanned_variable_apply_type_skipped_when_not_applicable`
10. `test_scanned_member_apply_type_logs_not_implemented`

### SearchVisitor (Python-level state)
11. `test_search_visitor_init_stores_origin_and_workspace`
12. `test_search_visitor_deref_tinfo_void_returns_none`
13. `test_search_visitor_deref_tinfo_char_ptr_returns_char`
14. `test_search_visitor_deref_tinfo_x_word_ptr_returns_pointed`
15. `test_search_visitor_deref_tinfo_non_ptr_returns_unchanged`
16. `test_search_visitor_extract_obj_ea_strips_ref`
17. `test_search_visitor_extract_obj_ea_returns_badaddr_for_non_obj`
18. `test_search_visitor_parse_call_returns_arg_tinfo`
19. `test_search_visitor_parse_call_falls_back_to_char_when_no_tinfo`
20. `test_search_visitor_get_member_skips_when_crippled`
21. `test_search_visitor_get_member_uses_void_member_for_vo_id_tinfo`
22. `test_search_visitor_get_member_dereferences_const_pvoid_to_pvoid`

### Concrete visitors (smoke)
23. `test_shallow_search_visitor_is_object_downwards`
24. `test_deep_search_visitor_is_recursive_object_downwards`
25. `test_deep_return_visitor_is_subclass_of_deep_search`

## Field-name mapping

All `__double` private attrs → `_single` (consistent with previous phases).

## Quality gates

- `pytest tests/domain/scanner/` — pass
- `mypy --strict` on `member_extractor.py` + `scanned_object.py` (new file) — clean
- `ruff check` — clean
- Full `pytest` — still passes, 80%+ coverage (omit if needed)

## Out of scope

- `apply_type()` bodies that need real IDA are exercised in idat headless, not unit tests.
- `temporary_structure` → `ReconWorkspace` rename is already in place; we
  just thread it through.
- The `_dump_scan_tree` debug pretty-printer stays as-is (Phase A.4 already
  ported it).

## Files

```
src/hexrays_pytools/domain/scanner/scanned_object.py    (existing — append 'd' class)
src/hexrays_pytools/domain/scanner/member_extractor.py  (rewrite: 41 LOC → ~220 LOC)
tests/domain/scanner/test_scanned_objects.py           (NEW — 10 tests)
tests/domain/scanner/test_search_visitor.py            (NEW — 13 tests)
```