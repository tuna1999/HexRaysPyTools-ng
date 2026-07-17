"""Swap if/then/else logic + persistent swap tracking.

Ported from the original `callbacks/swap_if.py` (186 LOC). Two halves:

  * **ctree manipulation** — ``inverse_if_condition`` flips an ``if``'s
    condition with logical-not and swaps its then/else branches.
    ``SwapThenElseVisitor`` re-applies stored swaps on re-decompile.
    ``SpaghettiVisitor`` flattens ``if (...) {...} return;`` into a straight
    fall-through (the "spaghetti" readability transform).
  * **persistent storage** — the plugin remembers which ``if`` sites were
    swapped so the swap survives re-decompilation. The original used
    ``idc.create_array`` (legacy); this port uses a netnode instead.

Everything operates on live Hex-Rays ctree objects, so this module is not
unit-testable with mocks — it is verified by use in a real IDA.
"""

from __future__ import annotations

import logging
from typing import Any

import idaapi  # type: ignore[import-not-found]

from ...infra.idb.netnode import Netnode

logger = logging.getLogger(__name__)

# Netnode storing the set of swapped-if RVAs per function.
# Keyed by function RVA: node.supstr(func_rva) -> "rva1 rva2 ..." (space-joined).
_SWAP_NODE = "$hexrays_pytools/swap_if_then_else"


# --- ctree manipulation -------------------------------------------------------


def inverse_if_condition(cif: Any) -> None:
    """Logically-invert an ``if``'s condition in place.

    cexpr_t becomes broken after the swap, but it still has an ``assign``
    method that copies one expr into another — use it to snapshot the
    condition, wrap it in ``lnot``, and swap it back in.
    """
    cit_if_condition = cif.expr
    tmp_cexpr = idaapi.cexpr_t()
    tmp_cexpr.assign(cit_if_condition)
    new_if_condition = idaapi.lnot(tmp_cexpr)
    cif.expr.swap(new_if_condition)
    del cit_if_condition


def inverse_if(cif: Any) -> None:
    """Invert the condition AND swap the then/else branches of ``cif``."""
    inverse_if_condition(cif)
    idaapi.qswap(cif.ithen, cif.ielse)


# --- persistent swap storage (netnode-backed) ---------------------------------


def _func_rva(func_ea: int) -> int:
    return int(func_ea - idaapi.get_imagebase())


def get_inverted(func_ea: int) -> set[int]:
    """Return the set of swapped-if RVAs for the function at `func_ea`."""
    node = Netnode(_SWAP_NODE)
    raw = node.get_string(key=_func_rva(func_ea))
    if not raw:
        return set()
    return {int(x) for x in raw.split() if x}


def has_inverted(func_ea: int) -> bool:
    """Return True if the function at `func_ea` has any stored swaps."""
    return bool(get_inverted(func_ea))


def invert(func_ea: int, if_ea: int) -> None:
    """Toggle whether the ``if`` at `if_ea` is recorded as swapped."""
    func_rva = _func_rva(func_ea)
    if_rva = int(if_ea - idaapi.get_imagebase())
    node = Netnode(_SWAP_NODE)
    inverted = get_inverted(func_ea)
    if if_rva in inverted:
        inverted.discard(if_rva)
    else:
        inverted.add(if_rva)
    node.set_string(" ".join(str(x) for x in inverted), key=func_rva)


# --- the action + the re-decompile visitor ------------------------------------


def swap_if_then_else(hx_view: Any) -> bool:
    """Swap the then/else branches of the ``if`` at the cursor.

    FIX B8: the original called ``hx_view.refresh_ctext()`` (removed in newer
    Hex-Rays SDKs); this uses ``hx_view.refresh_view(True)``.
    """
    if hx_view is None:
        return False
    item = hx_view.item
    if item.citype != idaapi.VDI_EXPR:
        return False
    insn = item.it.to_specific_type
    if insn.op != idaapi.cit_if or insn.cif.ielse is None:
        return False
    inverse_if(insn.cif)
    hx_view.refresh_view(True)  # FIX B8: was refresh_ctext()
    invert(int(hx_view.cfunc.entry_ea), int(insn.ea))
    return True


def can_swap(hx_view: Any) -> bool:
    """Return True if the cursor is on an ``if`` that has both branches."""
    if hx_view is None:
        return False
    item = hx_view.item
    if item.citype != idaapi.VDI_EXPR:
        return False
    insn = item.it.to_specific_type
    return bool(insn.op == idaapi.cit_if and insn.cif.ielse is not None)


class SwapThenElseVisitor(idaapi.ctree_parentee_t):  # type: ignore[misc]
    """Re-applies stored swaps when a function is re-decompiled."""

    def __init__(self, inverted: set[int]) -> None:
        super().__init__()
        self._inverted = inverted

    def visit_insn(self, insn: Any) -> int:
        if insn.op != idaapi.cit_if or insn.cif.ielse is None:
            return 0
        if int(insn.ea) in self._inverted:
            inverse_if(insn.cif)
        return 0

    def apply_to(self, *args: Any) -> None:
        if self._inverted:
            super().apply_to(*args)


class SpaghettiVisitor(idaapi.ctree_parentee_t):  # type: ignore[misc]
    """Flatten ``if (...) { ... } return;`` into straight-line fall-through."""

    def visit_insn(self, instruction: Any) -> int:
        if instruction.op != idaapi.cit_block:
            return 0

        while True:
            cblock = instruction.cblock
            size = cblock.size()
            # Need a block whose last two statements are `if` then `return`.
            if size < 2:
                break
            if cblock.at(size - 2).op != idaapi.cit_if:
                break

            cif = cblock.at(size - 2).cif
            if cblock.back().op != idaapi.cit_return or cif.ielse:
                break

            cit_then = cif.ithen
            # Skip if only one (not "if") statement in the "then" branch.
            if cit_then.cblock.size() == 1 and cit_then.cblock.front().op != idaapi.cit_if:
                return 0

            inverse_if_condition(cif)

            # Take the return off the end; we'll move it into the then-branch.
            cit_return = idaapi.cinsn_t()
            cit_return.assign(instruction.cblock.back())
            cit_return.thisown = False
            instruction.cblock.pop_back()

            # Spill the then-branch statements into the main block.
            while cit_then.cblock:
                instruction.cblock.push_back(cit_then.cblock.front())
                cit_then.cblock.pop_front()

            # Put the return back at the end of the main block unless the
            # spilled statements already end in a return/goto.
            if instruction.cblock.back().op not in (idaapi.cit_return, idaapi.cit_goto):
                new_return = idaapi.cinsn_t()
                new_return.thisown = False
                new_return.assign(cit_return)
                instruction.cblock.push_back(new_return)

            cit_then.cblock.push_back(cit_return)
        return 0
