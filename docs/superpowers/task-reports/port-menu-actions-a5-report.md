# Phase A.5 Report: Port SearchVisitor + ScannedObject hierarchy

**Date:** 2026-06-19
**Branch:** `master`
**Result:** A.5 complete; the struct-member scanner engine now has a real
`SearchVisitor` that walks a cfunc, extracts pointer/xword expressions, and
emits `Member`/`VoidMember`/`DiscoveredVTable` rows into the workspace's
`StructureModel`.

## Summary

Replaced the 41-LOC stub `member_extractor.py` with the full search engine,
plus ported the `ScannedObject` (with 'd') hierarchy from the original
`variable_scanner.py:19-114` (now in `scanned_object.py`). The visitor is
still not unit-testable end-to-end with mocks (same exclusion as
`visitor_base.py`); tests cover the Python-level state, factory dispatch,
and pure helpers.

## Changes

| File | Change |
|---|---|
| `src/hexrays_pytools/domain/scanner/scanned_object.py` | +ScannedObject hierarchy (base + 3 subclasses, ~150 LOC) |
| `src/hexrays_pytools/domain/scanner/member_extractor.py` | Rewrite stub → real SearchVisitor + 3 concrete visitors (~250 LOC) |
| `src/hexrays_pytools/domain/types/tinfo_utils.py` | +`is_legal_type()` (~25 LOC) |
| `tests/domain/scanner/test_scanned_objects.py` | NEW — 12 tests |
| `tests/domain/scanner/test_search_visitor.py` | NEW — 12 tests |
| `tests/domain/scanner/test_member_extractor.py` | Updated to new SearchVisitor signature |
| `docs/superpowers/task-reports/port-menu-actions-a5-brief.md` | NEW |

## What's ported

### ScannedObject hierarchy (in `scanned_object.py`)
- `ScannedObject` (base) — wraps name, expression_address, func_ea (via
  `idc.get_func_attr`), origin, `_applicable` flag; `apply_type` raises
  `NotImplementedError`.
- `ScannedGlobalObject` — `apply_type` → `idaapi.set_tinfo(obj_ea, tinfo)`.
- `ScannedVariableObject` — stores `lvar_locator_t(location, defea)`;
  `apply_type` opens pseudocode, finds the lvar by locator, sets type.
- `ScannedStructureMemberObject` — logs a warning (UI flow instead commits
  the whole struct via `StructureModel.import_to_structures`).
