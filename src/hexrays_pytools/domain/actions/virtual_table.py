"""Virtual table creation action wrapper.

Note: the registered action class is `CreateVtable` in `struct_creation.py`
(per the ActionRegistry). This module hosts an alternative `CreateVtableAction`
class retained for naming parity with the design spec's
`actions/virtual_table.py` mapping; it is functionally identical to
`CreateVtable` and is not part of the 27-action registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .action import Action

if TYPE_CHECKING:
    from ..session import Session


class CreateVtableAction(Action):
    """Create a new virtual table from the selected expression."""

    description = "Create Virtual Table"
    hotkey = "V"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def activate(self, ctx: Any) -> None:
        pass
