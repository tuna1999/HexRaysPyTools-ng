"""4 event handlers: MemberDoubleClick, PotentialNegativeCollector, StructXrefCollector, SilentIfSwapper."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]

from ...infra.arch.arch import choose_virtual_func_address, to_hex
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
    """Run at CMAT_FINAL — populate XrefStorage with struct-field xrefs.

    The handler delegates to :class:`StructXrefCollectorVisitor` which walks
    the cfunc body looking for ``cot_memptr``/``cot_memref`` expressions and
    records the field offset + access type (R/W/Arg) for each.

    Uses ``session.xrefs`` (the Session-owned, netnode-backed XrefStorage)
    so the data persists across CMAT events.
    """

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def handle(self, event: int, *args: Any) -> None:
        if not args:
            return
        cfunc = args[0]
        if self._session is None or self._session.xrefs is None:
            logger.debug("StructXrefCollector: no session/xrefs — skipping")
            return
        visitor = StructXrefCollectorVisitor(cfunc, self._session.xrefs)
        visitor.process()


class StructXrefCollectorVisitor(idaapi.ctree_parentee_t):  # type: ignore[misc]
    """Walk a cfunc body and record struct-field cross-references.

    Mirrors the original ``core/callbacks/struct_xref_collector.py``. Records
    for each ``cot_memptr``/``cot_memref``:
    * ``ordinal`` — the struct's local-type ordinal (via
      :func:`get_ordinal`)
    * ``field_offset`` — byte offset of the field in the struct
    * ``ea`` — the closest real (non-BADADDR) ancestor's EA
    * ``usage_type`` — 'R' (read), 'W' (write), or 'Arg' (call argument)
    * ``one_line`` — decompiled text of the enclosing citem

    The whole visitor body is ctree-coupled (excluded from coverage gate).
    """

    def __init__(self, cfunc: Any, storage: Any) -> None:
        idaapi.ctree_parentee_t.__init__(self)  # noqa: N806 - IDA SWIG casing
        self._cfunc = cfunc
        self._function_address = int(cfunc.entry_ea)
        self._result: dict[int, dict[int, list[tuple[Any, ...]]]] = {}
        self._storage = storage

    def visit_expr(self, expression: Any) -> int:  # noqa: ARG002 - IDA SWIG
        from ...domain.types.tinfo_utils import get_ordinal

        if int(expression.op) == int(idaapi.cot_memptr):
            struct_type = expression.x.type.get_pointed_object()
        elif int(expression.op) == int(idaapi.cot_memref):
            struct_type = expression.x.type
        else:
            return 0

        ordinal = get_ordinal(struct_type)
        field_offset = int(expression.m)
        ea = self._find_ref_address(expression)
        usage_type = self._get_type(expression)

        if ea == int(idaapi.BADADDR) or not ordinal:
            logger.warning(
                "Failed to parse at address %s, ordinal - %s, type - %s",
                to_hex(int(ea)),
                int(ordinal),
                str(struct_type.dstr()),
            )

        one_line = self._get_line()
        occurrence_offset = ea - self._function_address
        xref_info = (occurrence_offset, one_line, usage_type)

        if ordinal not in self._result:
            self._result[ordinal] = {field_offset: [xref_info]}
        elif field_offset not in self._result[ordinal]:
            self._result[ordinal][field_offset] = [xref_info]
        else:
            self._result[ordinal][field_offset].append(xref_info)
        return 0

    def process(self) -> None:
        import time

        start = time.time()
        self.apply_to(self._cfunc.body, None)
        # Persist to the netnode-backed XrefStorage. Our new API takes
        # (func_offset, ordinal, field_xrefs) per call — iterate the
        # result dict and call update for each (ordinal, field_offset)
        # batch.
        func_offset = int(self._function_address) - int(idaapi.get_imagebase())
        for ordinal, field_dict in self._result.items():
            for _field_offset, xref_list in field_dict.items():
                # Pack the per-field list with its offset as a marker
                # (the new XrefStorage stores the list verbatim).
                self._storage.update(int(ordinal), func_offset, list(xref_list))
        logger.debug(
            "Xref processing: %.3f s, %d fields, %d ordinals",
            time.time() - start,
            sum(len(v) for v in self._result.values()),
            len(self._result),
        )

    def _find_ref_address(self, cexpr: Any) -> int:
        """Return the closest real (non-BADADDR) EA in the cexpr's ancestry."""
        ea = int(cexpr.ea)
        if ea != int(idaapi.BADADDR):
            return ea
        for p in reversed(self.parents):
            if int(p.ea) != int(idaapi.BADADDR):
                return int(p.ea)
        return int(idaapi.BADADDR)

    def _get_type(self, cexpr: Any) -> str:
        """Return the access type: ``R`` (read), ``W`` (write), or ``Arg``."""
        child = cexpr
        for p in reversed(self.parents):
            if p is None:
                continue
            if int(p.cexpr.op) == int(idaapi.cot_call):
                return "Arg"
            if not p.is_expr():
                return "R"
            if int(p.cexpr.op) == int(idaapi.cot_asg):
                if p.cexpr.x == child:
                    return "W"
                return "R"
            child = p.cexpr
        return "R"

    def _get_line(self) -> str:
        """Return the decompiled text of the enclosing citem (the line of code)."""
        for p in reversed(self.parents):
            if not p.is_expr():
                return str(idaapi.tag_remove(p.print1(self._cfunc)))
        return ""


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
