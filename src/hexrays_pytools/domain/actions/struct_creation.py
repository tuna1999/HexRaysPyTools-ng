"""Struct creation actions (CreateNewField, CreateVtable)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .action import Action, HexRaysPopupAction

if TYPE_CHECKING:
    from ..session import Session


class CreateNewField(HexRaysPopupAction):
    """Create a new struct field at the selected offset."""

    description = "Create New Field"
    hotkey = "Ctrl+F"
    menu_path = "HexRaysPyTools/Structure/"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True


class CreateVtable(Action):
    """Create a new virtual table from the selected expression."""

    description = "Create Virtual Table"
    hotkey = "V"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass
