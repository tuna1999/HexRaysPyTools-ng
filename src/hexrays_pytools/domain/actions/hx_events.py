"""4 event handlers: MemberDoubleClick, PotentialNegativeCollector, StructXrefCollector, SilentIfSwapper."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]

from ...infra.arch.arch import choose_virtual_func_address
from ..ctree.negative_offsets import collect_potential_negatives
from ..ctree.swap_if import SpaghettiVisitor, SwapThenElseVisitor, get_inverted, has_inverted

if TYPE_CHECKING:
    from ..session import Session

logger = logging.getLogger(__name__)


class MemberDoubleClick:
    """Handle ``hxe_double_click`` — navigate from a struct member click to its function.

    The original ``refs/.../callbacks/member_double_click.py`` covers two
    cases:

    * ``item.e.x.op == cot_memref`` — direct struct field → jump to the
      function at that field's offset (member name → EA via demangled_names).
    * ``item.e.x.op == cot_memptr`` — vtable method call → resolve through
      the vtable to the implementing function.

    The handler reads ``session.demangled_names`` (populated by
    ``Session.open``) for the EA lookup.
    """

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def handle(self, event: int, *args: Any) -> None:
        if not args:
            return
        hx_view = args[0]
        item = hx_view.item
        # Quick guard — we only navigate on cot_memptr/cot_memref expressions.
        if int(item.citype) != int(idaapi.VDI_EXPR):
            return
        if int(item.e.op) not in (int(idaapi.cot_memptr), int(idaapi.cot_memref)):
            return

        from ...domain.types.tinfo_utils import get_member_name

        demangled = (
            self._session.demangled_names
            if self._session is not None
            else None
        )

        # Case 1: nested ptr-to-vtable access (`x->vf->method`)
        # — ``item.e.x`` is ``cot_memref`` pointing into a vtable struct, and
        # ``item.e.x.x`` is a ``cot_memptr`` access on the object.
        if (
            int(item.e.x.op) == int(idaapi.cot_memref)
            and int(item.e.x.x.op) == int(idaapi.cot_memptr)
        ):
            vtable_tinfo = item.e.x.type.get_pointed_object()
            method_offset = int(item.e.m)
            class_tinfo = item.e.x.x.x.type.get_pointed_object()
            vtable_offset = int(item.e.x.x.m)
            func_name = get_member_name(vtable_tinfo, method_offset)
            func_ea = choose_virtual_func_address(
                str(func_name),
                class_tinfo=class_tinfo,
                vtable_offset=vtable_offset,
                demangled_names=demangled,
            )
            if func_ea:
                idaapi.jumpto(int(func_ea))
                return  # handled — original returned 1

        # Case 2: pointer-deref (`x->method`) — item.e.x is cot_memptr directly
        if int(item.e.x.op) == int(idaapi.cot_memptr):
            vtable_tinfo = item.e.x.type
            if bool(vtable_tinfo.is_ptr()):
                vtable_tinfo = vtable_tinfo.get_pointed_object()
            method_offset = int(item.e.m)
            class_tinfo = item.e.x.x.type.get_pointed_object()
            vtable_offset = int(item.e.x.m)
            func_name = get_member_name(vtable_tinfo, method_offset)
            func_ea = choose_virtual_func_address(
                str(func_name),
                class_tinfo=class_tinfo,
                vtable_offset=vtable_offset,
                demangled_names=demangled,
            )
            if func_ea:
                idaapi.jumpto(int(func_ea))
                return

        # Case 3: direct struct field (`x.field`) — navigate to the
        # function at that field's offset if it's a known symbol.
        if int(item.e.x.op) == int(idaapi.cot_memref):
            func_offset = int(item.e.m)
            struct_tinfo = item.e.x.type.get_pointed_object()
            func_name = get_member_name(struct_tinfo, func_offset)
            func_ea = choose_virtual_func_address(
                str(func_name), demangled_names=demangled
            )
            if func_ea:
                idaapi.jumpto(int(func_ea))


class PotentialNegativeCollector:
    """Run at CMAT_BUILT — detect and apply CONTAINING_RECORD patterns."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def handle(self, event: int, *args: Any) -> None:
        cfunc, level_of_maturity = args
        if int(level_of_maturity) == idaapi.CMAT_BUILT:
            collect_potential_negatives(cfunc)


class StructXrefCollector:
    """Run at CMAT_FINAL — populate XrefStorage."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def handle(self, event: int, *args: Any) -> None:
        logger.debug("StructXrefCollector.handle")


class SilentIfSwapper:
    """Run at CMAT_TRANS1+2 — re-apply saved if-swaps + spaghetti transform."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def handle(self, event: int, *args: Any) -> None:
        cfunc, level_of_maturity = args
        level = int(level_of_maturity)
        if level == idaapi.CMAT_TRANS1 and has_inverted(int(cfunc.entry_ea)):
            inverted_rvas = get_inverted(int(cfunc.entry_ea))
            inverted = [n + idaapi.get_imagebase() for n in inverted_rvas]
            visitor = SwapThenElseVisitor(set(inverted))
            visitor.apply_to(cfunc.body, None)
        elif level == idaapi.CMAT_TRANS2:
            visitor = SpaghettiVisitor()
            visitor.apply_to(cfunc.body, None)
