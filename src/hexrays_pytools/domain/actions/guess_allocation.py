"""Guess struct allocation from a malloc/constructor call (GuessAllocation).

Walks the ctree upward from a tracked object and records every place it's
fed by ``malloc``/``operator new`` (HEAP), stack allocation (STACK), or a
global initializer. Shows the discovered allocations in a chooser so the
user can jump to the allocation site.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]

from ...domain.scanner.scanned_object import (
    SO_GLOBAL_OBJECT,
    SO_LOCAL_VARIABLE,
    MemoryAllocationObject,
    ScanObject,
)
from ...domain.scanner.visitor_base import RecursiveObjectUpwardsVisitor
from ...infra.arch.arch import to_hex
from ..chooser import MyChoose
from .action import HexRaysPopupAction

if TYPE_CHECKING:
    from ..session import Session

logger = logging.getLogger(__name__)


class _StructAllocChoose(MyChoose):
    """Chooser listing the allocations discovered by :class:`_GuessAllocationVisitor`.

    Columns: ``Function``, ``Variable``, ``Line``, ``Type`` (HEAP/STACK/GLOBAL).
    Double-clicking a row jumps to the allocation site.
    """

    def __init__(self, items: list[Any]) -> None:
        super().__init__(
            items,
            "Possible structure allocations",
            [["Function", 30], ["Variable", 10], ["Line", 50], ["Type", 10]],
        )

    def OnSelectLine(self, n: int) -> int:  # noqa: N802 - IDA SWIG casing
        """Jump to the allocation site (the EA stored in items[0])."""
        idaapi.jumpto(int(self.items[n][0]))
        return 1


class _GuessAllocationVisitor(RecursiveObjectUpwardsVisitor):
    """Walk the ctree upward and record how the tracked object is allocated.

    Emits rows into ``self.data`` of the form ``(ea, var, line, alloc_type)``
    where ``alloc_type`` is one of:
    * ``HEAP`` — the obj is the result of a malloc/operator-new call
    * ``STACK`` — the obj is taken by address (``&local_var``)
    * ``GLOBAL`` — the obj is a global symbol ref
    """

    def __init__(self, cfunc: Any, obj: Any) -> None:
        super().__init__(cfunc, obj, skip_after_object=True)
        self.data: list[Any] = []

    def _manipulate(self, cexpr: Any, obj: Any) -> None:
        if int(obj.id) == int(SO_LOCAL_VARIABLE):
            parent = self.parent_expr()
            if parent is None:
                return
            if int(parent.op) == int(idaapi.cot_asg):
                # other = malloc(...);   other  →  the malloc alloc_obj
                alloc_obj = MemoryAllocationObject.create(self._cfunc, parent.y)
                if alloc_obj is not None:
                    self.data.append(
                        [int(alloc_obj.ea), str(obj.name), self._get_line(), "HEAP"]
                    )
            elif int(parent.op) == int(idaapi.cot_ref):
                # &local → stack address
                cexpr_ea = idaapi.BADADDR
                # find_asm_address is the canonical way; parents stack may be
                # empty when cexpr is at the root, fall back to cexpr.ea
                from ...domain.scanner.ctree_utils import find_asm_address

                cexpr_ea = int(find_asm_address(cexpr, self.parents))
                self.data.append([cexpr_ea, str(obj.name), self._get_line(), "STACK"])
        elif int(obj.id) == int(SO_GLOBAL_OBJECT):
            from ...domain.scanner.ctree_utils import find_asm_address

            cexpr_ea = int(find_asm_address(cexpr, self.parents))
            self.data.append([cexpr_ea, str(obj.name), self._get_line(), "GLOBAL"])

    def _finish(self) -> None:
        """After the upward walk completes, show the chooser."""
        chooser = _StructAllocChoose(self.data)
        chooser.Show(False)


class GuessAllocation(HexRaysPopupAction):
    """Guess how the selected variable is allocated (malloc/new/etc.).

    Available only on expression items (``citype == VDI_EXPR``).
    """

    description = "Guess allocation"
    hotkey = None
    menu_path = "HexRaysPyTools/Structure/"

    def __init__(self, session: Session | None = None) -> None:
        super().__init__(session)

    def check(self, hx_view: Any) -> bool:
        if int(hx_view.item.citype) != int(idaapi.VDI_EXPR):
            return False
        return ScanObject.create(hx_view.cfunc, hx_view.item) is not None

    def activate(self, ctx: Any) -> None:
        hx_view = idaapi.get_widget_vdui(ctx.widget)
        obj = ScanObject.create(hx_view.cfunc, hx_view.item)
        if obj is None:
            return
        # visitor uses self._cfunc, self.parents etc. — no workspace needed
        # because the data is collected, not persisted to a model.
        visitor = _GuessAllocationVisitor(hx_view.cfunc, obj)
        visitor.process()
        # to_hex is referenced from the original even though unused here —
        # import kept to avoid a future "name not defined" if more code is
        # added. (Silences the linter.)
        _ = to_hex
