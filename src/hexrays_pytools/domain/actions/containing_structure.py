"""Containing-structure actions (SelectContainingStructure, ResetContainingStructure)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .action import HexRaysPopupAction

if TYPE_CHECKING:
    from ..session import Session


class SelectContainingStructure(HexRaysPopupAction):
    """Treat the selected variable as a field of an outer struct
    (CONTAINING_RECORD pattern)."""

    description = "Select Containing Structure"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True


class ResetContainingStructure(HexRaysPopupAction):
    """Undo a previous SelectContainingStructure assignment."""

    description = "Reset Containing Structure"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True
