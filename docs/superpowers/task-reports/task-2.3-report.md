# Task 2.3 Report: domain/types/udt_builder.py

## Status: DONE_WITH_CONCERNS

Two deviations from the brief's verbatim content, both minimal and
documented below. All verification gates pass.

## Commit

- SHA: `8fda23c`
- Subject: `feat(types): add udt_builder (create_padding_udt_member)`
- Files: 2 created, 60 insertions

## Files Created

1. `src/hexrays_pytools/domain/types/udt_builder.py`
2. `tests/domain/types/test_udt_builder.py`

(`src/hexrays_pytools/domain/types/__init__.py` and
`tests/domain/types/__init__.py` already exist from Task 2.1.)

## TDD Summary

### RED (confirmed)

Ran the brief's test against the absence of the implementation. With
`udt_builder.py` not yet created:

```
tests\domain\types\test_udt_builder.py:4: in <module>
    from hexrays_pytools.domain.types.udt_builder import create_padding_udt_member
E   ModuleNotFoundError: No module named 'hexrays_pytools.domain.types.udt_builder'
=========================== short test summary info ===========================
ERROR tests/domain/types/test_udt_builder.py
1 error in 0.14s
```

Collection error confirms the RED state: the test cannot import a module
that does not exist.

### GREEN (after creating impl + applying the brief-prescribed import fix + lint fixes)

```
tests/domain/types/test_udt_builder.py::test_create_padding_member_name PASSED   [ 33%]
tests/domain/types/test_udt_builder.py::test_create_padding_member_offset PASSED [ 66%]
tests/domain/types/test_udt_builder.py::test_create_padding_member_size PASSED   [100%]

============================== 3 passed in 0.03s ==============================
```

### Full suite (regression check)

```
TOTAL                                               299     52    83%
Required test coverage of 80% reached. Total coverage: 82.61%
============================= 67 passed in 0.24s ==============================
```

### mypy --strict

```
$ python -m mypy --strict src/hexrays_pytools/domain/types/udt_builder.py
Success: no issues found in 1 source file
```

### ruff

```
$ python -m ruff check src/hexrays_pytools/domain/types/udt_builder.py tests/domain/types/test_udt_builder.py
All checks passed!
```

## Deviations (DONE_WITH_CONCERNS)

### 1. Brief-internal bug: missing `MagicMock` import (brief-prescribed fix)

The brief's `test_udt_builder.py` block uses `MagicMock()` in all three
tests but never imports it. The brief's "Add" line explicitly calls this
out and prescribes the fix:

```python
from unittest.mock import MagicMock
```

Applied as documented. This is a brief bug, not an implementation choice.
Documented for traceability.

### 2. mypy --strict and ruff lint fixes (minimal, convention-aligned)

The brief's verification step runs `mypy --strict` and `ruff check`.
The verbatim source fails both. Applied the same minimal-fix pattern
already established by **Task 2.1 (`tinfo_utils.py`)** and **Task 2.2
(`func_type.py`)** — the directly analogous IDA-wrapper modules — as
documented in `docs/superpowers/task-reports/task-2.1-report.md` and
`task-2.2-report.md`.

#### `udt_builder.py` — mypy

Verbatim source produced:

```
udt_builder.py:12: error: Unused "type: ignore" comment  [unused-ignore]
udt_builder.py:19: error: Unused "type: ignore" comment  [unused-ignore]
Found 2 errors in 1 file (checked 1 source file)
```

Root cause (identical to Tasks 2.1 / 2.2): the brief annotates the
function signature with `# type: ignore[name-defined]` and the
`create_array(...)` call with `# type: ignore[attr-defined]`, but with
`import idaapi  # type: ignore[import-not-found]` already in place,
mypy 2.1 treats `idaapi.udt_member_t` and `idaapi.tinfo_t.create_array`
as resolvable names — making those ignores unused
(`warn_unused_ignores = true` is set in `pyproject.toml`).

Fixes (mirror the Task 2.1 / 2.2 precedent):

- Removed `# type: ignore[name-defined]` from the function signature.
- Removed `# type: ignore[attr-defined]` from the `create_array(...)`
  call.

Logic is byte-for-byte identical to the brief. (Unlike Task 2.2's
`create_func(...)`, this function returns the `member` object directly
rather than a bool from an `idaapi` call, so no `bool(...)` wrapping is
needed here.)

#### `udt_builder.py` — ruff

- `I001` import block: added the missing blank line between
  `from __future__ import annotations` and `import idaapi`.

#### `test_udt_builder.py` — ruff

- `F841` unused variable: removed `result = ` in
  `test_create_padding_member_name` (the variable was assigned but never
  used; only `member.name` is asserted). Same precedent as Task 2.1's
  removal of the unused `named` variable.

### Alternatives considered and rejected

- **Keep verbatim brief source and skip mypy/ruff** — rejected; the
  brief's own verification section requires both to pass, and the repo's
  `pyproject.toml` enables `warn_unused_ignores = true` and a broad
  ruff rule set. Shipping known-failing lint would break CI.
- **Add `[[tool.mypy]] ignore_missing_imports = true`** — rejected in
  Tasks 1.1 / 2.1 / 2.2 for the same reason: broader blast radius; the
  scoped `# type: ignore[import-not-found]` on the single `idaapi`
  import is the established repo pattern.
- **Add an `idaapi.pyi` stub** — out of scope (would belong in a
  dedicated stubs task, as noted in the Task 1.1 report).

## Self-Review

- [x] Two files created per brief (impl + test)
- [x] RED confirmed (ModuleNotFoundError with impl absent)
- [x] GREEN: 3/3 tests pass
- [x] mypy --strict: clean
- [x] ruff check: clean (both files)
- [x] Full suite: 67 passed, coverage 82.61% (>= 80% gate)
- [x] Commit message matches brief verbatim:
      `feat(types): add udt_builder (create_padding_udt_member)`
- [x] Only the two specified files committed (matching Task 2.1 / 2.2
      scope)
- [x] No mutation of shared/global state — pure function over `idaapi`
- [x] Logic identical to brief; only type-ignore comments and a dropped
      unused local differ

## Notes

- The `udt_builder.py` deviations are mechanical and identical in shape
  to Tasks 2.1 / 2.2's already-reviewed deviations. The lint-fix
  precedent is now established across four IDA-wrapper modules (arch,
  tinfo_utils, func_type, udt_builder). Subsequent tasks wrapping
  `idaapi` should apply the same pattern proactively.
- `create_padding_udt_member` is now importable from
  `hexrays_pytools.domain.types.udt_builder` for downstream recon /
  scanner tasks (e.g. Task 2.6 `ctree_utils`, Task 2.7
  `member_extractor`) that need to synthesize gap members.
