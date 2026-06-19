# Research: Port Missing Menu Features from Original Source

**Date:** 2026-06-19
**Branch:** `master`
**Trigger:** User reported "các feature trong menu đang chưa hoạt động được" — many menu
items appear but do nothing. Research mapped current state vs. original source.

## Method

Compared the 27-action registry + 4 event handlers in the new plugin against the
original `refs/HexRaysPyTools/HexRaysPyTools/callbacks/*.py`. Looked at:

1. Is the action class registered in `domain/actions/registry.py`?
2. Does the `activate()` body contain real logic, or `pass`?
3. If it calls a ctree/scanner engine, is that engine actually ported?
4. If it opens a UI widget, is the widget integration wired?

## Inventory: 27 actions + 4 handlers — what's ported?

### ✅ Fully ported (16 actions)

| Action | Port commit | What it does |
|---|---|---|
| ConvertToUsercall | 598dcb5 | Change calling convention to `__usercall` |
| AddRemoveReturn | 598dcb5 | Toggle void ↔ void* return |
| RemoveArgument | 598dcb5 | Remove a function arg from the signature |
| FindFieldXrefs | e61aac4 | Show xref chooser for the selected struct field |
| CreateNewField | e61aac4 | Split a `gap_` field into a real typed member |
| GetStructureBySize | e61aac4 | Find library structs of a given size, render as `sizeof(...)` |
| SwapThenElse | 57b3541 | Swap the then/else branches of an if |
| RecastItemLeft | 7a6d54a | Recast the target side of an assignment / return / call |
| RecastItemRight | 7a6d54a | Recast the source side of a cast |
| RenameOther | beb449a | a = b → rename a to b's name |
| RenameInside | beb449a | Push the caller's var name into the callee's param |
| RenameOutside | beb449a | Pull the callee's param name back to the caller |
| RenameMemberFromFunctionName | beb449a | Infer a struct member from getter/setter name |
| RenameUsingAssert | beb449a | Rename by assert-like string argument |
| SelectContainingStructure | 4cdafcb | Treat a struct pointer as an outer struct field |
| ResetContainingStructure | 4cdafcb | Undo a SelectContainingStructure assignment |

### ✅ Event handlers (2 of 4 ported)

| Handler | Port | Notes |
|---|---|---|
| PotentialNegativeCollector | 4cdafcb | Drives the CONTAINING_RECORD rewrite at CMAT_BUILT |
| SilentIfSwapper | 57b3541 | Re-applies saved if-swaps + spaghetti transform |

### ⚠️ Partial / check-only (1 action)

| Action | Status |
|---|---|
| CreateVtable | `check()` works (uses `DiscoveredVTable.check_address`); `activate()` only logs an info message — the vtable **import** is deferred ("import deferred to recon engine") |

### ❌ Still stub — `activate()` is `pass` (6 actions + 2 event handlers)

| Action | Where | Original source |
|---|---|---|
| ShowGraph | `domain/actions/form_requests.py:23` | `callbacks/form_requests.py:19` |
| ShowClasses | `domain/actions/form_requests.py:36` | `callbacks/form_requests.py:46` |
| ShowStructureBuilder | `domain/actions/form_requests.py:50` | `callbacks/form_requests.py:73` |
| ShallowScanVariable | `domain/actions/scanners.py:23` | `callbacks/scanners.py:34` |
| DeepScanVariable | `domain/actions/scanners.py:23` | `callbacks/scanners.py:52` |
| RecognizeShape | `domain/actions/scanners.py:23` | `callbacks/scanners.py:71` |
| DeepScanReturn | `domain/actions/scanners.py:23` | `callbacks/scanners.py:106` |
| DeepScanFunctions | `domain/actions/scanners.py:63` | `callbacks/scanners.py:121` |
| GuessAllocation | `domain/actions/guess_allocation.py:23` | `callbacks/guess_allocation.py:58` |
| PropagateName | `domain/actions/rename_action.py:145` | (uses `RecursiveObjectDownwardsVisitor`) |
| MemberDoubleClick (event) | `domain/actions/hx_events.py:24` | `callbacks/member_double_click.py` |
| StructXrefCollector (event) | `domain/actions/hx_events.py:48` | `callbacks/struct_xref_collector.py:97` |

## Why they're stubs — the missing engines

The scanner actions + GuessAllocation + PropagateName all depend on a single
large piece of machinery that is **only stubbed** in the new plugin:

### `domain/scanner/member_extractor.py` (41 LOC) — STUB
Original `core/variable_scanner.py` is **337 LOC** with a real `SearchVisitor`
that walks ctree to extract struct members from pointer/xword expressions, plus
`NewShallowSearchVisitor` / `NewDeepSearchVisitor` / `DeepReturnVisitor` that
drive it.

### `domain/scanner/scanned_object.py` (40 LOC) — STUB
Original `api.py` (~250 LOC) defines a full hierarchy:
- `ScanObject` base + 6 concrete subclasses:
  - `VariableObject` (matches `var` lvar expressions)
  - `StructPtrObject` (matches `x->m` expressions)
  - `StructRefObject` (matches `x.m` expressions)
  - `GlobalVariableObject` (matches global symbol refs)
  - `CallArgObject` (matches calls to a specific function)
  - `ReturnedObject` (matches the return value of a function)
