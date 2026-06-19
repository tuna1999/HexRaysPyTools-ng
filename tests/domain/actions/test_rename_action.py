"""Test 6 rename actions."""
from hexrays_pytools.domain.actions.rename_action import (
    PropagateName,
    RenameInside,
    RenameMemberFromFunctionName,
    RenameOther,
    RenameOutside,
    RenameUsingAssert,
)


def test_all_rename_classes_exist() -> None:
    """All 6 rename action classes are importable."""
    for cls in (RenameOther, RenameInside, RenameOutside,
                RenameMemberFromFunctionName, RenameUsingAssert, PropagateName):
        assert cls is not None


def test_b10_hotkey_collision_fix() -> None:
    """RenameMemberFromFunctionName uses Ctrl+Alt+N (B10 fix)."""
    assert RenameMemberFromFunctionName.hotkey == "Ctrl+Alt+N"
    assert RenameOther.hotkey == "Ctrl+N"
    assert RenameMemberFromFunctionName.hotkey != RenameOther.hotkey


def test_all_rename_can_instantiate() -> None:
    for cls in (RenameOther, RenameInside, RenameOutside,
                RenameMemberFromFunctionName, RenameUsingAssert, PropagateName):
        action = cls()
        assert action is not None
