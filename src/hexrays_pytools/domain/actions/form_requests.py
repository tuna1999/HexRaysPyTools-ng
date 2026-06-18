"""Form-request actions: open graph, classes, structure builder."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .action import Action, HexRaysPopupAction

if TYPE_CHECKING:
    from ..session import Session


class ShowGraph(Action):
    """Open the ctree graph for the current function."""

    description = "Show graph"
    hotkey = "G"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        # Real implementation requires UI graph widget; stub for now
        pass


class ShowClasses(Action):
    """Open the Classes (virtual tables) viewer."""

    description = "Classes"
    hotkey = "Alt+F1"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass


class ShowStructureBuilder(HexRaysPopupAction):
    """Open the Structure Builder widget from the pseudocode popup."""

    description = "Show Structure Builder"
    hotkey = "Alt+F8"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True
