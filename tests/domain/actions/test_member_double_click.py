"""Test member_double_click action wrapper (MemberDoubleClickAction).

Note: this is the hotkey-action wrapper, not the event handler. The
hxe_double_click event handler is in hx_events.py (tested by test_hx_events.py).
"""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.action import HexRaysPopupAction
from hexrays_pytools.domain.actions.member_double_click import MemberDoubleClickAction


def test_member_double_click_action_is_popup_action() -> None:
    assert issubclass(MemberDoubleClickAction, HexRaysPopupAction)
    assert MemberDoubleClickAction.description == "Jump to virtual function"
    assert MemberDoubleClickAction.hotkey is None


def test_member_double_click_action_instantiable_and_activates() -> None:
    a = MemberDoubleClickAction()
    assert a.name == "HexRaysPyTools:MemberDoubleClickAction"
    assert a.check(MagicMock()) is True
    a.activate(MagicMock())


def test_member_double_click_action_accepts_session() -> None:
    session = MagicMock()
    a = MemberDoubleClickAction(session=session)
    assert a._session is session
