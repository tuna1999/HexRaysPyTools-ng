"""Guess struct allocation from a malloc/constructor call (GuessAllocation)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .action import HexRaysPopupAction

if TYPE_CHECKING:
    from ..session import Session


class GuessAllocation(HexRaysPopupAction):
    """Guess how the selected variable is allocated (malloc/new/etc.)."""

    description = "Guess allocation"
    hotkey = None
    menu_path = "HexRaysPyTools/Structure/"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True