- The static `ScanObject.create()` factory dispatches on `cexpr.op`.

The new `scanned_object.py` has only the base class + `SO_*` constants — no
subclasses, no factory.

### `domain/scanner/visitor_base.py` (38 LOC) — STUB
Original `api.py` defines 4 visitor classes that the scanners need:
- `ObjectVisitor` (base — has real `_manipulate` default + `_get_line` + `set_callbacks`)
- `ObjectDownwardsVisitor` (forwards `cot_asg` propagation + leave-hook calls `_manipulate`)
- `ObjectUpwardsVisitor` (two-stage: prepare assignment graph, then run)
- `RecursiveObjectVisitor` + `RecursiveObjectDownwardsVisitor` + `RecursiveObjectUpwardsVisitor`
  (cross-function walking with a `_visited` set)

The new `visitor_base.py` has only the base `ObjectVisitor` with an abstract
`_manipulate`. Down/up/recursive variants are **missing**.

### `domain/recon/structure_model.py` (96 LOC) — PARTIAL
Original `core/temporary_structure.py:TemporaryStructureModel` (1073 LOC) is the
working struct-reconstruction model. The new `StructureModel` is the Qt model
shell, but lacks:
- `add_row` collision detection (the `__eq__` merge in `AbstractMember` is there,
  but the model never calls `bisect.insort` correctly with `__eq__` semantics)
- `import_to_structures` (apply the temp struct to actual Local Types)
- `get_recognized_shape` (used by `RecognizeShape` action)
- `add_offset` and `add_member` rich API
- `finalize()` (currently a no-op in the new code, called by the Structure Builder
  "Finalize" button)

### `core/const.py` — MISSING
Original has a module of pre-built tinfo singletons (`VOID_TINFO`, `PVOID_TINFO`,
`CHAR_TINFO`, `PX_WORD_TINFO`, `DUMMY_FUNC`, `LEGAL_TYPES`, …) initialized in
`init()`. Used heavily by the scanner engine for fallback types. The new plugin
has none of this.

### `core/helper.py` helpers — PARTIAL
Original has many helpers the scanner engine needs but the new plugin lacks:
- `decompile_function(ea)` — decompile + error handling
- `FunctionTouchVisitor` — used by `DeepScanVariable` to pre-touch callees
- `get_func_argument_info(call_expr, arg_expr)` — note: **already ported**
  as `get_call_argument_info` in `func_type.py` (the M3 rename)
- `find_asm_address` — **already ported** in `scanner/ctree_utils.py`
- `is_code_ea`, `is_imported_ea`, `get_funcs_calling_address` — mostly missing
  (only `is_code_ea` and `get_ptr` exist in `infra/arch/`)

## Why the form-request actions are stubs

The widget classes exist (`ui/widgets/structure_builder.py`, `class_viewer.py`,
`graph_viewer.py`) but are never instantiated and shown. Each action's
`activate()` does nothing. The work to port these is mostly about wiring:

| Action | Needs |
|---|---|
| ShowGraph | Construct `StructureGraph(...)` from `ctx.chooser_selection`, wrap in `StructureGraphViewer`, call `.Show()` |
| ShowClasses | Construct `ProxyModel()` + `TreeModel()`, wrap in `ClassViewer`, call `.Show()` |
| ShowStructureBuilder | Get current `StructureModel` from `session.workspace.model`, wrap in `StructureBuilder(model)`, call `.Show()` |

These are mostly mechanical — the widgets already exist.

## The 2 missing event handlers

### MemberDoubleClick (hxe_double_click)
Original `callbacks/member_double_click.py` navigates from a struct member
double-click in pseudocode to the virtual function (or imported symbol) at that
member's address. Needs `cache.demangled_names` (a name → {ea} map built at
plugin init from `idautils.Names()`). The new `session.py` does not yet have
this cache.

### StructXrefCollector (hxe_maturity / CMAT_FINAL)
Original `callbacks/struct_xref_collector.py:StructXrefCollectorVisitor` walks
the cfunc body looking for `cot_memptr` / `cot_memref` expressions and stores
`(func_offset, line, access_type)` in `XrefStorage()`. The new
`XrefStorage` exists and is netnode-backed, but the `CMAT_FINAL` collector that
populates it is missing.

## Recommended porting order

