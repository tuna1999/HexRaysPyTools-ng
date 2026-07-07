"""Reusable idaapi.Choose subclass for list selection UI.

Moved from `ui/chooser.py` to `domain/chooser.py` (F1.a) because it does not
depend on Qt widgets — it's a thin wrapper around `idaapi.Choose`. This
eliminates 5 upward imports from domain/ to ui/ that violated the 5-layer
architecture rule.

Lives in domain/ (not ui/) because:
- No Qt dependency (just idaapi.Choose)
- Used by domain actions (struct_xref, structs_by_size, guess_allocation,
  negative_offsets, type_library) to display selection lists

If a future change needs Qt widgets here, that should be a class extending
this one in ui/, not this module.
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
