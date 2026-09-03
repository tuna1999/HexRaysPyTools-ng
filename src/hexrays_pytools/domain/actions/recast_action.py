"""RecastItemLeft/Right action wrappers.

These wrap the ctree recast engine in ``domain/ctree/recast.py``:

  * Left (Shift+L) — recast the **target** side of an assignment / return / call.
  * Right (Shift+R) — recast the **source** side of a cast.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]

from ..ctree.recast import (
    apply_recast,
    extract_recast_info_left,
    extract_recast_info_right,
    recast_label,
)
from .action import HexRaysPopupAction

if TYPE_CHECKING:
    pass


class RecastItemLeft(HexRaysPopupAction):
    """Recast the selected item using the left-hand type suggestion."""

    description = "Recast Item"
    hotkey = "Shift+L"
    menu_path = "HexRaysPyTools-ng/"

    def activate(self, ctx: Any) -> None:
        hx_view = self._get_hx_view(ctx)
        if hx_view is None:
            return
        ri = extract_recast_info_left(hx_view.cfunc, hx_view.item)
        if ri is not None:
            apply_recast(hx_view, ri)

    def check(self, hx_view: Any) -> bool:
        if hx_view is None:
            return False
        ri = extract_recast_info_left(hx_view.cfunc, hx_view.item)
        if ri is None:
            return False
        self._set_label(recast_label(ri))
        return True

    @staticmethod
    def _get_hx_view(ctx: Any) -> Any:
        return idaapi.get_widget_vdui(ctx.widget)

    @staticmethod
    def _set_label(label: str) -> None:
        # The registered action's menu label is mutated so the popup shows the
        # specific recast target (e.g. "Recast Variable v1 to FOO *").
        idaapi.update_action_label("HexRaysPyTools:RecastItemLeft", label)


class RecastItemRight(HexRaysPopupAction):
    """Recast the selected item using the right-hand type suggestion."""

    description = "Recast Item"
    hotkey = "Shift+R"
    menu_path = "HexRaysPyTools-ng/"

    def activate(self, ctx: Any) -> None:
        hx_view = self._get_hx_view(ctx)
        if hx_view is None:
            return
        ri = extract_recast_info_right(hx_view.cfunc, hx_view.item)
        if ri is not None:
            apply_recast(hx_view, ri)

    def check(self, hx_view: Any) -> bool:
        if hx_view is None:
            return False
        ri = extract_recast_info_right(hx_view.cfunc, hx_view.item)
        if ri is None:
            return False
        self._set_label(recast_label(ri))
        return True

    @staticmethod
    def _get_hx_view(ctx: Any) -> Any:
        return idaapi.get_widget_vdui(ctx.widget)

    @staticmethod
    def _set_label(label: str) -> None:
        idaapi.update_action_label("HexRaysPyTools:RecastItemRight", label)
