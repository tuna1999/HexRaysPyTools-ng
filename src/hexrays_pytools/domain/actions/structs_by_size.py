"""Find structures matching a size (GetStructureBySize)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .action import HexRaysPopupAction

if TYPE_CHECKING:
    from ..session import Session


class GetStructureBySize(HexRaysPopupAction):
    """List existing structures whose size matches the selected expression."""

    description = "Structures with this size"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True
