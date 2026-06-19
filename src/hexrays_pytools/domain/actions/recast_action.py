"""RecastItemLeft/Right action wrappers."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..ctree.recast import recast_item_left, recast_item_right
from .action import HexRaysPopupAction

if TYPE_CHECKING:
    from ..session import Session


class RecastItemLeft(HexRaysPopupAction):
    """Recast the selected item using the left-hand type suggestion."""

    description = "Recast Item (Left)"
    hotkey = "Shift+L"
    menu_path = "HexRaysPyTools/Recast/"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        hx_view = self._get_hx_view(ctx)
        if hx_view and hx_view.item:
            recast_item_left(hx_view.item)

    def check(self, hx_view: Any) -> bool:
        return hx_view is not None

    @staticmethod
    def _get_hx_view(ctx: Any) -> Any:
        return getattr(ctx, "widget", None)


class RecastItemRight(HexRaysPopupAction):
    """Recast the selected item using the right-hand type suggestion."""

    description = "Recast Item (Right)"
    hotkey = "Shift+R"
    menu_path = "HexRaysPyTools/Recast/"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        hx_view = self._get_hx_view(ctx)
        if hx_view and hx_view.item:
            recast_item_right(hx_view.item)

    def check(self, hx_view: Any) -> bool:
        return hx_view is not None

    @staticmethod
    def _get_hx_view(ctx: Any) -> Any:
        return getattr(ctx, "widget", None)
