"""Base classes for actions (right-click menu + hotkey)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]

if TYPE_CHECKING:
    from ..session import Session


class Action(idaapi.action_handler_t):  # type: ignore[misc]
    """Base class for all actions.

    Attributes:
        description: label shown in the menu.
        hotkey: global hotkey (or None).
        menu_path: popup group path. Actions that appear in the right-click
            menu are grouped under this path (e.g. ``"HexRaysPyTools-ng/"``).
            The trailing ``/`` makes IDA create a submenu. ``None`` means the
            action is not attached to the popup (only triggered by hotkey or
            the Edit > Plugins menu).
        ida_menu_path: optional permanent IDA menu path used for non-popup
            actions such as the Classes entry under Local Types.
    """

    description: str = ""
    hotkey: str | None = None
    menu_path: str | None = None
    ida_menu_path: str | None = None

    def __init__(self, session: Session | None = None) -> None:
        super().__init__()
        self._session = session

    @property
    def name(self) -> str:
        return f"HexRaysPyTools:{type(self).__name__}"

    def activate(self, ctx: Any) -> None:  # noqa: D401 - IDA SWIG override
        raise NotImplementedError

    def update(self, ctx: Any) -> int:  # noqa: D401 - IDA SWIG override
        return int(idaapi.AST_DISABLE_FOR_WIDGET)


class HexRaysPopupAction(Action):
    """Action attached to right-click menu in pseudocode.

    Subclasses share the single flat ``HexRaysPyTools-ng/`` context-menu
    group (default = the group root).
    """

    menu_path: str = "HexRaysPyTools-ng/"

    def check(self, hx_view: Any) -> bool:
        raise NotImplementedError

    def update(self, ctx: Any) -> int:
        if ctx.widget_type == idaapi.BWN_PSEUDOCODE:
            return int(idaapi.AST_ENABLE_FOR_WIDGET)
        return int(idaapi.AST_DISABLE_FOR_WIDGET)


class HexRaysXrefAction(Action):
    """Action also enabled in Local Types view (BWN_TILIST)."""

    menu_path: str = "HexRaysPyTools-ng/"

    def check(self, hx_view: Any) -> bool:
        raise NotImplementedError

    @staticmethod
    def _is_local_types_widget(widget_type: int) -> bool:
        """Accept both current and legacy Local Types widget constants."""
        return widget_type in (
            idaapi.BWN_LOCTYPS,
            idaapi.BWN_TILVIEW,
            idaapi.BWN_TILIST,
        )

    def update(self, ctx: Any) -> int:
        if self._is_local_types_widget(ctx.widget_type):
            # Local Types does not emit Hex-Rays' hxe_populating_popup event,
            # so attach the action from the generic action update callback.
            idaapi.attach_action_to_popup(ctx.widget, None, self.name, self.menu_path)
            return int(idaapi.AST_ENABLE_FOR_WIDGET)
        if ctx.widget_type == idaapi.BWN_PSEUDOCODE:
            return int(idaapi.AST_ENABLE_FOR_WIDGET)
        return int(idaapi.AST_DISABLE_FOR_WIDGET)


class HexRaysPopupRequestHandler:
    """Wraps HexRaysPopupAction for the hxe_populating_popup event."""

    def __init__(self, action: HexRaysPopupAction | HexRaysXrefAction) -> None:
        self._action = action

    def handle(self, event: int, *args: Any) -> None:
        form, popup, hx_view = args
        if self._action.check(hx_view):
            # The 4th arg (popuppath) groups the action into a submenu.
            # "HexRaysPyTools-ng/" (trailing slash) creates a single flat
            # "HexRaysPyTools-ng" submenu containing every popup action.
            idaapi.attach_action_to_popup(form, popup, self._action.name, self._action.menu_path)
