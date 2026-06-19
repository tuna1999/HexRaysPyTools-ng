# Task 2.7 Report: domain/scanner/member_extractor.py

## Status: DONE

## Commit

- **SHA:** `a4555fc`
- **Subject:** `feat(scanner): add SearchVisitor (main member extractor)`
- **Files changed:** 2 files, 73 insertions

## Deliverables

| File | Purpose |
|------|---------|
| `src/hexrays_pytools/domain/scanner/member_extractor.py` | `SearchVisitor` + `NewShallowSearchVisitor` / `NewDeepSearchVisitor` ctree scanners |
| `tests/domain/scanner/test_member_extractor.py` | 3 unit tests for the visitor |

## TDD Summary

| Phase | Result |
|-------|--------|
| RED | `ModuleNotFoundError: No module named 'hexrays_pytools.domain.scanner.member_extractor'` (collection error, tests cannot import) |
| GREEN | 3/3 tests pass |

### Tests

1. `test_search_visitor_init` — `SearchVisitor(cfunc)` stores the cfunc in `self._cfunc`
2. `test_search_visitor_manipulate_matches_target` — `_manipulate(cexpr, obj)` runs without raising when `obj.is_target()` returns True
3. `test_shallow_visitor_subclasses_search` — `NewShallowSearchVisitor` subclasses `SearchVisitor`

### Quality Gates

| Gate | Result |
|------|--------|
| `pytest tests/domain/scanner/test_member_extractor.py` | 3 passed |
| `mypy --strict` on `member_extractor.py` | Success: no issues found |
| `ruff check` on both files | All checks passed! |
| Full scanner test suite (regression) | 11 passed |

## Deviations from Brief

The brief's verbatim content had three issues that prevented mypy/ruff from being clean under the project's strict config (`warn_unused_ignores = true`, `strict = true`). Resolved with minimal, intent-preserving changes:

1. **Removed unused `# type: ignore[name-defined]` comments.** The mock IDA module resolves `idaapi.cfunc_t` / `idaapi.cexpr_t` at type-check time, so these ignores are unused and fail under `warn_unused_ignores = true`. The sibling module `visitor_base.py` (Task 2.4) already uses the same annotations without the ignore and passes mypy clean.

2. **Changed `_manipulate(cexpr, obj: ScanObject)` to `obj: object` with an internal `cast(ScanObject, obj)`.** The base `ObjectVisitor._manipulate` is typed `obj: object`; tightening the parameter type to `ScanObject` in the subclass triggers mypy's Liskov (`[override]`) check. Matching the base signature with a local cast keeps the brief's runtime behavior identical.

3. **Removed unused imports** (`SO_LOCAL_VARIABLE`, `SO_GLOBAL_OBJECT` from `.scanned_object`) and **sorted the import block** (ruff `I001` / `F401`). Also dropped the redundant `__init__` override that just called `super().__init__(cfunc)` — the base already does the same, and `test_search_visitor_init` still passes via inherited init.

4. **In the test file**, removed the unused `idaapi = __import__("idaapi")` locals (conftest already installs mocks) and split the multi-name import across lines for ruff's formatter. Added `from unittest.mock import MagicMock` per the brief.

## Verification Commands

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/domain/scanner/test_member_extractor.py -v
python -m mypy --strict src/hexrays_pytools/domain/scanner/member_extractor.py
python -m ruff check src/hexrays_pytools/domain/scanner/member_extractor.py tests/domain/scanner/test_member_extractor.py
```
