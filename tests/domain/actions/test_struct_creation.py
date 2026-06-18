"""Test struct_creation actions (CreateNewField, CreateVtable)."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.action import Action, HexRaysPopupAction
from hexrays_pytools.domain.actions.struct_creation import CreateNewField, CreateVtable


def test_create_new_field_is_popup_action() -> None:
    assert issubclass(CreateNewField, HexRaysPopupAction)
    assert CreateNewField.description == "Create New Field"
    assert CreateNewField.hotkey == "Ctrl+F"


def test_create_new_field_instantiable_and_activates() -> None:
    a = CreateNewField()
    assert a.name == "HexRaysPyTools:CreateNewField"
    assert a.check(MagicMock()) is True
    a.activate(MagicMock())


def test_create_vtable_is_action() -> None:
    assert issubclass(CreateVtable, Action)
    assert CreateVtable.description == "Create Virtual Table"
    assert CreateVtable.hotkey == "V"


def test_create_vtable_instantiable_and_activates() -> None:
    a = CreateVtable()
    assert a.name == "HexRaysPyTools:CreateVtable"
    a.activate(MagicMock())


def test_both_accept_session() -> None:
    session = MagicMock()
    for cls in (CreateNewField, CreateVtable):
        a = cls(session=session)
        assert a._session is session
