"""Test swap_if_action (SwapThenElse)."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.action import HexRaysPopupAction
from hexrays_pytools.domain.actions.swap_if_action import SwapThenElse


def test_swap_then_else_is_popup_action() -> None:
    assert issubclass(SwapThenElse, HexRaysPopupAction)
    assert SwapThenElse.description == "Swap then/else"
    assert SwapThenElse.hotkey == "Shift+Alt+S"


def test_swap_then_else_instantiable_and_activates() -> None:
    a = SwapThenElse()
    assert a.name == "HexRaysPyTools:SwapThenElse"
    assert a.check(MagicMock()) is True
    a.activate(MagicMock())


def test_swap_then_else_accepts_session() -> None:
    session = MagicMock()
    a = SwapThenElse(session=session)
    assert a._session is session
