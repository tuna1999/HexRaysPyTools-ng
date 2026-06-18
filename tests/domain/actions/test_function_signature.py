"""Test function_signature actions (ConvertToUsercall, AddRemoveReturn, RemoveArgument)."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.action import HexRaysPopupAction
from hexrays_pytools.domain.actions.function_signature import (
    AddRemoveReturn,
    ConvertToUsercall,
    RemoveArgument,
)


def test_convert_to_usercall_is_popup_action() -> None:
    assert issubclass(ConvertToUsercall, HexRaysPopupAction)
    assert ConvertToUsercall.description == "Convert to __usercall"


def test_convert_to_usercall_instantiable_and_activates() -> None:
    a = ConvertToUsercall()
    assert a.name == "HexRaysPyTools:ConvertToUsercall"
    assert a.check(MagicMock()) is True
    a.activate(MagicMock())


def test_add_remove_return_is_popup_action() -> None:
    assert issubclass(AddRemoveReturn, HexRaysPopupAction)
    assert AddRemoveReturn.description == "Add/Remove Return"


def test_add_remove_return_instantiable_and_activates() -> None:
    a = AddRemoveReturn()
    assert a.name == "HexRaysPyTools:AddRemoveReturn"
    assert a.check(MagicMock()) is True
    a.activate(MagicMock())


def test_remove_argument_is_popup_action() -> None:
    assert issubclass(RemoveArgument, HexRaysPopupAction)
    assert RemoveArgument.description == "Remove Argument"


def test_remove_argument_instantiable_and_activates() -> None:
    a = RemoveArgument()
    assert a.name == "HexRaysPyTools:RemoveArgument"
    assert a.check(MagicMock()) is True
    a.activate(MagicMock())


def test_all_three_accept_session() -> None:
    session = MagicMock()
    for cls in (ConvertToUsercall, AddRemoveReturn, RemoveArgument):
        a = cls(session=session)
        assert a._session is session
