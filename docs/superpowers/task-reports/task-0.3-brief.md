# Task 0.3 Brief: logging_setup module

## Where This Fits

Task 0.2 created the `hexrays_pytools` package. This task creates the first module inside it: `logging_setup.py` for centralized logging. After this task, the project has its first runnable module with TDD coverage.

## Files to Create

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\logging_setup.py`
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\pure\__init__.py` (empty)
3. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\pure\test_logging_setup.py`

## Required Content (use VERBATIM)

### `src/hexrays_pytools/logging_setup.py`

```python
"""Centralized logging configuration for HexRaysPyTools.

Replaces the original `logging.basicConfig(...)` call in `PLUGIN_ENTRY`.
Use `setup_logging(level)` once during plugin init.
"""
import logging

_LOG_FORMAT = "[%(levelname)s] %(message)s\t(%(module)s:%(funcName)s)"


def setup_logging(level: int) -> None:
    """Configure the root logger with our standard format.

    Idempotent: safe to call multiple times (does not add duplicate handlers).
    """
    root = logging.getLogger()
    root.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        root.addHandler(handler)
```

### `tests/pure/__init__.py`

Empty file (just `pass` is fine).

### `tests/pure/test_logging_setup.py`

```python
"""Test logging_setup module."""
import logging
from hexrays_pytools.logging_setup import setup_logging


def test_setup_logging_sets_root_level() -> None:
    """setup_logging(N) should set root logger level to N."""
    setup_logging(logging.WARNING)
    assert logging.getLogger().level == logging.WARNING


def test_setup_logging_is_idempotent() -> None:
    """Calling setup_logging twice should not add duplicate handlers."""
    setup_logging(logging.INFO)
    initial_handler_count = len(logging.getLogger().handlers)
    setup_logging(logging.INFO)
    assert len(logging.getLogger().handlers) == initial_handler_count


def test_setup_logging_format_contains_module_and_function() -> None:
    """The log format should include module name and function name."""
    import io
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s\t(%(module)s:%(funcName)s)"))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    try:
        root.info("test message")
        output = buf.getvalue()
        assert "test message" in output
        assert "test_logging_setup" in output
        assert "test_setup_logging_format_contains_module_and_function" in output
    finally:
        root.removeHandler(handler)
```

## Verification Steps (TDD)

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools

# RED: run test before creating implementation
pytest tests/pure/test_logging_setup.py -v
# Expected: FAIL with ModuleNotFoundError

# GREEN: create the implementation

# Re-run test
pytest tests/pure/test_logging_setup.py -v
# Expected: 3 tests pass
```

**IMPORTANT:** Run pytest with `PYTHONPATH=src` (or ensure the package is installed editable). The src-layout means bare pytest might not find `hexrays_pytools`. Use:
```bash
PYTHONPATH=src pytest tests/pure/test_logging_setup.py -v
```

Or run `pip install -e ".[dev]"` first (already done in Task 0.1 verification).

## Additional Verification

```bash
python -m mypy --strict src/hexrays_pytools/logging_setup.py
python -m ruff check src/hexrays_pytools/logging_setup.py tests/pure/
```

Both should pass.

## Commit

```bash
git add src/hexrays_pytools/logging_setup.py tests/pure/
git commit -m "feat(pure): add logging_setup module with tests"
```

## Working Directory

`D:\re_dev_projects\ida-plugins\HexRaysPyTools`

## Report File

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-0.3-report.md`

## Report Contract

Write report with TDD evidence (RED then GREEN output snippets), files created, commit SHA, self-review, concerns.