| # | Phase | What | Effort | Why this order |
|---|---|---|---|---|
| 1 | **Engine** | Port `core/const.py` (tinfo singletons) | 30 min | Scanner engine depends on it |
| 2 | **Engine** | Port full `ScannedObject` hierarchy to `scanned_object.py` | 1.5 h | Scanner engine depends on it |
| 3 | **Engine** | Port `ObjectDownwardsVisitor` + `ObjectUpwardsVisitor` to `visitor_base.py` | 3 h | All 5 scanners + RecognizeShape depend on it |
| 4 | **Engine** | Port `RecursiveObjectDownwardsVisitor` + `RecursiveObjectUpwardsVisitor` to `visitor_base.py` | 2 h | Deep scanners + PropagateName |
| 5 | **Engine** | Port real `SearchVisitor` + 3 concrete visitors to `member_extractor.py` | 3 h | The actual struct-reconstruction logic |
| 6 | **Engine** | Wire `ScannedGlobalObject.apply_type` + `ScannedVariableObject.apply_type` | 1 h | Scanners need to apply types after recognition |
| 7 | **Actions** | Port 5 scanner actions + GuessAllocation | 2 h | Depends on phases 1–6 |
| 8 | **Actions** | Port PropagateName | 30 min | Depends on phase 4 |
| 9 | **Handlers** | Port MemberDoubleClick + add `demangled_names` cache to `Session` | 1.5 h | Standalone |
| 10 | **Handlers** | Port StructXrefCollector + visit logic | 1.5 h | Depends on xref_storage (already ported) |
| 11 | **Form** | Port ShowGraph / ShowClasses / ShowStructureBuilder | 2 h | Mechanical wiring |
| 12 | **Actions** | Finish CreateVtable import | 1.5 h | Depends on `discovered_vtable` model |
| **Total** | | | **~20 h** | |

## What's NOT in the gap

For completeness — these have real implementations and do work:

- All 6 ctree engines (recast, rename, swap_if, negative_offsets)
- All `domain/types/` (tinfo_utils, func_type, udt_builder)
- All `domain/xrefs/` (XrefStorage netnode-backed with auto-migrate)
- `domain/browser/` (TreeModel, ProxyModel — UI model layer, not the engine)
- `domain/graph/structure_graph.py`
- `domain/templated/`, `domain/til/`
- `domain/til/type_library.py` (choose_til, import_type)

## Verification plan

After each phase, verify in real IDA 9.3 via `idat -A`:
- Phase 1-2: `pytest tests/domain/scanner/` passes with mock
- Phase 3-6: `pytest tests/domain/scanner/` passes + manual idat test of a 5-line
  C struct decompilation
- Phase 7-8: All scanner actions appear in menu and do something
- Phase 9-10: Both event handlers fire correctly
- Phase 11: All 3 form widgets open
- Phase 12: CreateVtable imports a real vtable

## Files touched (expected)

```
src/hexrays_pytools/
├── domain/
│   ├── const.py                       (NEW)
│   ├── recon/structure_model.py       (rewrite: real model API)
│   ├── scanner/
│   │   ├── scanned_object.py          (rewrite: full hierarchy)
│   │   ├── visitor_base.py            (rewrite: 4 visitor classes)
│   │   └── member_extractor.py        (rewrite: real SearchVisitor)
│   ├── actions/
│   │   ├── form_requests.py           (port all 3)
│   │   ├── scanners.py                (port all 5)
│   │   ├── guess_allocation.py        (port)
│   │   ├── rename_action.py           (port PropagateName)
│   │   ├── struct_creation.py         (finish CreateVtable)
│   │   └── hx_events.py               (port MemberDoubleClick + StructXrefCollector)
│   ├── session.py                     (add demangled_names cache)
│   └── types/func_type.py             (already has get_call_argument_info)
tests/
├── domain/scanner/                    (new test files)
│   ├── test_scanned_object.py
│   ├── test_visitor_base.py
│   └── test_member_extractor.py
```

## Out of scope (existing v1 features that can wait)

- Templated type detection (`domain/templated/templated_types.py` is ported but
  the "Propagate through all names" / "Scan any type" UX that the original has
  is minimal — the test in `tests/domain/templated/` is the only thing driving it)
- "Demangled name → virtual function" navigation in the Local Types viewer
  (original has this; new plugin's class browser is just a read-only tree)

## Notes / Risks

1. **ctree_parentee_t visit semantics**: Original uses `cv_flags |= idaapi.CV_POST`
   in `ObjectDownwardsVisitor.__init__`. The new plugin's `ObjectVisitor` base
   may need a `cv_flags` plumbing pass.

2. **`apply_to` ownership**: Original carefully sets `thisown = False` on
   `cexpr_t` objects it constructs (to avoid IDA freeing them). The new
   `domain/ctree/negative_offsets.py:_make_num` does this — must be applied
   consistently in the new port.

3. **The `crippled` flag**: Original `RecursiveObjectVisitor` checks if the
   function is just a single call (thunk) and disables type application in that
   case. The new `member_extractor.py` has no such guard.

4. **Mock test coverage**: The new scanner engine code is **not unit-testable
   with mocks** (same exclusion list as the ctree engines). All testing has to
   happen in real IDA via idat. Pytest coverage gate already excludes
   `*/domain/scanner/*.py` (per `pyproject.toml`).

## Commit strategy

One commit per phase, in order. Each commit:
- Bumps the relevant brief/report docs (`docs/superpowers/task-reports/port-menu-actions-phaseN.{brief,report}.md`)
- Includes the `mypy --strict` / `ruff` / `pytest` gates
- Verified in real IDA 9.3 via idat
