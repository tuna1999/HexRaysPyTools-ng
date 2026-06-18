"""Test Action base classes."""
from unittest.mock import MagicMock

import pytest

from hexrays_pytools.domain.actions.action import (
    Action,
    HexRaysPopupAction,
    HexRaysPopupRequestHandler,
    HexRaysXrefAction,
)


def test_action_name_uses_class_name() -> None:
    a = Action()
    assert a.name == "HexRaysPyTools:Action"


def test_action_init_accepts_session() -> None:
    session = MagicMock()
    a = Action(session=session)
    assert a._session is session


def test_action_activate_raises_not_implemented() -> None:
    a = Action()
    with pytest.raises(NotImplementedError):
        a.activate(None)


def test_hexrays_popup_action_check_raises() -> None:
    a = HexRaysPopupAction()
    with pytest.raises(NotImplementedError):
        a.check(None)


def test_hexrays_xref_action_check_raises() -> None:
    a = HexRaysXrefAction()
    with pytest.raises(NotImplementedError):
        a.check(None)


def test_popup_request_handler_calls_attach_when_check_passes() -> None:
    """Request handler attaches action to popup when check returns True."""
    idaapi = __import__("idaapi")
    action = MagicMock()
    action.check.return_value = True
    action.name = "test_action"
    handler = HexRaysPopupRequestHandler(action)
    form = MagicMock()
    popup = MagicMock()
    hx_view = MagicMock()
    handler.handle(0, form, popup, hx_view)
    idaapi.attach_action_to_popup.assert_called_once_with(form, popup, "test_action", None)


def test_popup_request_handler_skips_when_check_fails() -> None:
    idaapi = __import__("idaapi")
    action = MagicMock()
    action.check.return_value = False
    handler = HexRaysPopupRequestHandler(action)
    handler.handle(0, MagicMock(), MagicMock(), MagicMock())
    idaapi.attach_action_to_popup.assert_not_called()
