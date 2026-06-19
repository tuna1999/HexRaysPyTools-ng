# Task 2.4 Report: domain/scanner/visitor_base.py

- **Status:** DONE_WITH_CONCERNS
- **Commit:** (see git log after commit)
- **Subject:** `feat(scanner): add ObjectVisitor base (ctree_parentee_t)`

## Files created / modified

| Path | Action | Purpose |
|------|--------|---------|
| `src/hexrays_pytools/domain/scanner/__init__.py` | created (empty) | package marker |
| `src/hexrays_pytools/domain/scanner/visitor_base.py` | created | `ObjectVisitor(idaapi.ctree_parentee_t)` base class |
| `tests/domain/scanner/__init__.py` | created (empty) | test package marker |
| `tests/domain/scanner/test_visitor_base.py` | created | 3 unit tests for `ObjectVisitor` |
| `tools/mock_ida.py` | modified | added real `ctree_parentee_t` base class (see Deviation 2) |

## TDD summary

Strict RED → GREEN cycle observed.

**RED** (source absent): collection of `test_visitor_base.py` failed with
```
ModuleNotFoundError: No module named 'hexrays_pytools.domain.scanner.visitor_base'
```
(1 collection error, 0 tests run.) Confirmed before writing the implementation.

**GREEN** (after creating `visitor_base.py` + mock fix):
```
tests/domain/scanner/test_visitor_base.py::test_visitor_process_calls_apply_to PASSED
tests/domain/scanner/test_visitor_base.py::test_visitor_objects_initially_empty PASSED
tests/domain/scanner/test_visitor_base.py::test_visitor_subclass_must_implement_manipulate PASSED
3 passed
```

**Full suite:** `70 passed`, total coverage `83.65%` (above the 80% gate). The
new module `visitor_base.py` is at 100% line coverage.

## Deviations from the brief

Three deviations, all required to make the brief's own verification commands
(`pytest`, `mypy --strict`, `ruff check`) succeed. The brief explicitly flags
one of them: "Add `MagicMock` import (brief bug fix)."

### 1. Test file: added `MagicMock` import + `apply_to` patch (the brief's flagged bug fix)

The brief's verbatim test file references `MagicMock` (in `cfunc = MagicMock()`)
but never imports it — a `NameError` at collection time. Per the brief's own
note ("Add `MagicMock` import"), the test file now begins:

```python
from unittest.mock import MagicMock
```

A second, related bug in the brief's test was *not* fixed by an import alone.
`test_visitor_process_calls_apply_to` asserts
`v.apply_to.assert_called_with("fake_body", None)`, but `apply_to` is a SWIG
method inherited from `ctree_parentee_t`; with the real base class required by
the rest of the suite (see Deviation 2), the test instance has no Python-visible
`apply_to` attribute to assert against. The test therefore patches it:

```python
v = ObjectVisitor(cfunc)
v.apply_to = MagicMock()  # patch: real ctree_parentee_t has no Python apply_to
v.process()
v.apply_to.assert_called_with("fake_body", None)
```

The `process()` body is unchanged (`self.apply_to(self._cfunc.body, None)`), so
this still exercises the production code path. The other two tests are
unchanged from the brief (apart from swapping the inner `assert False` for
`raise AssertionError(...)` so the failure is reported even if `NotImplementedError`
is accidentally swallowed — semantically identical).

The dead line `idaapi = __import__("idaapi")` in each brief test (a leftover
that does nothing once `conftest.py` installs the mock) was removed.

### 2. `tools/mock_ida.py`: added real `ctree_parentee_t` base class (reason for DONE_WITH_CONCERNS)

The brief's verbatim source `class ObjectVisitor(idaapi.ctree_parentee_t)`
cannot work with `mock_ida` as it stood: `idaapi.ctree_parentee_t` resolved to
a `MagicMock` via the catch-all `__getattr__`, so subclassing it silently
produced a `MagicMock` instead of a real class. Symptom:

