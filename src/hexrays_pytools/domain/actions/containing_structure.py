"""SelectContainingStructure / ResetContainingStructure action wrappers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]

from ..ctree.negative_offsets import (
    can_reset_containing,
    can_select_containing,
    reset_containing_structure,
    select_containing_structure,
)
from .action import HexRaysPopupAction

if TYPE_CHECKING:
    from ..session import Session


def _store(session: Session | None) -> dict[int, dict[int, Any]]:
    """The session's potential-negatives store (empty when no session)."""
    return session.potential_negatives if session is not None else {}


def _get_hx_view(ctx: Any) -> Any:
    return idaapi.get_widget_vdui(ctx.widget)


class SelectContainingStructure(HexRaysPopupAction):
    """Treat the selected variable as a field of an outer struct
    (CONTAINING_RECORD pattern)."""

    description = "Select Containing Structure"
    menu_path = "HexRaysPyTools/Structure/"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        hx_view = _get_hx_view(ctx)
        if hx_view is not None:
            select_containing_structure(hx_view, _store(self._session))

    def check(self, hx_view: Any) -> bool:
        return can_select_containing(hx_view, _store(self._session))


class ResetContainingStructure(HexRaysPopupAction):
    """Undo a previous SelectContainingStructure assignment."""
    description = "Reset Containing Structure"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        hx_view = _get_hx_view(ctx)
        if hx_view is not None:
            reset_containing_structure(hx_view)

    def check(self, hx_view: Any) -> bool:
        return can_reset_containing(hx_view)
