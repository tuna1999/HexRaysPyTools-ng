"""Rename actions (6 classes).

B10 fix: RenameMemberFromFunctionName uses Ctrl+Alt+N (not Ctrl+N, which is
already taken by RenameOther). See design spec §6.1 row 14.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .action import HexRaysPopupAction

if TYPE_CHECKING:
    from ..session import Session


class RenameOther(HexRaysPopupAction):
    """Take the other name (from the paired xref) for the selected item."""

    description = "Take other name"
    hotkey = "Ctrl+N"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True


class RenameInside(HexRaysPopupAction):
    """Rename a variable inside an argument expression."""

    description = "Rename inside argument"
    hotkey = "Shift+N"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True


class RenameOutside(HexRaysPopupAction):
    """Take the argument name and propagate it outwards."""

    description = "Take argument name"
    hotkey = "Ctrl+Shift+N"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True


class RenameMemberFromFunctionName(HexRaysPopupAction):
    """Take a struct member name from the called function name.

    B10 fix: hotkey is Ctrl+Alt+N, not Ctrl+N (Ctrl+N collides with RenameOther).
    """

    description = "Take name from function"
    hotkey = "Ctrl+Alt+N"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True


class RenameUsingAssert(HexRaysPopupAction):
    """Rename a variable based on the assert argument that checks it."""

    description = "Rename as assert argument"
    hotkey = None

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True


class PropagateName(HexRaysPopupAction):
    """Propagate the selected name to all matching references."""

    description = "Propagate name"
    hotkey = "P"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True
