"""Base classes for actions (right-click menu + hotkey)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]

if TYPE_CHECKING:
    from ..session import Session


class Action(idaapi.action_handler_t):  # type: ignore[misc]
    """Base class for all actions."""

    description: str = ""
    hotkey: str | None = None

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
    """Action attached to right-click menu in pseudocode."""

    def check(self, hx_view: Any) -> bool:
        raise NotImplementedError

    def update(self, ctx: Any) -> int:
        if ctx.widget_type == idaapi.BWN_PSEUDOCODE:
            return int(idaapi.AST_ENABLE_FOR_WIDGET)
        return int(idaapi.AST_DISABLE_FOR_WIDGET)


class HexRaysXrefAction(Action):
    """Action also enabled in Local Types view (BWN_TILIST)."""

    def check(self, hx_view: Any) -> bool:
        raise NotImplementedError

    def update(self, ctx: Any) -> int:
        if ctx.widget_type in (idaapi.BWN_PSEUDOCODE, idaapi.BWN_TILIST):
            return int(idaapi.AST_ENABLE_FOR_WIDGET)
        return int(idaapi.AST_DISABLE_FOR_WIDGET)


class HexRaysPopupRequestHandler:
    """Wraps HexRaysPopupAction for the hxe_populating_popup event."""

    def __init__(self, action: HexRaysPopupAction) -> None:
        self._action = action

    def handle(self, event: int, *args: Any) -> None:
        form, popup, hx_view = args
        if self._action.check(hx_view):
            idaapi.attach_action_to_popup(form, popup, self._action.name, None)
