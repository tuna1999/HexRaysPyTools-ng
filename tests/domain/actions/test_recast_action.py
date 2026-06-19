"""Test RecastItemLeft/Right actions."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.recast_action import RecastItemLeft, RecastItemRight


def test_recast_left_init() -> None:
    a = RecastItemLeft()
    assert a.hotkey == "Shift+L"


def test_recast_left_check() -> None:
    a = RecastItemLeft()
    assert a.check(None) is False
    assert a.check(MagicMock()) is True


def test_recast_right_init() -> None:
    a = RecastItemRight()
    assert a.hotkey == "Shift+R"
