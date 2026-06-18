"""Test recast_action (RecastItemLeft, RecastItemRight)."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.action import HexRaysPopupAction
from hexrays_pytools.domain.actions.recast_action import (
    RecastItemLeft,
    RecastItemRight,
)


def test_recast_item_left_is_popup_action() -> None:
    assert issubclass(RecastItemLeft, HexRaysPopupAction)
    assert RecastItemLeft.description == "Recast Item"
    assert RecastItemLeft.hotkey == "Shift+L"


def test_recast_item_left_instantiable_and_activates() -> None:
    a = RecastItemLeft()
    assert a.name == "HexRaysPyTools:RecastItemLeft"
    assert a.check(MagicMock()) is True
    a.activate(MagicMock())


def test_recast_item_right_inherits_recast_item_left() -> None:
    assert issubclass(RecastItemRight, RecastItemLeft)
    assert RecastItemRight.description == "Recast Item"
    assert RecastItemRight.hotkey == "Shift+R"


def test_recast_item_right_instantiable_and_activates() -> None:
    a = RecastItemRight()
    assert a.name == "HexRaysPyTools:RecastItemRight"
    assert a.check(MagicMock()) is True
    a.activate(MagicMock())


def test_both_accept_session() -> None:
    session = MagicMock()
    for cls in (RecastItemLeft, RecastItemRight):
        a = cls(session=session)
        assert a._session is session
