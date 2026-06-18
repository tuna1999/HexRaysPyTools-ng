"""Test rename_action (RenameOther, RenameInside, RenameOutside, RenameMemberFromFunctionName, RenameUsingAssert, PropagateName).

B10 fix verification: RenameMemberFromFunctionName uses Ctrl+Alt+N, not Ctrl+N
(Ctrl+N is taken by RenameOther).
"""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.action import HexRaysPopupAction
from hexrays_pytools.domain.actions.rename_action import (
    PropagateName,
    RenameInside,
    RenameMemberFromFunctionName,
    RenameOther,
    RenameOutside,
    RenameUsingAssert,
)

ALL_RENAME_CLASSES = (
    RenameOther,
    RenameInside,
    RenameOutside,
    RenameMemberFromFunctionName,
    RenameUsingAssert,
    PropagateName,
)


def test_all_rename_are_popup_actions() -> None:
    for cls in ALL_RENAME_CLASSES:
        assert issubclass(cls, HexRaysPopupAction), cls


def test_rename_other_hotkey_ctrl_n() -> None:
    assert RenameOther.description == "Take other name"
    assert RenameOther.hotkey == "Ctrl+N"


def test_rename_inside_hotkey_shift_n() -> None:
    assert RenameInside.description == "Rename inside argument"
    assert RenameInside.hotkey == "Shift+N"


def test_rename_outside_hotkey_ctrl_shift_n() -> None:
    assert RenameOutside.description == "Take argument name"
    assert RenameOutside.hotkey == "Ctrl+Shift+N"


def test_rename_member_from_function_name_b10_fix() -> None:
    """B10 fix: Ctrl+Alt+N, NOT Ctrl+N (which collides with RenameOther)."""
    assert RenameMemberFromFunctionName.description == "Take name from function"
    assert RenameMemberFromFunctionName.hotkey == "Ctrl+Alt+N"
    # Explicitly assert it does NOT reuse RenameOther's hotkey
    assert RenameMemberFromFunctionName.hotkey != RenameOther.hotkey


def test_rename_using_assert_no_hotkey() -> None:
    assert RenameUsingAssert.description == "Rename as assert argument"
    assert RenameUsingAssert.hotkey is None


def test_propagate_name_hotkey_p() -> None:
    assert PropagateName.description == "Propagate name"
    assert PropagateName.hotkey == "P"


def test_all_six_instantiable_and_activatable() -> None:
    for cls in ALL_RENAME_CLASSES:
        a = cls()
        assert a.name == f"HexRaysPyTools:{cls.__name__}"
        assert a.check(MagicMock()) is True
        a.activate(MagicMock())


def test_all_six_accept_session() -> None:
    session = MagicMock()
    for cls in ALL_RENAME_CLASSES:
        a = cls(session=session)
        assert a._session is session
