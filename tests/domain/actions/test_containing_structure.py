"""Test containing_structure actions (SelectContainingStructure, ResetContainingStructure)."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.action import HexRaysPopupAction
from hexrays_pytools.domain.actions.containing_structure import (
    ResetContainingStructure,
    SelectContainingStructure,
)


def test_select_containing_structure_is_popup_action() -> None:
    assert issubclass(SelectContainingStructure, HexRaysPopupAction)
    assert SelectContainingStructure.description == "Select Containing Structure"


def test_select_containing_structure_instantiable_and_activates() -> None:
    a = SelectContainingStructure()
    assert a.name == "HexRaysPyTools:SelectContainingStructure"
    assert a.check(MagicMock()) is True
    a.activate(MagicMock())


def test_reset_containing_structure_is_popup_action() -> None:
    assert issubclass(ResetContainingStructure, HexRaysPopupAction)
    assert ResetContainingStructure.description == "Reset Containing Structure"


def test_reset_containing_structure_instantiable_and_activates() -> None:
    a = ResetContainingStructure()
    assert a.name == "HexRaysPyTools:ResetContainingStructure"
    assert a.check(MagicMock()) is True
    a.activate(MagicMock())


def test_both_accept_session() -> None:
    session = MagicMock()
    for cls in (SelectContainingStructure, ResetContainingStructure):
        a = cls(session=session)
        assert a._session is session
