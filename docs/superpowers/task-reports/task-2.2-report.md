# Task 2.2 Report: domain/types/func_type.py

## Status: DONE_WITH_CONCERNS

Two deviations from the brief's verbatim content, both minimal and
documented below. All verification gates pass.

## Commit

- SHA: `4d447b6434545f3f3b5e6fccb0da052751d72bd5`
- Subject: `feat(types): add func_type (get/set func arg, return)`
- Files: 2 created, 99 insertions

## Files Created

1. `src/hexrays_pytools/domain/types/func_type.py`
2. `tests/domain/types/test_func_type.py`

(`src/hexrays_pytools/domain/types/__init__.py` and
`tests/domain/types/__init__.py` already exist from Task 2.1.)

## TDD Summary

### RED (confirmed)

Ran the brief's test against the absence of the implementation. With
`func_type.py` temporarily removed:

```
tests\domain\types\test_func_type.py:4: in <module>
    from hexrays_pytools.domain.types.func_type import ...
E   ModuleNotFoundError: No module named 'hexrays_pytools.domain.types.func_type'
=========================== short test summary info ===========================
ERROR tests/domain/types/test_func_type.py
1 error in 0.10s
```

Collection error confirms the RED state: the test cannot import a module
that does not exist.

### GREEN (after creating impl + applying the brief-prescribed import fix + lint fixes)

```
tests/domain/types/test_func_type.py::test_get_func_argument_info_returns_name_and_type PASSED [ 33%]
tests/domain/types/test_func_type.py::test_set_func_argument_modifies_type PASSED        [ 66%]
tests/domain/types/test_func_type.py::test_set_func_return_modifies_rettype PASSED       [100%]

============================== 3 passed in 0.03s ==============================
```

### Full suite (regression check)

```
TOTAL                                               288     52    82%
Required test coverage of 80% reached. Total coverage: 81.94%
============================= 64 passed in 0.22s ==============================
```

### mypy --strict

```
$ python -m mypy --strict src/hexrays_pytools/domain/types/func_type.py
Success: no issues found in 1 source file
```

### ruff

```
$ python -m ruff check src/hexrays_pytools/domain/types/func_type.py tests/domain/types/test_func_type.py
All checks passed!
```

## Deviations (DONE_WITH_CONCERNS)

### 1. Brief-internal bug: missing `MagicMock` import (brief-prescribed fix)

The brief's `test_func_type.py` block uses `MagicMock()` in all three
tests but never imports it. The brief's "NOTE" section explicitly calls
this out and prescribes the fix:

```python
from unittest.mock import MagicMock
```

Applied as documented (ruff then expanded the import block into
parenthesized form per `I001`). This is a brief bug, not an
implementation choice. Documented for traceability.

### 2. mypy --strict and ruff lint fixes (minimal, convention-aligned)

The brief's verification step runs `mypy --strict` and `ruff check`.
The verbatim source fails both. Applied the same minimal-fix pattern
already established by **Task 2.1 (`tinfo_utils.py`)** — the directly
analogous IDA-wrapper module — as documented in
`docs/superpowers/task-reports/task-2.1-report.md`, which in turn
mirrors **Task 1.1 (`arch.py`)**.

#### `func_type.py` — mypy

Verbatim source produced:

```
func_type.py:10: error: Unused "type: ignore" comment  [unused-ignore]
func_type.py:24: error: Unused "type: ignore" comment  [unused-ignore]
func_type.py:32: error: Unused "type: ignore" comment  [unused-ignore]
func_type.py:32: error: Returning Any from function declared to return "bool"  [no-any-return]
func_type.py:32: note: Error code "no-any-return" not covered by "type: ignore[attr-defined]" comment
func_type.py:35: error: Unused "type: ignore" comment  [unused-ignore]
func_type.py:41: error: Unused "type: ignore" comment  [unused-ignore]
func_type.py:41: error: Returning Any from function declared to return "bool"  [no-any-return]
func_type.py:41: note: Error code "no-any-return" not covered by "type: ignore[attr-defined]" comment
Found 7 errors in 1 file (checked 1 source file)
```

Root cause (identical to Task 2.1): the brief annotates all three
function signatures with `# type: ignore[name-defined]`, but with
`import idaapi  # type: ignore[import-not-found]` already in place,
mypy treats `idaapi.tinfo_t` as a resolvable name — making those
per-signature ignores unused (`warn_unused_ignores = true` is set in
`pyproject.toml`). Independently, the two `create_func(...)` returns
are `Any` under the untyped `idaapi`, triggering `[no-any-return]`.

Fixes (mirror the Task 2.1 precedent — `bool(...)` wrapping for `bool`
returns, the same shape as Task 2.1's `int(...)` wrapping):

- Removed all three `# type: ignore[name-defined]` from function
  signatures.
- Removed both `# type: ignore[attr-defined]` from the
  `create_func(...)` calls.
- Wrapped both `create_func(...)` returns in `bool(...)`.

Logic is byte-for-byte identical to the brief.

#### `func_type.py` — ruff

- `I001` import block: added the missing blank line between
  `from __future__ import annotations` and `import idaapi`.

#### `test_func_type.py` — ruff

- `I001` import block: `--fix` expanded the `MagicMock` import and the
  three-name `func_type` import into parenthesized form per ruff's
  line-length and sorting rules.

### Alternatives considered and rejected

- **Keep verbatim brief source and skip mypy/ruff** — rejected; the
  brief's own verification section requires both to pass, and the repo's
  `pyproject.toml` enables `warn_unused_ignores = true` and a broad
  ruff rule set. Shipping known-failing lint would break CI.
- **Add `[[tool.mypy]] ignore_missing_imports = true`** — rejected in
  Tasks 1.1 / 2.1 for the same reason: broader blast radius; the scoped
  `# type: ignore[import-not-found]` on the single `idaapi` import is
  the established repo pattern.
- **Add an `idaapi.pyi` stub** — out of scope (would belong in a
  dedicated stubs task, as noted in the Task 1.1 report).

## Self-Review

- [x] Two files created per brief (impl + test)
- [x] RED confirmed (ModuleNotFoundError with impl absent)
- [x] GREEN: 3/3 tests pass
- [x] mypy --strict: clean
- [x] ruff check: clean (both files)
- [x] Full suite: 64 passed, coverage 81.94% (>= 80% gate)
- [x] Commit message matches brief verbatim:
      `feat(types): add func_type (get/set func arg, return)`
- [x] Only the two specified files committed (matching Task 2.1 scope)
- [x] No mutation of shared/global state — all functions are pure
      wrappers over `idaapi`
- [x] Logic identical to brief; only type-ignore comments and `bool()`
      wrapping differ

## Notes

- The `func_type.py` deviations are mechanical and identical in shape to
  Task 2.1's already-reviewed deviations. The lint-fix precedent is now
  established across three IDA-wrapper modules (arch, tinfo_utils,
  func_type). Subsequent tasks wrapping `idaapi` should apply the same
  pattern proactively.
