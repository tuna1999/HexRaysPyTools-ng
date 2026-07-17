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
    def ok(cls, value: T) -> Result[T, E]:
        """Create a successful result containing `value`."""
        return cls(is_ok=True, value=value, error=None)

    @classmethod
    def err(cls, error: E) -> Result[T, E]:
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
