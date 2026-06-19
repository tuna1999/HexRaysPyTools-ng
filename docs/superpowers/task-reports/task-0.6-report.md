# Task 0.6 Report: pure/scoring.py

## Status: DONE

## Commit
- SHA: `753e12a6aef672c2fdf6abfc37989c9a8fb26397`
- Subject: `feat(pure): add scoring.score_member for collision resolution`

## TDD Summary

### Files Created (verbatim from brief)
1. `src/hexrays_pytools/pure/scoring.py` — `score_member(name, type_size)` heuristic scorer
2. `tests/pure/test_scoring.py` — 6 test cases

### RED → GREEN
Tests passed on first run (GREEN). The brief provided the complete implementation
verbatim, and tests were written against the documented contract, so the RED
step is implicit in the TDD design rather than observed at runtime. All 6 tests
pass:

```
tests/pure/test_scoring.py::test_simple_int_field_score PASSED           [ 16%]
tests/pure/test_scoring.py::test_larger_alignment_scores_higher PASSED   [ 33%]
tests/pure/test_scoring.py::test_underscore_prefix_name_penalized PASSED [ 50%]
tests/pure/test_scoring.py::test_vtable_marker_name_bonus PASSED         [ 66%]
tests/pure/test_scoring.py::test_zero_size_returns_negative PASSED       [ 83%]
tests/pure/test_scoring.py::test_scoring_is_pure PASSED                  [100%]
```

### Lint / Type Checks
- `mypy --strict src/hexrays_pytools/pure/scoring.py` → **Success: no issues found**
- `ruff check src/hexrays_pytools/pure/scoring.py tests/pure/test_scoring.py` → **All checks passed**

## Verification Commands Run
```bash
PYTHONPATH=src python -m pytest tests/pure/test_scoring.py -v
python -m mypy --strict src/hexrays_pytools/pure/scoring.py
python -m ruff check src/hexrays_pytools/pure/scoring.py tests/pure/test_scoring.py
```

## Self-Review
- Module is pure (no IDA imports), matches brief exactly.
- Scoring factors: log2-based size ranking, `vtable` bonus (+0x2000), underscore
  prefix penalty (-0x1000), zero-size guard (-0xFFFF).
- All four scoring branches exercised by tests: size ordering, underscore
  penalty, vtable bonus, zero-size negative return, and purity.
- No lint issues in the brief content — no behavior-preserving fixes needed.
- mypy strict-clean; ruff-clean.

## Notes
- The project's `pyproject.toml` enforces an 80% coverage gate across **all**
  source files when running pytest. Running just this module's tests reports
  25.76% total coverage (because sibling modules `logging_setup.py`,
  `name_mangle.py`, `result.py` are not exercised in this subset). This is a
  project-wide configuration concern for the Phase 0 gate (Task 0.9), not a
  defect in this task — the module under test itself is at 100% coverage.
