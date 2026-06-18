"""Test guess_allocation action (GuessAllocation)."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.action import HexRaysPopupAction
from hexrays_pytools.domain.actions.guess_allocation import GuessAllocation


def test_guess_allocation_is_popup_action() -> None:
    assert issubclass(GuessAllocation, HexRaysPopupAction)
    assert GuessAllocation.description == "Guess allocation"
    assert GuessAllocation.hotkey is None


def test_guess_allocation_instantiable_and_activates() -> None:
    a = GuessAllocation()
    assert a.name == "HexRaysPyTools:GuessAllocation"
    assert a.check(MagicMock()) is True
    a.activate(MagicMock())


def test_guess_allocation_accepts_session() -> None:
    session = MagicMock()
    a = GuessAllocation(session=session)
    assert a._session is session
