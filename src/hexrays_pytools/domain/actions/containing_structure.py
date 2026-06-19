"""SelectContainingStructure / ResetContainingStructure action wrappers."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..ctree.negative_offsets import (
    reset_containing_structure,
    select_containing_structure,
)
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
        hx_view = getattr(ctx, "widget", None)
        if hx_view and getattr(hx_view, "item", None):
            select_containing_structure(hx_view.item)

    def check(self, hx_view: Any) -> bool:
        return hx_view is not None


class ResetContainingStructure(HexRaysPopupAction):
    """Undo a previous SelectContainingStructure assignment."""

    description = "Reset Containing Structure"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        hx_view = getattr(ctx, "widget", None)
        if hx_view and getattr(hx_view, "item", None):
            reset_containing_structure(hx_view.item)

    def check(self, hx_view: Any) -> bool:
        return hx_view is not None
