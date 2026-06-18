"""Function signature modifier actions (ConvertToUsercall, AddRemoveReturn, RemoveArgument)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .action import HexRaysPopupAction

if TYPE_CHECKING:
    from ..session import Session


class ConvertToUsercall(HexRaysPopupAction):
    """Convert the current function signature to __usercall."""

    description = "Convert to __usercall"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True


class AddRemoveReturn(HexRaysPopupAction):
    """Toggle a return value on the current function."""

    description = "Add/Remove Return"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True


class RemoveArgument(HexRaysPopupAction):
    """Remove the selected argument from the function signature."""

    description = "Remove Argument"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass

    def check(self, hx_view: Any) -> bool:
        return True
