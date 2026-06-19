"""6 rename action wrappers."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..ctree.rename import (
    propagate_name,
    rename_inside,
    rename_member_from_function_name,
    rename_other,
    rename_outside,
    rename_using_assert,
)
from .action import HexRaysPopupAction

if TYPE_CHECKING:
    from ..session import Session


def _make_rename_action(name: str, description: str, hotkey: str | None, ctree_fn: Any) -> type:
    """Factory: create a rename action class wrapping a ctree function."""
    class _RenameAction(HexRaysPopupAction):
        _description = description
        _hotkey = hotkey
        _ctree_fn = staticmethod(ctree_fn)

        def __init__(self, session: Session | None = None) -> None:
            super().__init__(session)

        def activate(self, ctx: Any) -> None:
            hx_view = getattr(ctx, "widget", None)
            if hx_view and getattr(hx_view, "item", None):
                self._ctree_fn(hx_view.item)

        def check(self, hx_view: Any) -> bool:
            return hx_view is not None

    _RenameAction.__name__ = name
    _RenameAction.description = description
    _RenameAction.hotkey = hotkey
    _RenameAction.menu_path = "HexRaysPyTools/Rename/"
    return _RenameAction


# 6 rename actions. B10 fix: RenameMemberFromFunctionName uses Ctrl+Alt+N
RenameOther = _make_rename_action("RenameOther", "Take other name", "Ctrl+N", rename_other)
RenameInside = _make_rename_action("RenameInside", "Push var name into arg", "Shift+N", rename_inside)
RenameOutside = _make_rename_action("RenameOutside", "Take arg name for var", "Ctrl+Shift+N", rename_outside)
RenameMemberFromFunctionName = _make_rename_action(
    "RenameMemberFromFunctionName", "Take name from function", "Ctrl+Alt+N", rename_member_from_function_name,
)
RenameUsingAssert = _make_rename_action("RenameUsingAssert", "Rename using assert", None, rename_using_assert)
PropagateName = _make_rename_action("PropagateName", "Propagate name", "P", propagate_name)
