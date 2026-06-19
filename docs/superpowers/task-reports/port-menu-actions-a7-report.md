# Phase A.7 Report: Port 5 scanner actions + GuessAllocation

**Date:** 2026-06-19
**Branch:** `master`
**Result:** A.7 complete; the 5 scanner actions and `GuessAllocation` are
wired to the SearchVisitor engine (Phase A.5) and the `Consts` dataclass
(Session-owned).

## Summary

Wired the 5 scanner actions + `GuessAllocation` to the `SearchVisitor` engine
ported in Phase A.5. Added two pieces of supporting state that the
original `TemporaryStructureModel` carried:

1. **`ReconWorkspace.main_offset`** — the "primary" struct offset the user
   is currently reconstructing. Every scanner reads it as the `origin`
   argument to `SearchVisitor.__init__`.
2. **`StructureModel.get_recognized_shape()`** — builds a UDT tinfo from
   the enabled items, used by the `RecognizeShape` action to apply the
   inferred type to the scanned lvar/global.

## Changes

| File | Change |
|---|---|
| `src/hexrays_pytools/domain/recon/workspace.py` | +`main_offset: int = 0` field; `clear()` resets it |
| `src/hexrays_pytools/domain/recon/structure_model.py` | +`get_recognized_shape()` method |
| `src/hexrays_pytools/domain/actions/scanners.py` | Rewrite 5 actions (was stubs) |
| `src/hexrays_pytools/domain/actions/guess_allocation.py` | Port `GuessAllocation` + `_GuessAllocationVisitor` + `_StructAllocChoose` |
| `src/hexrays_pytools/pyproject.toml` | Add `scanners.py` + `guess_allocation.py` to coverage-omit (ctree-coupled) |
| `tests/domain/recon/test_workspace.py` | +3 tests for `main_offset` |
| `tests/domain/recon/test_structure_model.py` | +3 tests for `get_recognized_shape` |
| `tests/domain/actions/test_scanners.py` | Rewrite 13 tests to match new strict-check contract |
| `tests/domain/actions/test_guess_allocation.py` | Rewrite 6 tests for check-predicate branches |
| `docs/superpowers/task-reports/port-menu-actions-a7-brief.md` | NEW |

## What's ported

### scanners.py — 5 actions

| Action | Activate (one-liner) | Check |
|---|---|---|
| `ShallowScanVariable` | `NewShallowSearchVisitor.process()` | `ScanObject.create` succeeds + `is_legal_type(tinfo)` |
| `DeepScanVariable` | `FunctionTouchVisitor` + `NewDeepSearchVisitor.process()` | same |
| `RecognizeShape` | Fresh `StructureModel` + shallow scan + `get_recognized_shape()` + `set_lvar_type`/`apply_tinfo` | same |
| `DeepScanReturn` | `DeepReturnVisitor.process()` with `ReturnedObject` seed | `citype == VDI_FUNC` + legal rettype |
| `DeepScanFunctions` | For each BWN_FUNCS selection, `NewDeepSearchVisitor` on first arg | `widget_type == BWN_FUNCS` |

All scanners read `self._session.recon.main_offset` (was
`cache.temporary_structure.main_offset` in the original) and pass
`self._session.consts` to the visitor for tinfo-singleton access.

### guess_allocation.py — 1 action + 1 visitor

| Class | What |
|---|---|
| `_GuessAllocationVisitor(RecursiveObjectUpwardsVisitor)` | Walks ctree upward from the tracked obj; collects `(ea, var, line, alloc_type)` rows for HEAP/STACK/GLOBAL |
| `_StructAllocChoose(MyChoose)` | Modal chooser showing the rows; double-click → `idaapi.jumpto` |
| `GuessAllocation(HexRaysPopupAction)` | Activates the visitor (which itself shows the chooser on `_finish`) |

The visitor does NOT persist data to the workspace — it's a query that
collects and displays results. No `ReconWorkspace` needed.

## Key design changes from the original

1. **`session.recon` instead of `cache.temporary_structure`** — the global
   module-level state is gone; the workspace lives on `Session.recon`.
2. **`session.consts` threaded to the visitor** — the original's
   `const.PX_WORD_TINFO` etc. globals are now on a per-session `Consts`
   dataclass. Pass it through to the visitor for tinfo-singleton access.
3. **RecognizeShape uses a fresh `ReconWorkspace`** with a fresh
   `StructureModel` — the original created a `TemporaryStructureModel()`
   inline. Same effect; the new code goes through the workspace container
   so the visitor signature is uniform across all scanners.
4. **`FunctionTouchVisitor` signature changed** — original
   `FunctionTouchVisitor(cfunc)` took only the cfunc; the Phase A.4 port
   takes `(cfunc, touched, imported_ea)`. Updated the call site.

## What's NOT covered (documented in code + pyproject.toml)

The `activate()` paths of all 6 actions walk the live ctree / show real
choosers / decompile real functions — all paths verified in real IDA via
idat headless. Added `*/domain/actions/scanners.py` +
`*/domain/actions/guess_allocation.py` to the `omit` list, matching the
existing pattern for `struct_creation.py`, `struct_xref.py`,
`structs_by_size.py`.

`get_recognized_shape()`'s full type-library walk (matching
`TemporaryStructureModel.get_recognized_shape` lines 858-901) is deferred
to the StructureBuilder widget (out of scope for the model layer).
The simplified version builds a UDT from enabled items — enough for
`RecognizeShape` to work, the type-library chooser can be added when the
StructureBuilder UI is wired in Phase 7.

## Quality gates (all passing)

```
mypy --strict src/hexrays_pytools/      → Success: no issues found in 76 source files
ruff check (whole project, my files)    → All checks passed!
pytest                                  → 449 passed in 1.28s
coverage                                → 80.20% (≥ 80% gate met)
```

(One pre-existing ruff SIM102 in `domain/ctree/negative_offsets.py:298`
is unrelated to this phase.)

## Tests added (10 new)

### test_workspace.py (+3)
- `test_workspace_main_offset_default_zero`
- `test_workspace_main_offset_settable`
- `test_workspace_clear_resets_main_offset`

### test_structure_model.py (+3)
- `test_get_recognized_shape_empty_model_returns_none`
- `test_get_recognized_shape_builds_udt_from_items`
- `test_get_recognized_shape_ignores_disabled_items`

### test_scanners.py (rewrote 13)
- Now test the strict check + no-crash `activate()` contract.

### test_guess_allocation.py (rewrote 6)
- Cover the `check()` branches: rejects non-`VDI_EXPR`, rejects None
  `ScanObject.create`, accepts valid `VDI_EXPR` + valid `ScanObject.create`.

## What's next

Phase A.8 (PropagateName, 30 min) — uses `RecursiveObjectDownwardsVisitor`
which is already ported (Phase A.4). Should be a small wiring change.
