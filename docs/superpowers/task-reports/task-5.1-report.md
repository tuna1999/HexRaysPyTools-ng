# Task 5.1 Report: domain/ctree/recast.py

## Status: DONE

## Commit
- **SHA:** `5b8f128`
- **Subject:** `feat(ctree): add recast logic stubs (RecastItemLeft/Right)`

## Files (4)
| Path | Purpose |
|------|---------|
| `src/hexrays_pytools/domain/ctree/__init__.py` | New package marker (empty), matches sibling-package convention |
| `src/hexrays_pytools/domain/ctree/recast.py` | `recast_item_left`, `recast_item_right` stub functions |
| `tests/domain/ctree/__init__.py` | New test package marker (empty) |
| `tests/domain/ctree/test_recast.py` | 2 unit tests |

## TDD Summary
- **RED:** Wrote `test_recast.py` first; ran pytest -> `ModuleNotFoundError: No module named 'hexrays_pytools.domain.ctree.recast'` (collection error). Confirmed test fails before implementation exists.
- **GREEN:** Wrote `recast.py` per the brief. Both tests pass.
- **REFACTOR:** Applied one mechanical fix required by the ruff gate (see Deviations). No functional deviation.

## Tests (2/2)
| Test | Purpose |
|------|---------|
| `test_recast_left_stub_returns_false` | `recast_item_left(None) is False` |
| `test_recast_right_stub_returns_false` | `recast_item_right(None) is False` |

## Verification Gates
| Gate | Result |
|------|--------|
| `PYTHONPATH=src pytest tests/domain/ctree/test_recast.py -v` | 2/2 passed |
| `mypy --strict src/hexrays_pytools/domain/ctree/recast.py` | Success: no issues found in 1 source file |
| `ruff check src/hexrays_pytools/domain/ctree/recast.py tests/domain/ctree/test_recast.py` | All checks passed |

## Notes / Deviations

### 1. ruff `F401` + `I001` — unused `idaapi` import in the brief's verbatim source

The brief's `recast.py` ships with `import idaapi  # type: ignore[import-not-found]` at module top, but the stub body never references `idaapi`. Ruff flagged:
- `F401` — `idaapi` imported but unused
- `I001` — import block unsorted (consequence of the lone third-party import with a type-ignore comment)

Removed the unused `import idaapi` line. This is the same mechanical-cleanup precedent set by Task 4.3 (removed unused `Callable`) and Task 4.5. No functional change: the stub returns `False` unconditionally; `idaapi` would only be needed once real ctree-walking lands. The module docstring already records that the real implementation is deferred.

The sibling stub `swap_if.py` (Task 5.3) *does* reference `idaapi` indirectly via its docstring's FIX-B8 note but also leaves it unused at runtime — see that report for the parallel decision.

### 2. Package `__init__.py` files added

The brief lists only `recast.py` / `test_recast.py`, but every sibling package under `src/hexrays_pytools/domain/` and `tests/domain/` ships an empty `__init__.py` (verified: `actions/`, `browser/`, `graph/`, `recon/`, `scanner/`, `templated/`, `til/`, `types/`, `xrefs/`). Without them, `from hexrays_pytools.domain.ctree.recast import ...` still resolves (Python 3 namespace packages), but the project's own convention is explicit package markers. Added empty `__init__.py` to both `ctree` dirs to match. Included in this first ctree commit so Tasks 5.2-5.4 only stage their own files.

## Notes for Downstream Tasks
- **Tasks 5.2-5.4:** Same package, add `rename.py`, `swap_if.py`, `negative_offsets.py` + tests. No further `__init__.py` work needed.
- **Tasks 5.5/5.6 (actions/recast_action.py, rename_action.py):** These action wrappers currently have `activate() -> pass`. Once `recast_item_left/right` grow real bodies, wire them: `recast_item_left(ctx.item)` inside `RecastItemLeft.activate`.
