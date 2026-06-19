"""SwapThenElse action wrapper."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]

from ..ctree.swap_if import can_swap, swap_if_then_else
from .action import HexRaysPopupAction

if TYPE_CHECKING:
    from ..session import Session


class SwapThenElse(HexRaysPopupAction):
    """Swap the then/else branches of the selected if statement."""

    description = "Swap if/then/else branches"
    hotkey = "Shift+Alt+S"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        hx_view = idaapi.get_widget_vdui(ctx.widget)
        if hx_view is not None:
            swap_if_then_else(hx_view)

    def check(self, hx_view: Any) -> bool:
        return can_swap(hx_view)
