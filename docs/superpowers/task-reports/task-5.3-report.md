# Task 5.3 Report: domain/ctree/swap_if.py

## Status: DONE

## Commit
- **SHA:** `8814d1c`
- **Subject:** `feat(ctree): add swap_if logic (B8 fix: refresh_view not refresh_ctext)`

## Files (2)
| Path | Purpose |
|------|---------|
| `src/hexrays_pytools/domain/ctree/swap_if.py` | `swap_if_then_else` stub function; B8 fix documented |
| `tests/domain/ctree/test_swap_if.py` | 1 unit test |

## Function (1)
| Function | Behavior |
|----------|----------|
| `swap_if_then_else(hx_view)` | Returns `False` if `hx_view is None`; otherwise stub-returns `False`. Real impl (invert condition, swap branches, `refresh_view(True)`) deferred. |

## TDD Summary
- **RED:** Wrote `test_swap_if.py` first; ran pytest -> `ModuleNotFoundError: No module named 'hexrays_pytools.domain.ctree.swap_if'`. Confirmed test fails before implementation exists.
- **GREEN:** Wrote `swap_if.py` per the brief. Test passes.
- **REFACTOR:** Applied one mechanical ruff fix (see Deviations). No functional deviation.

## Tests (1/1)
| Test | Purpose |
|------|---------|
| `test_swap_if_none_returns_false` | `swap_if_then_else(None) is False` exercises the `None` guard |

## Verification Gates
| Gate | Result |
|------|--------|
| `PYTHONPATH=src pytest tests/domain/ctree/test_swap_if.py -v` | 1/1 passed |
| `mypy --strict src/hexrays_pytools/domain/ctree/swap_if.py` | Success: no issues found in 1 source file |
| `ruff check src/hexrays_pytools/domain/ctree/swap_if.py tests/domain/ctree/test_swap_if.py` | All checks passed |

## Notes / Deviations

### 1. ruff `F401` + `I001` — unused `idaapi` import in the brief's verbatim source

Same situation as Task 5.1 (`recast.py`). The brief ships `import idaapi  # type: ignore[import-not-found]`, but the stub body never references `idaapi` — the B8 fix (`hx_view.refresh_view(True)`) is documented in the docstring but the actual call hasn't landed yet. Ruff flagged:
- `F401` — `idaapi` imported but unused
- `I001` — import block unsorted (consequence of the lone third-party import)

Removed the unused `import idaapi` line. **The B8 documentation is fully preserved** in both the module docstring and the function docstring (`FIX B8: was hx_view.refresh_ctext() ... now hx_view.refresh_view(True)`). When the real implementation lands and actually calls `hx_view.refresh_view(True)`, the `idaapi` import should be re-evaluated — note that `refresh_view` is a method on the `vdui_t` (`hx_view`) instance, not a module-level `idaapi` call, so `idaapi` may still not be needed at that point.

This matches the precedent set by Task 5.1 and the earlier mechanical cleanups in Tasks 4.3 / 4.5.

### 2. B8 fix status

The B8 fix itself (using `refresh_view(True)` instead of the removed `refresh_ctext()`) is **documented but not yet exercised** — the stub returns `False` before reaching any refresh call. The actual behavioral fix lands when the real branch-swap logic is implemented (out of scope for this rewrite per the brief: "Real implementation requires full ctree walking"). The docstring is the contract; the action-layer wrapper (`SwapThenElse` in `actions/swap_if_action.py`) will call `swap_if_then_else(hx_view)` once wired.

## Notes for Downstream Tasks
- **Task 5.7 (actions/swap_if_action.py):** `SwapThenElse.activate()` is currently `pass`. Wire it to call `swap_if_then_else(hx_view)` and propagate the bool return.
- **B8 verification:** Once the real impl lands, add a test that mocks `hx_view` and asserts `hx_view.refresh_view(True)` is called (and `refresh_ctext` is never referenced). The current `None`-guard test only covers the early-return branch.
