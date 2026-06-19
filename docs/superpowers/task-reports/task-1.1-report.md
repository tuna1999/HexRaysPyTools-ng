# Task 1.1 Report: infra/arch/arch.py

## Status

**DONE_WITH_CONCERNS** — All gates green, but a Phase 0 infrastructure bug
(`tools/mock_ida.py`) had to be fixed in a prerequisite commit for the brief's
tests to pass, and the brief's verification commands required three minimal
deviations (documented below).

## Commits

| SHA | Subject |
|-----|---------|
| `d28e8f5` | `fix(test): cache mock attributes so return_value/call_args persist` |
| `a298887` | `feat(infra): add arch.is_code_ea and arch.get_ptr (ARM thumb)` |

The arch commit `a298887` carries the brief's exact message. The mock fix
(`d28e8f5`) is a separate prerequisite commit because it is logically a Phase 0
infra fix, not part of Task 1.1's deliverable. Both commits are independently
green.

## TDD Summary

1. **RED** — Created the three `__init__.py` files and `tests/infra/test_arch.py`
   (no implementation yet). Ran `pytest tests/infra/test_arch.py -v` and observed
   the expected failure: `ModuleNotFoundError: No module named
   'hexrays_pytools.infra.arch.arch'` (collection error, 1 error).

2. **Implementation** — Created `src/hexrays_pytools/infra/arch/arch.py` with
   the brief's logic verbatim.

3. **Initial GREEN attempt FAILED (4/4)** — All four tests failed because the
   Phase 0 `tools/mock_ida.py` `_MockIdaModule.__getattr__` returned a **fresh**
   `MagicMock` on every attribute access (no caching). This meant:
   - `idaapi.is_code.return_value = True` set `return_value` on a throwaway mock
     that was discarded immediately — the next `idaapi.is_code(...)` read an
     unconfigured mock. (`test_is_code_ea_returns_bool`)
   - `idaapi.get_full_flags.call_args` was `None` because the call went to a
     different mock instance than the one being inspected.
     (`test_is_code_ea_strips_arm_thumb_bit`)
   - `assert_called()` failed for the same identity mismatch.
     (`test_get_ptr_x86_uses_wide_dword`, `test_get_ptr_x64_uses_qword`)

   This is a genuine defect in the mock: it also breaks `reset()`'s documented
   contract (it iterates `dir(mod)` expecting attribute stability). Fixing the
   mock is strictly more correct than rewriting the brief's tests around the
   broken behavior, so the mock was fixed.

4. **GREEN after mock fix** — `4 passed in 0.02s`. Full suite: `35 passed`,
   `95.15%` coverage (gate is 80%). `arch.py` at 100%.

## Verification Results

| Gate | Command | Result |
|------|---------|--------|
| Tests | `PYTHONPATH=src pytest tests/infra/test_arch.py -v` | 4 passed |
| Full suite | `PYTHONPATH=src pytest tests/` | 35 passed, 95.15% cov |
| Types | `mypy --strict src/hexrays_pytools/infra/arch/arch.py` | Success: no issues |
| Types (full src) | `mypy --strict src/hexrays_pytools/` | Success: no issues (10 files) |
| Lint | `ruff check src/hexrays_pytools/infra/ tests/infra/` | All checks passed! |

## Deviations from the Brief (Concerns)

### 1. `tools/mock_ida.py` caching fix (prerequisite, separate commit)

**Brief expectation:** Tests use the mock infrastructure from Phase 0 (Task 0.8)
unchanged.

**Reality:** `_MockIdaModule.__getattr__` did not cache attributes, so the
brief's tests could not pass. Fixed by caching each synthesized `MagicMock` in
`self.__dict__`. The fix:

```python
def __getattr__(self, name: str) -> Any:
    if name.startswith("_"):
        raise AttributeError(name)
    mock = MagicMock(name=f"ida.{self.__class__.__name__}.{name}")
    self.__dict__[name] = mock
    return mock
```

This matches standard module-mock semantics (an attribute resolves to the same
object on repeated access) and makes `reset()` work as documented. Committed as
`d28e8f5`, before the arch commit. Existing `tests/pure/` (31 tests) still pass.

### 2. `arch.py` mypy deviations (minimal type-safety additions)

The brief's verification step `mypy --strict src/hexrays_pytools/infra/arch/arch.py`
fails on the verbatim source with four errors:

```
arch.py:8:  error: Cannot find implementation or library stub for module named "idaapi"  [import-not-found]
arch.py:13: error: Returning Any from function declared to return "bool"  [no-any-return]
arch.py:20: error: Returning Any from function declared to return "int"   [no-any-return]
arch.py:21: error: Returning Any from function declared to return "int"   [no-any-return]
```

`idaapi` has no type stubs (it is a SWIG module provided by IDA at runtime).
Applied the minimal fixes:

- `import idaapi  # type: ignore[import-not-found]`
- wrapped the three returns in `bool(...)` / `int(...)` to satisfy
  `[no-any-return]` and to make the conversion explicit.

Logic is byte-for-byte identical to the brief. The alternatives considered and
rejected:

- **Adding `[[tool.mypy]] ignore_missing_imports = true` to pyproject.toml** —
  broader blast radius (suppresses the import error project-wide); rejected in
  favor of a scoped `# type: ignore` on the one line that needs it.
- **Adding a `idaapi.pyi` stub** — out of scope for Task 1.1 (would belong in a
  dedicated stubs task); the `# type: ignore` is the standard pattern for
  runtime-only IDA imports.

### 3. `test_arch.py` ruff deviations (minimal lint fixes)

The brief's test as written produced two ruff errors:

- `F401` — `from unittest.mock import MagicMock` was unused (the test uses
  `__import__("idaapi")` instead of the imported `MagicMock`). Removed the
  unused import.
- `I001` — ruff wanted the imported names alphabetized. Changed
  `import is_code_ea, get_ptr` to `import get_ptr, is_code_ea`.

No behavioral change; the brief's note explicitly permits minimal fixes of this
kind ("If brief has lint issues (e.g., the `__import__` pattern), apply minimal
fixes and document").

## Files Created

| Path | Purpose |
|------|---------|
| `src/hexrays_pytools/infra/__init__.py` | Package marker (empty) |
| `src/hexrays_pytools/infra/arch/__init__.py` | Package marker (empty) |
| `src/hexrays_pytools/infra/arch/arch.py` | `is_code_ea`, `get_ptr` |
| `tests/infra/__init__.py` | Package marker (empty) |
| `tests/infra/test_arch.py` | 4 tests for arch module |

## Files Modified

| Path | Change |
|------|--------|
| `tools/mock_ida.py` | `_MockIdaModule.__getattr__` now caches mocks in `__dict__` |

## Self-Review Checklist

- [x] Files created per brief (5 files: 3 `__init__.py` + arch.py + test_arch.py)
- [x] 4 tests pass (RED confirmed first, then GREEN)
- [x] `mypy --strict` clean (with documented minimal type fixes)
- [x] `ruff check` clean (with documented minimal lint fixes)
- [x] Single arch commit with the exact message from the brief (`a298887`)
- [x] Mock fix in a separate prerequisite commit (`d28e8f5`)
- [x] Full suite green (35 passed), coverage 95.15% (gate 80%)
- [x] No regressions in existing `tests/pure/` (31 passed)
