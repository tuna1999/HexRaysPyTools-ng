# Task 0.4 Brief: pure/result.py

## Files to Create

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\pure\__init__.py` (empty)
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\pure\result.py`
3. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\pure\test_result.py`

## Required Content (verbatim)

### `src/hexrays_pytools/pure/__init__.py`

Empty file (just `pass`).

### `src/hexrays_pytools/pure/result.py`

```python
"""Result[T, E] type for explicit error handling.

Use `Result.ok(value)` for success and `Result.err(error)` for failure.
Avoids exception-based control flow for expected errors.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Result(Generic[T, E]):
    """A value or an error. Use `ok()` and `err()` factories.

    Example:
        def parse_decl(s: str) -> Result[tinfo_t, str]:
            if not s:
                return Result.err("empty string")
            ...
            return Result.ok(tinfo)
    """
    is_ok: bool
    value: T | None
    error: E | None

    @classmethod
    def ok(cls, value: T) -> "Result[T, E]":
        """Create a successful result containing `value`."""
        return cls(is_ok=True, value=value, error=None)

    @classmethod
    def err(cls, error: E) -> "Result[T, E]":
        """Create an error result containing `error`."""
        return cls(is_ok=False, value=None, error=error)

    def unwrap(self) -> T:
        """Return the value or raise ValueError if is_ok=False."""
        if not self.is_ok:
            raise ValueError(f"called unwrap() on error result: {self.error}")
        assert self.value is not None
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Return the value or `default` if is_ok=False."""
        if self.is_ok:
            assert self.value is not None
            return self.value
        return default
```

### `tests/pure/test_result.py`

```python
"""Test Result type."""
import pytest
from hexrays_pytools.pure.result import Result


def test_ok_creates_successful_result() -> None:
    """Result.ok(value) creates a result with is_ok=True and value=value."""
    r = Result.ok(42)
    assert r.is_ok is True
    assert r.value == 42
    assert r.error is None


def test_err_creates_error_result() -> None:
    """Result.err(error) creates a result with is_ok=False and error=error."""
    r = Result.err("something went wrong")
    assert r.is_ok is False
    assert r.value is None
    assert r.error == "something went wrong"


def test_unwrap_returns_value_on_ok() -> None:
    """Result.unwrap() returns the value if is_ok=True."""
    r = Result.ok(42)
    assert r.unwrap() == 42


def test_unwrap_raises_on_error() -> None:
    """Result.unwrap() raises ValueError if is_ok=False."""
    r = Result.err("oops")
    with pytest.raises(ValueError, match="oops"):
        r.unwrap()


def test_unwrap_or_returns_value_on_ok() -> None:
    """Result.unwrap_or(default) returns the value if is_ok=True."""
    r = Result.ok(42)
    assert r.unwrap_or(0) == 42


def test_unwrap_or_returns_default_on_error() -> None:
    """Result.unwrap_or(default) returns default if is_ok=False."""
    r = Result.err("oops")
    assert r.unwrap_or(0) == 0


def test_result_is_immutable() -> None:
    """Result instances should be frozen (immutable)."""
    r = Result.ok(42)
    with pytest.raises(Exception):
        r.value = 100  # type: ignore[misc]
```

## TDD Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/pure/test_result.py -v
# Expected RED first: ModuleNotFoundError on hexrays_pytools.pure.result
# Then GREEN: 7 tests pass

# Type + lint
python -m mypy --strict src/hexrays_pytools/pure/result.py
python -m ruff check src/hexrays_pytools/pure/result.py tests/pure/test_result.py
```

## Commit

```bash
git add src/hexrays_pytools/pure/ tests/pure/test_result.py
git commit -m "feat(pure): add Result[T, E] type with full test coverage"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-0.4-report.md`

Status + commit + TDD summary + path.
