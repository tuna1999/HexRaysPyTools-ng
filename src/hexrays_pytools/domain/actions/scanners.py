"""Scanner actions: shallow/deep scan, recognize shape, scan returns and functions."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .action import Action, HexRaysPopupAction

if TYPE_CHECKING:
    from ..session import Session


class Scanner(HexRaysPopupAction):
    """Abstract scanner. Concrete subclasses implement `activate`."""

    description = "Scan"
    hotkey: str | None = None

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True


class ShallowScanVariable(Scanner):
    """Scan the selected variable once, depth-limited."""

    description = "Scan Variable"
    hotkey = "F"


class DeepScanVariable(Scanner):
    """Recursively scan the selected variable."""

    description = "Deep Scan Variable"
    hotkey = "Shift+Alt+F"


class RecognizeShape(Scanner):
    """Attempt to recognize the shape of the selected expression."""

    description = "Recognize Shape"


class DeepScanReturn(Scanner):
    """Scan variables returned by the current function."""

    description = "Deep Scan Returned Variables"


class DeepScanFunctions(Action):
    """Scan the first argument across all callers of the selected function."""

    description = "Scan First Argument"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass
