"""UI chooser stubs.

This module provides placeholder chooser classes until the full UI layer is
implemented (planned for Task 3.5). The stubs subclass `idaapi.Choose` so they
can be exercised under the mock_ida test infrastructure, and expose the
minimum interface required by callers in the domain layer
(`MyChoose.OnClose`, `OnGetLine`, `OnGetSize`, `Show`).
"""
from __future__ import annotations

from typing import Any

import idaapi  # type: ignore[import-not-found]


class MyChoose(idaapi.Choose):  # type: ignore[misc]
    """Minimal modal chooser used by the TIL picker.

    Production implementation (Task 3.5) will add column formatting, icons,
    and double-click handling. For now this only stores items and exposes the
    IDA `Choose` callback surface.
    """

    def __init__(self, items: list[Any], title: str, cols: list[Any], icon: int = -1) -> None:
        idaapi.Choose.__init__(  # noqa: N806 - IDA SWIG casing
            self, title, cols, flags=idaapi.Choose.CH_MODAL, icon=icon
        )
        self.items = items

    def OnClose(self) -> None:  # noqa: N802 - IDA SWIG casing
        """Called by IDA when the chooser window closes."""

    def OnGetLine(self, n: int) -> list[Any]:  # noqa: N802 - IDA SWIG casing
        """Return the n-th row."""
        result: list[Any] = self.items[n]
        return result

    def OnGetSize(self) -> int:  # noqa: N802 - IDA SWIG casing
        """Return the row count."""
        return len(self.items)
