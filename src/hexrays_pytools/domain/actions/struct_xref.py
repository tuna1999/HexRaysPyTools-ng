"""Struct field xref action (FindFieldXrefs)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .action import HexRaysXrefAction

if TYPE_CHECKING:
    from ..session import Session


class FindFieldXrefs(HexRaysXrefAction):
    """Show cross-references to the selected struct field."""

    description = "Field Xrefs"
    hotkey = "Ctrl+X"
    menu_path = "HexRaysPyTools/Structure/"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True
