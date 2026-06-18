"""Recast item actions (RecastItemLeft, RecastItemRight)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .action import HexRaysPopupAction

if TYPE_CHECKING:
    from ..session import Session


class RecastItemLeft(HexRaysPopupAction):
    """Recast the selected item using the left-hand type suggestion."""

    description = "Recast Item"
    hotkey = "Shift+L"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True


class RecastItemRight(RecastItemLeft):
    """Recast the selected item using the right-hand type suggestion."""

    description = "Recast Item"
    hotkey = "Shift+R"
