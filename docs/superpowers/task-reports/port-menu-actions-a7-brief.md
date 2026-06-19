# Phase A.7 Brief: Port 5 scanner actions + GuessAllocation

**Date:** 2026-06-19
**Phase:** A.7 of port-menu-actions research
**Goal:** Wire the 6 actions that depend on the SearchVisitor engine (Phase A.5).

## Source

`refs/.../callbacks/scanners.py` (141 LOC) + `refs/.../callbacks/guess_allocation.py` (66 LOC).

## What needs adding to the supporting layer first

Before porting the actions themselves, the project needs two pieces of state
that used to live on the original `TemporaryStructureModel`:

### `ReconWorkspace.main_offset` (NEW field)

The "primary" struct offset the user is currently reconstructing. The
original `TemporaryStructureModel.main_offset = 0` was mutated when the
user clicked a row in the Structure Builder table. Every scanner reads it
as the `origin` argument to `SearchVisitor.__init__`.

→ Add `main_offset: int = 0` to `ReconWorkspace`. Tracked here (not on
`StructureModel`) because the workspace is session-owned and the model
is a pure Qt model.

### `StructureModel.get_recognized_shape()` (NEW method)

`RecognizeShape` action needs to build a `tinfo_t` from the discovered
members — used to apply the inferred type to the scanned lvar/global.

→ Port the original `get_recognized_shape()` (~60 LOC, builds a UDT
tinfo from the model items) to `StructureModel`. Returns `None` if the
model is empty.

## What's ported

### scanners.py (5 actions)

| Action | Activates | Check |
|---|---|---|
| `ShallowScanVariable` | `NewShallowSearchVisitor.process()` | `ScanObject.create(cfunc, item)` is not None + `is_legal_type` |
| `DeepScanVariable` | `NewDeepSearchVisitor.process()` (after `FunctionTouchVisitor`) | same |
| `RecognizeShape` | Run shallow scan into a fresh model, get recognized tinfo, apply to lvar/global | same |
| `DeepScanReturn` | `DeepReturnVisitor.process()` with `ReturnedObject(func_ea)` seed | `citype == VDI_FUNC` + rettype legal |
| `DeepScanFunctions` | For each selected function in BWN_FUNCS, scan its first arg | widget_type == BWN_FUNCS |

All scanners need:
- `self._session.workspace` for the model + `main_offset`
- `self._session.consts` for the visitor's tinfo singletons
- `self._session.imported_ea` for `RecursiveObjectDownwardsVisitor`

### guess_allocation.py (1 action + 1 visitor)

| Class | What |
|---|---|
| `_GuessAllocationVisitor(RecursiveObjectUpwardsVisitor)` | Tracks allocations feeding the scanned object; collects `(func_ea, var, line, alloc_type)` rows |
| `GuessAllocation(HexRaysPopupAction)` | Activates `_GuessAllocationVisitor` + shows `_StructAllocChoose` chooser |

`_StructAllocChoose` is a chooser that lists the discovered allocations
(uses `ui.chooser.MyChoose`).

## Tests

Actions are exercised end-to-end in real IDA via idat headless (same
exclusion as the rest of `domain/actions/`). Tests cover the
`get_recognized_shape` pure helper + the chooser build path.

### test_get_recognized_shape (in test_structure_model.py)
1. `test_get_recognized_shape_empty_model_returns_none`
2. `test_get_recognized_shape_builds_udt_from_items`
3. `test_get_recognized_shape_ignores_disabled_items`
4. `test_get_recognized_shape_sorts_by_offset`

### test_workspace.py (NEW)
5. `test_workspace_main_offset_default_zero`
6. `test_workspace_main_offset_settable`

### test_guess_allocation.py (NEW — limited)
7. `test_guess_allocation_visitor_collects_alloc_data` (with mocks for the
   ctree walk; `_manipulate` is a no-op without a real ctree, so the
   visitor's `data` list is the only testable surface — this is documented
   as best-effort).

## Quality gates

- `pytest tests/domain/` — pass
- `mypy --strict` on `scanners.py` + `guess_allocation.py` + `workspace.py` + `structure_model.py` — clean
- `ruff check` — clean
- Full `pytest` — 80%+ coverage

## Out of scope

- The end-to-end ctree walks in `activate()` — verified in real IDA via
  idat headless.
- The structure model collision-merge logic — the original's `__eq__`-based
  merge in `add_row` is non-trivial; we keep the Qt model simple for now
  and document the gap.

## Files

```
src/hexrays_pytools/domain/recon/workspace.py          (+main_offset field)
src/hexrays_pytools/domain/recon/structure_model.py   (+get_recognized_shape)
src/hexrays_pytools/domain/actions/scanners.py        (rewrite 5 actions)
src/hexrays_pytools/domain/actions/guess_allocation.py (port action + visitor)
tests/domain/recon/test_workspace.py                  (NEW — 2 tests)
tests/domain/recon/test_structure_model.py            (+4 tests)
tests/domain/actions/test_guess_allocation.py         (NEW — 1 test)
```