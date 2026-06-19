"""Test SwapThenElse action."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.swap_if_action import SwapThenElse


def test_swap_then_else_init() -> None:
    a = SwapThenElse()
    assert a.hotkey == "Shift+Alt+S"


def test_swap_then_else_check() -> None:
    a = SwapThenElse()
    assert a.check(MagicMock()) is True
