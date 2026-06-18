"""Member-double-click action wrapper.

Note: the actual `hxe_double_click` navigation logic lives in the
`MemberDoubleClick` event handler in `hx_events.py`. This action class exists
so a hotkey-triggered variant can be registered separately if needed; it is
not part of the 27-action registry.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .action import HexRaysPopupAction

if TYPE_CHECKING:
    from ..session import Session


class MemberDoubleClickAction(HexRaysPopupAction):
    """Hotkey-triggered variant of the MemberDoubleClick navigation."""

    description = "Jump to virtual function"
    hotkey = None

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True