- `ScannedObject.create(obj, expression_address, origin, applicable)` —
  static factory dispatching on `obj.id`. Raises `AssertionError` for
  non-producer kinds (the original's assertion).

### SearchVisitor (in `member_extractor.py`)
- `_manipulate(cexpr, obj)` — rejects non-legal types, dispatches to
  `_extract_member_from_pointer` (for `cot_ptr`) or
  `_extract_member_from_xword` (default). On success → `workspace.model.add_row`.
- `_get_member(offset, cexpr, obj, tinfo, obj_ea)` — builds the right
  `Member`/`VoidMember`/`DiscoveredVTable` based on type heuristics.
- `_parse_call(call_cexpr, arg_cexpr, offset)` — pulls tinfo via
  `get_call_argument_info`, derefs via `_deref_tinfo`. Falls back to
  `consts.char_tinfo`.
- `_extract_member_from_pointer` / `_extract_member_from_xword` — walk
  parents stack to decode `idx`/`add`/`cast` shapes.
- `_extract_member` — main state machine: picks default tinfo (from
  `cast` parent or `consts.px_word_tinfo`), derefs, handles `idx`/`ptr`/
  `asg`/`call` shapes.
- `_extract_obj_ea(cexpr)` — strip `cot_ref`, read `cot_obj.obj_ea`.
- `_deref_tinfo(tinfo)` — strip one pointer level. `char*` → `char`;
  1-byte `void*` → `None`.

### Three concrete visitors
- `NewShallowSearchVisitor(SearchVisitor, ObjectDownwardsVisitor)` —
  non-recursive.
- `NewDeepSearchVisitor(SearchVisitor, RecursiveObjectDownwardsVisitor)` —
  walks callees via the Phase A.4 machinery.
- `DeepReturnVisitor(NewDeepSearchVisitor)` — pre-scans all callers via
  `_start`/`_finish` lifecycle hooks (uses the recursive visitor's
  `prepare_new_scan` to reset per-function state).

## Key design change: Session-owned Consts dataclass

The original `core/const.py` exposed module-level globals (`PX_WORD_TINFO`,
`DUMMY_FUNC`, …). Phase A.1 ported these into a per-session `Consts`
dataclass owned by `Session.consts`. `SearchVisitor` takes `consts` via
`__init__` (default `None` for backward compatibility in tests) and reads
tinfo singletons through `@property` accessors (`_px_word_tinfo`,
`_void_tinfo`, etc.). Callers in `domain/actions/scanners.py` (Phase A.7)
will pass `session.consts` explicitly.

## Why we refactored from `__double` to `_single` naming

Initial port used `_SearchVisitor__deref_tinfo` (Python name-mangling for
private access) — the pattern the original `variable_scanner.py` uses.
Ruff flagged the `__double` names as non-PEP8 (`N802`), so refactored to
`_deref_tinfo`, `_extract_member`, `_extract_obj_ea`, `_callers_ea`,
`_call_obj`, `_prepare_scanner`, `_iter_callers`. This matches the
single-underscore convention in the Phase A.4 visitor_base port.

## Tests added (24 new)

### test_scanned_objects.py (12)
1. `test_scanned_object_creation_sets_fields`
2. `test_scanned_object_equality_by_func_ea_name_ea`
3. `test_scanned_object_to_list_format`
4. `test_scanned_object_factory_dispatches_global`
5. `test_scanned_object_factory_dispatches_local_variable`
6. `test_scanned_object_factory_dispatches_struct_member`
7. `test_scanned_object_factory_asserts_unknown_id`
8. `test_scanned_global_apply_type_calls_set_tinfo`
9. `test_scanned_global_apply_type_skipped_when_not_applicable`
10. `test_scanned_variable_apply_type_finds_lvar_in_pseudocode`
11. `test_scanned_variable_apply_type_logs_warning_when_lvar_missing`
12. `test_scanned_member_apply_type_logs_not_implemented`

### test_search_visitor.py (12)
1. `test_search_visitor_deref_tinfo_non_ptr_returns_unchanged`
2. `test_search_visitor_deref_tinfo_x_word_ptr_returns_pointed`
3. `test_search_visitor_deref_tinfo_char_ptr_returns_char`
4. `test_search_visitor_deref_tinfo_one_byte_void_ptr_returns_none`
5. `test_search_visitor_extract_obj_ea_strips_ref`
6. `test_search_visitor_extract_obj_ea_returns_none_for_non_obj`
7. `test_search_visitor_parse_call_returns_arg_tinfo`
8. `test_search_visitor_parse_call_falls_back_to_char`
9. `test_shallow_search_visitor_is_object_downwards`
10. `test_deep_search_visitor_is_recursive_object_downwards`
11. `test_deep_return_visitor_is_subclass_of_deep_search`
12. `test_search_visitor_init_stores_origin_and_workspace`

### test_member_extractor.py (3) — updated to new SearchVisitor signature
- `test_search_visitor_init` (new signature: `cfunc, origin, obj, workspace, consts`)
- `test_search_visitor_manipulate_does_not_raise`
- `test_shallow_visitor_subclasses_search`

## Quality gates (all passing)

```
mypy --strict src/hexrays_pytools/    → Success: no issues found in 76 source files
ruff check (whole package)             → All checks passed!
pytest                                  → 438 passed in 1.26s
coverage                                → 80.12% (≥ 80% gate met)
```

## What's NOT covered (documented in code comments)

- The `_manipulate` ctree walk is verified in real IDA via idat headless
  (same exclusion list as `visitor_base.py` — `pyproject.toml` already
  omits the scanner package).
- `apply_type` bodies that need real IDA (open_pseudocode, set_lvar_type)
  are exercised end-to-end via idat headless + manual right-click.

## What's next

Phase A.6 is now lightweight — it was originally scoped as
"Wire ScannedGlobalObject.apply_type + ScannedVariableObject.apply_type",
but those bodies are already ported in this phase. A.6 will instead be
absorbed by **Phase A.7** (Port 5 scanner actions + GuessAllocation) which
actually wires the actions to instantiate the visitors and pass them
`session.consts` + `session.workspace`.

The action stubs in:
- `domain/actions/scanners.py` (5 actions: ShallowScan, DeepScan,
  RecognizeShape, DeepScanReturn, DeepScanFunctions)
- `domain/actions/guess_allocation.py`

…are the next targets.
