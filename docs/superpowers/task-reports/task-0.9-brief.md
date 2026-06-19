# Task 0.9 Brief: Phase 0 Gate Verification

## Where This Fits

This is the FINAL task of Phase 0. All code is done. This task verifies the Phase 0 gate and tags the milestone.

## Gate Criteria (from plan)

- [ ] All tests in `tests/` pass
- [ ] `mypy --strict` clean on `src/`
- [ ] `ruff check` clean on `src/` and `tests/`
- [ ] All Phase 0 deliverables exist

## Verification Commands

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools

# 1. Full test suite (includes --cov-fail-under=80 from pyproject.toml)
PYTHONPATH=src pytest -v

# 2. Type check
python -m mypy --strict src/hexrays_pytools/

# 3. Lint
python -m ruff check src/hexrays_pytools/ tests/ tools/

# 4. List deliverables
ls -la pyproject.toml .gitignore .python-version README.md
ls -la src/hexrays_pytools/__init__.py
ls -la src/hexrays_pytools/logging_setup.py
ls -la src/hexrays_pytools/pure/
ls -la tests/conftest.py
ls -la tests/pure/
ls -la tools/mock_ida.py
```

## Expected Deliverables (9 files minimum)

1. `pyproject.toml`
2. `.gitignore`
3. `.python-version`
4. `README.md` (minimal)
5. `src/hexrays_pytools/__init__.py`
6. `src/hexrays_pytools/logging_setup.py`
7. `src/hexrays_pytools/pure/__init__.py`
8. `src/hexrays_pytools/pure/result.py`
9. `src/hexrays_pytools/pure/name_mangle.py`
10. `src/hexrays_pytools/pure/scoring.py`
11. `src/hexrays_pytools/pure/toml_template.py`
12. `tests/conftest.py`
13. `tests/pure/__init__.py`
14. `tests/pure/test_logging_setup.py`
15. `tests/pure/test_result.py`
16. `tests/pure/test_name_mangle.py`
17. `tests/pure/test_scoring.py`
18. `tests/pure/test_toml_template.py`
19. `tests/fixtures/__init__.py`
20. `tests/fixtures/sample_templated_types.toml`
21. `tools/mock_ida.py`

## What to Do If Gate Fails

1. If any command fails, report BLOCKED with the failure
2. If --cov-fail-under=80 fails, report the actual coverage % and which modules are uncovered. DO NOT lower the gate. The structural issue with logging_setup.py is known.
3. If mypy/ruff fail, report the specific error

## Tag the milestone

If all gates pass:

```bash
git tag phase-0-foundation
git log --oneline -10
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-0.9-report.md`

Report the actual outputs of all verification commands, the coverage %, and confirm all 21 deliverables exist.