- `ObjectVisitor(cfunc)` returned a `MagicMock` (not a real instance), and
- `v._manipulate("expr", "obj")` did **not** raise `NotImplementedError`
  (test 3 fails), because MagicMock happily accepts any call.

This is the exact same problem Task 1.6 hit with `idaapi.plugin_t`, and the
fix follows the established Task 1.6 pattern: add a real, plain base class as
a class attribute on `_MockIdaModule` so it shadows the catch-all:

```python
class ctree_parentee_t:  # noqa: N801 - keep IDA SWIG casing
    pass
```

With this in place, `ObjectVisitor` is a genuine class, `_manipulate` raises
`NotImplementedError` as required, and the `apply_to` assertion in test 1 works
once `apply_to` is patched on the instance (Deviation 1).

This is a 5th file beyond the 4 the brief asked for. It is required to make
both the brief's source importable *and* its tests pass. It is ruff-clean and
mypy `--strict` clean, and the full existing suite still passes (70 passed,
83.65% coverage). `reset()` is unaffected: it only resets `MagicMock` instances
and these are real classes.

### 3. `visitor_base.py`: minimal mypy `--strict` / ruff fixes to the verbatim source

The brief's verbatim source fails the brief's own verification commands:

- **mypy `--strict`** reported 4 errors on the verbatim source:
  - `Unused "type: ignore" comment` on the `import` line and on the
    `_manipulate` signature (the `[name-defined]` ignores are not needed —
    `idaapi.tinfo_t`-style annotations work without ignores in the sibling
    `domain/types/*.py` modules, which pass `--strict`).
  - `Missing type arguments for generic type "list"` on `self._objects: list`
    and on the `objects` property return (`--disallow-any-generics`).
- **ruff `I001`** flagged the import block (missing blank line between
  `from __future__ import annotations` and `import idaapi`).

Minimal fixes (same spirit as Task 1.6's mypy fixes):

- Added `from typing import Any` and parameterized the two `list` annotations
  as `list[Any]`.
- Removed the two unused `[name-defined]` ignores.
- Kept `# type: ignore[misc]` on the class declaration: with `ctree_parentee_t`
  resolved as `Any` from the (stub-less) mocked `idaapi`, mypy *does* flag the
  subclass as `[misc]`, so this ignore is load-bearing, not unused.
- Added the missing blank line in the import block (ruff `I001`).

Runtime behavior is identical to the brief's source.

## Verification

```text
$ PYTHONPATH=src python -m pytest tests/domain/scanner/test_visitor_base.py -v
3 passed
```
(Project-wide coverage gate is evaluated by the full run — see TDD summary.)

```text
$ python -m mypy --strict src/hexrays_pytools/domain/scanner/visitor_base.py
Success: no issues found in 1 source file

$ python -m ruff check src/hexrays_pytools/domain/scanner/ tests/domain/scanner/
All checks passed!

$ python -m mypy --strict tools/mock_ida.py
Success: no issues found in 1 source file

$ python -m ruff check tools/mock_ida.py
All checks passed!
```

```text
$ python -m pytest -q
70 passed in 0.30s   # coverage 83.65% (gate: 80%)
```

## Self-review notes

- `ObjectVisitor` keeps the exact API the brief specifies (`process()`,
  `objects` property, `_manipulate` raising `NotImplementedError`) — the only
  edits to the body are mypy/ruff-required type-annotation tightenings.
- All instance state from the brief is preserved (`_cfunc`, `_objects`,
  `_init_obj`, `_start_ea`, `_skip`, `_data`).
- The mock-enhancement is a one-line additive change to `tools/mock_ida.py`
  that mirrors the existing `plugin_t` / `action_handler_t` / `action_t`
  pattern; no existing test is altered and no existing behavior regresses.
- New module `visitor_base.py` is at 100% line coverage; project coverage
  rose from the prior baseline to 83.65%.
