# Task 2.1 Report: domain/types/tinfo_utils.py

## Status: DONE_WITH_CONCERNS

Two deviations from the brief's verbatim content, both minimal and
documented below. All verification gates pass.

## Commit

- SHA: `bb3326290784ae25d1de626a1c2518c6707e9235`
- Subject: `feat(types): add tinfo_utils (get_ordinal, get_nice_pointed_object)`
- Files: 4 created, 70 insertions

## Files Created

1. `src/hexrays_pytools/domain/types/__init__.py` (empty)
2. `src/hexrays_pytools/domain/types/tinfo_utils.py`
3. `tests/domain/types/__init__.py` (empty)
4. `tests/domain/types/test_tinfo_utils.py`

## TDD Summary

### RED (confirmed)

Ran the brief's **original** test verbatim (without the `MagicMock`
import). Result:

```
tests/domain/types/test_tinfo_utils.py::test_get_ordinal_for_udt PASSED  [ 33%]
tests/domain/types/test_tinfo_utils.py::test_get_ordinal_for_non_udt PASSED [ 66%]
tests/domain/types/test_tinfo_utils.py::test_get_nice_pointed_object_strips_p FAILED [100%]

E   NameError: name 'MagicMock' is not defined
========================= 1 failed, 2 passed in 0.05s =========================
```

The brief itself documents this as a known internal bug and prescribes
the fix (add `from unittest.mock import MagicMock`). Confirmed the RED
state exists *only* because of that missing import, not because of the
implementation.

### GREEN (after applying the brief-prescribed import fix + lint fixes)

```
tests/domain/types/test_tinfo_utils.py::test_get_ordinal_for_udt PASSED            [ 33%]
tests/domain/types/test_tinfo_utils.py::test_get_ordinal_for_non_udt PASSED        [ 66%]
tests/domain/types/test_tinfo_utils.py::test_get_nice_pointed_object_strips_p PASSED [100%]

============================== 3 passed in 0.03s ==============================
```

### Full suite (regression check)

```
TOTAL                                               264     47    82%
Required test coverage of 80% reached. Total coverage: 82.20%
============================= 61 passed in 0.21s ==============================
```

### mypy --strict

```
$ python -m mypy --strict src/hexrays_pytools/domain/types/tinfo_utils.py
Success: no issues found in 1 source file
```

### ruff

```
$ python -m ruff check src/hexrays_pytools/domain/types/ tests/domain/types/
All checks passed!
```

## Deviations (DONE_WITH_CONCERNS)

### 1. Brief-internal bug: missing `MagicMock` import (brief-prescribed fix)

The brief's `test_tinfo_utils.py` block uses `MagicMock()` in
`test_get_nice_pointed_object_strips_p` but never imports it. The
brief's "Note" section explicitly calls this out and prescribes the
fix. Applied as documented:

```python
from unittest.mock import MagicMock
```

This is a brief bug, not an implementation choice. Documented for
traceability.

### 2. mypy --strict and ruff lint fixes (minimal, convention-aligned)

The brief's verification step runs `mypy --strict` and `ruff check`.
The verbatim source fails both. Applied the same minimal-fix pattern
already established by **Task 1.1 (`arch.py`)** — the directly analogous
IDA-wrapper module — as documented in
`docs/superpowers/task-reports/task-1.1-report.md`.

#### `tinfo_utils.py` — mypy

Verbatim source produced:

```
tinfo_utils.py:11: error: Unused "type: ignore" comment  [unused-ignore]
tinfo_utils.py:14: error: Returning Any from function declared to return "int"  [no-any-return]
tinfo_utils.py:16: error: Returning Any from function declared to return "int"  [no-any-return]
tinfo_utils.py:20: error: Unused "type: ignore" comment  [unused-ignore]
```

Root cause: the brief annotates both function signatures with
`# type: ignore[name-defined]`, but with `import idaapi  # type: ignore[import-not-found]`
already in place, mypy 2.1 treats `idaapi.tinfo_t` as a resolvable
name — making those per-signature ignores unused
(`warn_unused_ignores = true` is set in `pyproject.toml`).
Independently, the two `tinfo.get_ordinal()` returns are `Any` under the
untyped `idaapi`, triggering `[no-any-return]`.

Fixes (mirror the `arch.py` precedent of `int(...)` wrapping for `int`
returns):

- Removed both `# type: ignore[name-defined]` from function signatures.
- Wrapped the two `get_ordinal()` returns in `int(...)`.
- The `get_nice_pointed_object` returns are `idaapi.tinfo_t` (a typed
  class once the import-ignore applies), so no `no-any-return` ignore is
  needed there — mypy 2.1 confirmed clean without annotation.

Logic is byte-for-byte identical to the brief.

#### `tinfo_utils.py` — ruff

- `I001` import block: added the missing blank line between
  `from __future__ import annotations` and `import idaapi`.

#### `test_tinfo_utils.py` — ruff

- `F841` unused variable: removed `named = MagicMock()` (the variable
  was assigned but never used; only `tinfo2` is needed to drive
  `get_named_type.return_value = True`).
- `I001` import order: ruff requires imported names alphabetized —
  changed `get_ordinal, get_nice_pointed_object` to
  `get_nice_pointed_object, get_ordinal`.

### Alternatives considered and rejected

- **Keep verbatim brief source and skip mypy/ruff** — rejected; the
  brief's own verification section requires both to pass, and the repo's
  `pyproject.toml` enables `warn_unused_ignores = true` and a broad
  ruff rule set. Shipping known-failing lint would break CI.
- **Add `[[tool.mypy]] ignore_missing_imports = true`** — rejected in
  Task 1.1 for the same reason: broader blast radius; the scoped
  `# type: ignore[import-not-found]` on the single `idaapi` import is
  the established repo pattern.
- **Add an `idaapi.pyi` stub** — out of scope (would belong in a
  dedicated stubs task, as noted in the Task 1.1 report).

## Self-Review

- [x] Four files created per brief (2 source, 2 test, including both `__init__.py`)
- [x] RED confirmed (via the brief's own missing-import bug)
- [x] GREEN: 3/3 tests pass
- [x] mypy --strict: clean
- [x] ruff: clean
- [x] Full suite regression: 61 passed, 82.20% coverage (gate holds)
- [x] Commit message matches brief verbatim
- [x] All deviations documented
- [x] No mutation of inputs (pure functions; `tinfo` is only read)
- [x] No hardcoded secrets, no debug statements
- [x] Error handling: `get_nice_pointed_object` guards the falsy
      `inner` return (matches brief logic)

## Notes for downstream tasks

- `tinfo_utils.get_ordinal` and `get_nice_pointed_object` are now
  importable from `hexrays_pytools.domain.types.tinfo_utils` for Tasks
  2.2 (`func_type.py`) and 2.3 (`udt_builder.py`).
- The `[import-not-found]` on `import idaapi` is the standard pattern;
  downstream IDA-wrapper modules in `domain/` should follow it plus
  `int(...)` / typed wrapping as needed.
