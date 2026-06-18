"""Swap then/else branches of an if statement (SwapThenElse)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .action import HexRaysPopupAction

if TYPE_CHECKING:
    from ..session import Session


class SwapThenElse(HexRaysPopupAction):
    """Swap the then/else branches of the selected if statement."""

    description = "Swap then/else"
    hotkey = "Shift+Alt+S"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True
