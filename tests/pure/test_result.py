"""Test Result type."""
from dataclasses import FrozenInstanceError

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
    with pytest.raises(FrozenInstanceError):
        r.value = 100  # type: ignore[misc]
