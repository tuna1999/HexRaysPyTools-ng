# Task 0.3 Report: logging_setup module

## Status: DONE_WITH_CONCERNS

All three required tests pass, mypy --strict passes, ruff check passes, and the commit
matches the brief's exact message. The single concern is the project-wide coverage gate
(`--cov-fail-under=80`) failing at 72.73% on this isolated module — see Concerns below.

## Files Created

- `src/hexrays_pytools/logging_setup.py` (verbatim from brief)
- `tests/pure/__init__.py` (empty)
- `tests/pure/test_logging_setup.py` (verbatim from brief, with one ruff isort
  reformat: blank line between `import logging` and `from hexrays_pytools...`)

## TDD Evidence

### RED (before implementation)

```
tests\pure\test_logging_setup.py:3: in <module>
    from hexrays_pytools.logging_setup import setup_logging
E   ModuleNotFoundError: No module named 'hexrays_pytools.logging_setup'
=========================== short test summary info ===========================
ERROR tests/pure/test_logging_setup.py
```

(Note: prior to this, the editable install was stale and reported
`No module named 'hexrays_pytools'`; re-running `pip install -e ".[dev]"` repaired
the `.pth`/finder mapping to `src/hexrays_pytools`. RED was then cleanly
`No module named 'hexrays_pytools.logging_setup'`.)

### GREEN (after implementation)

```
tests/pure/test_logging_setup.py::test_setup_logging_sets_root_level PASSED [ 33%]
tests/pure/test_logging_setup.py::test_setup_logging_is_idempotent PASSED [ 66%]
tests/pure/test_logging_setup.py::test_setup_logging_format_contains_module_and_function PASSED [100%]
============================== 3 passed in 0.05s ==============================
```

3/3 tests pass.

## Additional Verification

### mypy --strict

```
$ python -m mypy --strict src/hexrays_pytools/logging_setup.py
Success: no issues found in 1 source file
```

### ruff check

```
$ python -m ruff check src/hexrays_pytools/logging_setup.py tests/pure/
All checks passed!
```

(After applying `ruff check --fix` to reorder the test file's import block — see
Deviation note.)

## Commit

- SHA: `738ff53c2745620b0446e573130d6a9030e3c362`
- Subject: `feat(pure): add logging_setup module with tests`
- Message source: verbatim from brief (`feat(pure): add logging_setup module with tests`)

## Deviation From Brief

The brief's verbatim test file placed `import logging` directly above
`from hexrays_pytools.logging_setup import setup_logging` with no blank line. Ruff's
`isort` (`I001`) flagged this as an unsorted import block. Per the brief's mandatory
gate "ruff check passes", I applied `ruff check --fix`, which inserted a single blank
line between the stdlib import and the first-party import. Test logic is unchanged.

## Concerns

1. **Coverage gate interaction (project-wide, not test failure).** `pyproject.toml`
   sets `addopts = "--cov=hexrays_pytools --cov-report=term-missing --cov-fail-under=80"`.
   With only this 9-line module committed, coverage is 72.73% because lines 19-21
   (the add-handler branch inside the idempotency guard) are not exercised by the
   three verbatim tests:

   ```
   src\hexrays_pytools\logging_setup.py       9      3    67%   19-21
   TOTAL                                     11      3    73%
   FAIL Required test coverage of 80% not reached. Total coverage: 72.73%
   ```

   The 3 tests pass; the exit-code failure comes from the `--cov-fail-under` gate
   alone. Two ways to resolve, deferred to Task 0.9 (Phase 0 gate verification):
   - Add a 4th test that calls `setup_logging` on a freshly-reset root (no existing
     `StreamHandler`) so the add-handler branch executes.
   - Or revisit the `--cov-fail-under=80` setting in pyproject.toml for the
     early-skeleton phase where only a few modules exist.

   I did NOT add a 4th test or modify pyproject.toml here, because the brief
   specified the test file verbatim and limited this task's scope to the
   logging_setup module. Flagging for Task 0.9.

## Self-Review

- [x] Test file created before implementation (TDD order): test written, RED
      confirmed as `ModuleNotFoundError: No module named 'hexrays_pytools.logging_setup'`,
      then implementation created.
- [x] 3 tests pass: yes, all 3 verbatim tests pass (`3 passed in 0.05s`).
- [x] mypy --strict passes: `Success: no issues found in 1 source file`.
- [x] ruff check passes: `All checks passed!` (after isort auto-fix on test imports).
- [x] Commit message exactly as specified: `feat(pure): add logging_setup module with tests`.
