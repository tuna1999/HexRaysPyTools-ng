"""Test structs_by_size action (GetStructureBySize)."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.action import HexRaysPopupAction
from hexrays_pytools.domain.actions.structs_by_size import GetStructureBySize


def test_get_structure_by_size_is_popup_action() -> None:
    assert issubclass(GetStructureBySize, HexRaysPopupAction)
    assert GetStructureBySize.description == "Structures with this size"


def test_get_structure_by_size_instantiable_and_activates() -> None:
    a = GetStructureBySize()
    assert a.name == "HexRaysPyTools:GetStructureBySize"
    assert a.check(MagicMock()) is True
    a.activate(MagicMock())


def test_get_structure_by_size_accepts_session() -> None:
    session = MagicMock()
    a = GetStructureBySize(session=session)
    assert a._session is session
