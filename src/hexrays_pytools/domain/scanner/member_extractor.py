"""Struct-member scanner engine.

The :class:`SearchVisitor` walks a decompiled function looking for pointer /
xword expressions that reveal struct member offsets. Each match is converted
into a :class:`ScannedObject` (with 'd') and added to the structure model
held by the workspace.

Three concrete subclasses drive the scanner:

* :class:`NewShallowSearchVisitor` — non-recursive (this function only)
* :class:`NewDeepSearchVisitor` — recursive (also walks callees)
* :class:`DeepReturnVisitor` — recursive + iterates callers

The walk itself uses the live Hex-Rays ctree via ``ctree_parentee_t`` dispatch
in :mod:`.visitor_base`; this module is not unit-testable end-to-end with
mocks. Tests cover the Python-level state and the pure static helpers.

Ported from the original ``core/variable_scanner.py`` (337 LOC).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]

from ...domain.recon.discovered_vtable import DiscoveredVTable
from ...domain.recon.member import Member, VoidMember
from ...domain.recon.workspace import ReconWorkspace
from ...domain.types.func_type import get_call_argument_info
from ...domain.types.tinfo_utils import is_legal_type
from ...infra.arch.arch import (
    get_funcs_calling_address,
    get_insn_mem_size,
    is_code_ea,
    to_hex,
)
from .ctree_utils import find_asm_address
from .helpers import decompile_function
from .scanned_object import ScannedObject
from .visitor_base import (
    ObjectDownwardsVisitor,
    RecursiveObjectDownwardsVisitor,
)

if TYPE_CHECKING:
    from ...domain.const import Consts

logger = logging.getLogger(__name__)


class SearchVisitor(ObjectDownwardsVisitor):
    """Extract struct member candidates from a cfunc.

    Override :meth:`_manipulate` to react to each cexpr that matches a tracked
    :class:`ScanObject`. The base :class:`ObjectDownwardsVisitor` handles the
    assignment-chain tracking; this subclass only adds the extraction logic.

    ``origin`` is the struct offset the user clicked — every member produced
    by this visitor is tagged with it for grouping in the workspace.
    ``workspace`` is the :class:`ReconWorkspace` whose ``model.add_row()`` is
    called for each match. ``consts`` is the per-session :class:`Consts`
    dataclass that provides the tinfo singletons (PX_WORD_TINFO, DUMMY_FUNC,
    VOID_TINFO, …) the extraction logic compares against.
    """

    def __init__(
        self,
        cfunc: Any,
        origin: int,
        obj: Any,
        workspace: ReconWorkspace,
        consts: Consts | None = None,
    ) -> None:
        # skip_until_object=True — don't fire _manipulate until we reach the
        # expression the user actually clicked.
        super().__init__(cfunc, obj, None, True)
        self._origin = int(origin)
        self._workspace = workspace
        self._consts = consts

    @property
    def _px_word_tinfo(self) -> Any:
        return self._consts.px_word_tinfo if self._consts is not None else None

    @property
    def _void_tinfo(self) -> Any:
        return self._consts.void_tinfo if self._consts is not None else None

    @property
    def _const_void_tinfo(self) -> Any:
        return self._consts.const_void_tinfo if self._consts is not None else None

    @property
    def _const_pchar_tinfo(self) -> Any:
        return self._consts.const_pchar_tinfo if self._consts is not None else None

    @property
    def _pchar_tinfo(self) -> Any:
        return self._consts.pchar_tinfo if self._consts is not None else None

    @property
    def _const_pvoid_tinfo(self) -> Any:
        return self._consts.const_pvoid_tinfo if self._consts is not None else None

    @property
    def _pvoid_tinfo(self) -> Any:
        return self._consts.pvoid_tinfo if self._consts is not None else None

    @property
    def _char_tinfo(self) -> Any:
        return self._consts.char_tinfo if self._consts is not None else None

    @property
    def _dummy_func(self) -> Any:
        return self._consts.dummy_func if self._consts is not None else None

    def _manipulate(self, cexpr: Any, obj: Any) -> None:
        # 1. Skip types we can't reason about (forward-declared pointers with
        #    unknown size, unknown primitives, etc.).
        if obj.tinfo is not None and not is_legal_type(obj.tinfo):
            cexpr_ea = find_asm_address(cexpr, self.parents)
            logger.warning(
                "Variable %s has weird type at %s",
                str(obj.name),
                to_hex(int(cexpr_ea)),
            )
            return

        # 2. Pick the extraction strategy by expression type.
        if cexpr.type.is_ptr():
            member = self._extract_member_from_pointer(cexpr, obj)
        else:
            member = self._extract_member_from_xword(cexpr, obj)
        if member is None:
            logger.debug("  no member extracted from '%s'", str(obj.name))
            return

        # 3. Persist.
        self._emit_scan_hit(cexpr, obj, member)
        logger.debug(
            "  created member offset=%d tinfo=%s scanned=%s",
            int(member.offset),
            str(member.tinfo),
            str(member.scanned_variables),
        )
        model = self._workspace.model
        if model is not None:
            model.add_row(member)

    def _emit_scan_hit(self, cexpr: Any, obj: Any, member: Any) -> None:
        """Log every discovered member candidate at DEBUG level."""
        func_ea = int(getattr(self._cfunc, "entry_ea", 0))
        func_name = str(idaapi.get_name(func_ea) or f"sub_{func_ea:X}")
        source_ea = int(find_asm_address(cexpr, self.parents))
        obj_name = str(getattr(obj, "name", "<unknown>"))
        member_name = str(getattr(member, "name", "") or "<unnamed>")
        member_tinfo = getattr(member, "tinfo", None)
        type_name = str(member_tinfo) if member_tinfo is not None else type(member).__name__
        message = (
            f"[HexRaysPyTools][Scan Hit] {func_name}@0x{func_ea:X} "
            f"source=0x{source_ea:X} object={obj_name} "
            f"offset=0x{int(member.offset):X} member={member_name} type={type_name}"
        )
        logger.debug("%s", message)

    # --- Member construction ------------------------------------------------

    def _get_member(
        self,
        offset: int,
        cexpr: Any,
        obj: Any,
        tinfo: Any = None,
        obj_ea: Any = None,
        is_array: bool = False,
    ) -> Any:
        """Build the right ``Member``/``VoidMember``/``DiscoveredVTable`` for the offset.

        Heuristics:
        * ``obj_ea`` in a discovered vtable → :class:`DiscoveredVTable`.
        * ``obj_ea`` is code → decompile it and use the function's tinfo
          (or :data:`Consts.dummy_func` if decompile failed).
        * ``tinfo`` is void / const void → :class:`VoidMember` (size 0).
        * ``tinfo`` is const char* → :class:`Member` with char*.
        * ``tinfo`` is const void* → :class:`Member` with void*.
        * Otherwise strip the const bit and build a :class:`Member`.
        """
        cexpr_ea = find_asm_address(cexpr, self.parents)
        if int(offset) < 0:
            logger.error(
                "Considered to be impossible: offset - %d, obj - %s",
                int(offset),
                to_hex(int(cexpr_ea)),
            )
            raise AssertionError

        applicable = not bool(self.crippled)
        scan_obj = ScannedObject.create(obj, int(cexpr_ea), self._origin, applicable)

        if obj_ea is not None and int(obj_ea) != 0:
            if DiscoveredVTable.check_address(int(obj_ea)):
                logger.debug(
                    "    _get_member off=%d -> DiscoveredVTable @ %s",
                    int(offset),
                    to_hex(int(obj_ea)),
                )
                return DiscoveredVTable(
                    offset=int(offset),
                    tinfo=None,
                    name=str(scan_obj.name),
                    origin=self._origin,
                    address=int(obj_ea),
                    scanned_variables={scan_obj},
                )
            if is_code_ea(int(obj_ea)):
                cfunc = decompile_function(int(obj_ea))
                if cfunc is not None:
                    func_tinfo = cfunc.type
                    func_tinfo.create_ptr(func_tinfo)
                    tinfo = func_tinfo
                else:
                    tinfo = self._dummy_func
                logger.debug(
                    "    _get_member off=%d -> Member(funcptr) @ %s tinfo=%s",
                    int(offset),
                    to_hex(int(obj_ea)),
                    str(tinfo),
                )
                return Member(
                    offset=int(offset),
                    tinfo=tinfo,
                    origin=self._origin,
                    scanned_variables={scan_obj},
                )

        if (
            tinfo is None
            or (self._void_tinfo is not None and tinfo.equals_to(self._void_tinfo))
            or (self._const_void_tinfo is not None and tinfo.equals_to(self._const_void_tinfo))
        ):
            logger.debug("    _get_member off=%d -> VoidMember", int(offset))
            return VoidMember(
                offset=int(offset),
                origin=self._origin,
                scanned_variables={scan_obj},
            )

        if self._const_pchar_tinfo is not None and tinfo.equals_to(self._const_pchar_tinfo):
            tinfo = self._pchar_tinfo
        elif self._const_pvoid_tinfo is not None and tinfo.equals_to(self._const_pvoid_tinfo):
            tinfo = self._pvoid_tinfo
        else:
            tinfo.clr_const()
        logger.debug(
            "    _get_member off=%d -> Member tinfo=%s",
            int(offset),
            str(tinfo),
        )
        return Member(
            offset=int(offset),
            tinfo=tinfo,
            origin=self._origin,
            scanned_variables={scan_obj},
            is_array=is_array,
        )

    def _parse_call(
        self,
        call_cexpr: Any,
        arg_cexpr: Any,
        offset: int,  # noqa: ARG002 - kept for API parity with original
    ) -> Any:
        """Return the dereffed tinfo for the argument at the call site.

        Falls back to :data:`Consts.char_tinfo` if no tinfo can be derived —
        the original comment notes "TODO: Find example with UTF-16 strings".
        """
        _idx, tinfo = get_call_argument_info(call_cexpr, arg_cexpr)
        if tinfo is not None:
            return self._deref_tinfo(tinfo)
        return self._char_tinfo

    def _parse_left_assignee(
        self,
        cexpr: Any,  # noqa: ARG002 - stub for API parity
        offset: int,  # noqa: ARG002 - stub for API parity
    ) -> None:
        """Stub — the original's `pass` body; future home for left-of-= parsing."""
        # Original is `pass`; left-assignee extraction is not currently
        # implemented (the original's comment also leaves it as a TODO).

    # --- Pointer expression extraction --------------------------------------

    def _extract_member_from_pointer(
        self,
        cexpr: Any,
        obj: Any,
    ) -> Any:
        parents_type = [idaapi.get_ctype_name(int(x.cexpr.op)) for x in list(self.parents)[:0:-1]]
        parents = [x.cexpr for x in list(self.parents)[:0:-1]]

        logger.debug(
            "Parsing expression %s. Parents - %s",
            str(obj.name),
            str(parents_type),
        )

        # Extracting offset and removing expression parents making this offset
        if len(parents_type) >= 1 and parents_type[0] in ("idx", "add"):
            # `obj[idx]` or `(TYPE *) + x`
            if int(parents[0].y.op) != int(idaapi.cot_num):
                # Dynamic offset — array evidence (TRex colocation §3.3.3):
                # a symbolic index over a base pointer means the base points
                # at a run of elements, not a scalar field.
                return self._extract_array_member(cexpr, obj, parents[0], parents_type[0])
            offset = int(parents[0].y.numval()) * int(cexpr.type.get_ptrarr_objsize())
            cexpr = self.parent_expr()
            if parents_type[0] == "add":
                del parents_type[0]
                del parents[0]
        elif parents_type[0:2] == ["cast", "add"]:
            # (TYPE *)obj + offset or (TYPE)obj + offset
            if int(parents[1].y.op) != int(idaapi.cot_num):
                logger.debug("  ptr: skip '%s' (dynamic cast+add offset)", str(obj.name))
                return None
            if bool(parents[0].type.is_ptr()):
                size = int(parents[0].type.get_ptrarr_objsize())
            else:
                size = 1
            offset = int(parents[1].theother(parents[0]).numval()) * size
            cexpr = parents[1]
            del parents_type[0:2]
            del parents[0:2]
        else:
            offset = 0

        return self._extract_member(cexpr, obj, offset, parents, parents_type)

    def _extract_array_member(self, cexpr: Any, obj: Any, node: Any, kind: str) -> Any:
        """Dynamic-index access → array member evidence (TRex colocation §3.3.3).

        ``base[i]`` / ``base + i`` with symbolic ``i``: the element type is the
        deref expression's own type; the array start offset is the constant
        term of the index expression (``base[i + 3]`` → offset ``3 * elemsize``),
        or 0 for a bare symbolic index. Element count is unknowable statically
        (TRex models these as flexible array members).
        """
        try:
            elem_size = int(cexpr.type.get_ptrarr_objsize())
        except (AttributeError, RuntimeError, TypeError, ValueError):
            logger.debug("  array: skip '%s' (no element size)", str(obj.name))
            return None

        const_term = 0
        if kind == "idx":
            elem_tinfo = node.type if is_legal_type(node.type) else None
            index_expr = node.y
            if int(index_expr.op) in (int(idaapi.cot_add), int(idaapi.cot_sub)):
                negate = int(index_expr.op) == int(idaapi.cot_sub)
                left, right = index_expr.x, index_expr.y
                if int(left.op) == int(idaapi.cot_num):
                    const_term = int(left.numval())
                elif int(right.op) == int(idaapi.cot_num):
                    const_term = -int(right.numval()) if negate else int(right.numval())
        else:  # "add" — pointer arithmetic with a symbolic offset
            elem_tinfo = self._deref_tinfo(cexpr.type)
        if elem_tinfo is None:
            elem_tinfo = self._deref_tinfo(cexpr.type)
        if elem_tinfo is None:
            logger.debug("  array: skip '%s' (no element type)", str(obj.name))
            return None

        offset = const_term * elem_size
        if offset < 0:
            logger.debug("  array: skip '%s' (negative offset %d)", str(obj.name), offset)
            return None
        logger.debug(
            "  array: '%s' dynamic index -> element %s at offset %d",
            str(obj.name),
            str(elem_tinfo),
            offset,
        )
        return self._get_member(offset, cexpr, obj, elem_tinfo, is_array=True)

    def _extract_member_from_xword(
        self,
        cexpr: Any,
        obj: Any,
    ) -> Any:
        parents_type = [idaapi.get_ctype_name(int(x.cexpr.op)) for x in list(self.parents)[:0:-1]]
        parents = [x.cexpr for x in list(self.parents)[:0:-1]]

        logger.debug(
            "Parsing expression %s. Parents - %s",
            str(obj.name),
            str(parents_type),
        )

        if len(parents_type) >= 1 and parents_type[0] == "add":
            other = parents[0].theother(cexpr)
            if int(other.op) != int(idaapi.cot_num):
                logger.debug("  xword: skip '%s' (dynamic add offset)", str(obj.name))
                return None
            offset = int(other.numval())
            cexpr = self.parent_expr()
            del parents_type[0]
            del parents[0]
        else:
            offset = 0

        return self._extract_member(cexpr, obj, offset, parents, parents_type)

    def _extract_member(
        self,
        cexpr: Any,
        obj: Any,
        offset: int,
        parents: list[Any],
        parents_type: list[str],
    ) -> Any:
        if len(parents_type) >= 1 and parents_type[0] == "cast":
            default_tinfo = parents[0].type
            cexpr = parents[0]
            del parents_type[0]
            del parents[0]
        else:
            default_tinfo = self._px_word_tinfo

        if len(parents_type) >= 1 and parents_type[0] in ("idx", "ptr"):
            # TRex-style behavior capture: the deref/index expression's own
            # type is the observed copy width (`a1[2]` on `_DWORD *` observes
            # a 4-byte copy) — richer than the pointer-sized PX_WORD guess.
            deref_tinfo = parents[0].type
            if not is_legal_type(deref_tinfo):
                deref_tinfo = self._deref_tinfo(default_tinfo)
            deref_tinfo = self._asm_narrowed_tinfo(deref_tinfo, parents[0])
            if len(parents_type) >= 2 and parents_type[1] == "cast":
                cexpr = parents[0]
                del parents_type[0]
                del parents[0]
            # A value cast after the load is a post-load operation — it never
            # changes the observed memory-access width (TRex COPY_SIZES come
            # from the deref expression, not from value contexts).
            default_tinfo = deref_tinfo

            if len(parents_type) >= 2 and parents_type[1] == "asg":
                if parents[1].x == parents[0]:
                    # *(TYPE *)(var + x) = ??? — the STORE's memory width is
                    # the deref type; the value may still contribute richer
                    # structure (funcptr / vtable) at the same or wider width.
                    obj_ea = self._extract_obj_ea(parents[1].y)
                    asg_tinfo = self._wider_tinfo(default_tinfo, parents[1].y.type)
                    return self._get_member(int(offset), cexpr, obj, asg_tinfo, obj_ea)
                # lhs = *(TYPE *)(var + x) — a READ into a local: the local's
                # type is a value context, not memory evidence; the deref
                # (asm-narrowed) type is the whole observation.
                return self._get_member(int(offset), cexpr, obj, default_tinfo)
            if len(parents_type) >= 2 and parents_type[1] == "call":
                if parents[1].x == parents[0]:
                    # ((type (__some_call *)(..., ..., ...))(var[idx]))(...)
                    return self._get_member(int(offset), cexpr, obj, parents[0].type)
                _idx, tinfo = get_call_argument_info(parents[1], parents[0])
                if default_tinfo is None:
                    # No deref width available — fall back to the callee's
                    # parameter type (a guess) / char*.
                    tinfo = tinfo if tinfo is not None else self._pchar_tinfo
                    return self._get_member(int(offset), cexpr, obj, tinfo)
                # The callee's parameter type is a decompiler guess, not a
                # memory access — the deref width is the observed copy size
                # (TRex: pass-as-argument adds no COPY_SIZES evidence).
                return self._get_member(int(offset), cexpr, obj, default_tinfo)
            return self._get_member(int(offset), cexpr, obj, default_tinfo)

        if len(parents_type) >= 1 and parents_type[0] == "call":
            # call(..., (TYPE)(var + x), ...)
            tinfo = self._parse_call(parents[0], cexpr, int(offset))
            return self._get_member(int(offset), cexpr, obj, tinfo)

        if len(parents_type) >= 1 and parents_type[0] == "asg" and parents[0].y == cexpr:
            # other_obj = (TYPE) (var + offset) — pointer-arithmetic assignment
            # is real field-offset evidence; keep the pointer-width member.
            self._parse_left_assignee(parents[1].x, int(offset))
            return self._get_member(int(offset), cexpr, obj, self._deref_tinfo(default_tinfo))
        if int(cexpr.op) in (int(idaapi.cot_idx), int(idaapi.cot_ptr)) and is_legal_type(cexpr.type):
            # cexpr is itself a deref/index expression consumed by the caller
            # (e.g. `a1[0]` feeding arithmetic) — its own type is the observed
            # copy width, stronger than the pointer-sized PX_WORD guess.
            return self._get_member(int(offset), cexpr, obj, cexpr.type)
        # Pure value use of the scanned object (comparisons, arithmetic on the
        # pointer itself) carries no member evidence — TRex records it as an
        # operation on the pointer's type, not as a field observation.
        return None

    @staticmethod
    def _wider_tinfo(base: Any, refine: Any) -> Any:
        """Return the wider of two tinfos.

        TRex COPY_SIZES union: when a load/store of width ``base`` feeds a
        narrower value context ``refine`` (truncating cast, assignment,
        call argument), the member must keep the observed access width —
        the narrowing op happened after the memory access. Ties and any API
        error prefer ``refine`` (the more specific context).
        """
        if base is None:
            return refine
        if refine is None:
            return base
        try:
            base_size = int(base.get_size())
            refine_size = int(refine.get_size())
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return refine
        return base if base_size > refine_size else refine

    def _asm_narrowed_tinfo(self, tinfo: Any, deref_expr: Any) -> Any:
        """Narrow a deref-derived tinfo to the machine instruction's width.

        TRex §3.3.1: disassembly observes the actual copy width; Hex-Rays
        can re-type it (``mov eax, [rcx]`` is a 4-byte copy even when the
        ctree deref feeds a 64-bit expression). Only narrows integral
        types — pointers, floats and UDTs are kept as the ctree derived
        them, and any decode failure keeps the ctree width.
        """
        try:
            if tinfo is None or not bool(tinfo.is_integral()):
                return tinfo
            ea = int(deref_expr.ea)
            if ea == int(idaapi.BADADDR):
                ea = int(find_asm_address(deref_expr, self.parents))
            mem_size = get_insn_mem_size(ea)
            if mem_size is None:
                return tinfo
            size = int(tinfo.get_size())
            if size <= mem_size or mem_size not in (1, 2, 4, 8, 16):
                return tinfo
            btf_name = {1: "BTF_BYTE", 2: "BTF_WORD", 4: "BTF_DWORD", 8: "BTF_QWORD"}.get(
                mem_size
            )
            btf = getattr(idaapi, btf_name, None) if btf_name is not None else None
            if not isinstance(btf, int):
                return tinfo
            narrowed = idaapi.tinfo_t(int(btf))
            if int(narrowed.get_size()) == mem_size:
                logger.debug(
                    "  asm-narrowed deref %s -> %s (%d-byte access at %s)",
                    str(tinfo),
                    str(narrowed.dstr()),
                    mem_size,
                    to_hex(ea),
                )
                return narrowed
            return tinfo
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return tinfo

    @staticmethod
    def _extract_obj_ea(cexpr: Any) -> int | None:
        """Return the obj_ea of ``cexpr``, stripping an outer ``cot_ref``.

        Used by ``*(TYPE *)(var + x) = some_global`` — the global's EA is the
        candidate for vtable / function-ptr detection.
        """
        if cexpr is None:
            return None
        if int(cexpr.op) == int(idaapi.cot_ref):
            cexpr = cexpr.x
        if int(cexpr.op) == int(idaapi.cot_obj):
            ea = int(cexpr.obj_ea)
            if ea != int(idaapi.BADADDR):
                return ea
        return None

    def _deref_tinfo(self, tinfo: Any) -> Any:
        """Strip one pointer level. ``char*`` → ``char``; 1-byte ``void*`` → ``None``.

        The original mutates ``tinfo`` via :meth:`clr_const` elsewhere; this
        helper is pure (returns a fresh tinfo or ``None``).
        """
        if tinfo is None:
            return None
        if not tinfo.is_ptr():
            return tinfo
        if int(tinfo.get_ptrarr_objsize()) == 1:
            # 1-byte pointer → either char* (special) or void* (becomes VoidMember)
            if self._consts is not None and (
                tinfo.equals_to(self._consts.pchar_tinfo)
                or tinfo.equals_to(self._consts.const_pchar_tinfo)
            ):
                return self._consts.char_tinfo
            return None
        return tinfo.get_pointed_object()


class NewShallowSearchVisitor(SearchVisitor, ObjectDownwardsVisitor):
    """Non-recursive scanner: only walks the current function.

    Used by :class:`~hexrays_pytools.domain.actions.scanners.ShallowScanVariable`
    (and friends) when the user only wants to see the current function's
    members without recursing into callees.
    """

    def __init__(
        self,
        cfunc: Any,
        origin: int,
        obj: Any,
        workspace: ReconWorkspace,
        consts: Consts | None = None,
    ) -> None:
        super().__init__(cfunc, origin, obj, workspace, consts)


class NewDeepSearchVisitor(SearchVisitor, RecursiveObjectDownwardsVisitor):
    """Recursive scanner: also walks into callees.

    Used by :class:`~hexrays_pytools.domain.actions.scanners.DeepScanVariable`
    / ``DeepScanFunctions`` — the recursive machinery lives in
    :class:`RecursiveObjectDownwardsVisitor` (see ``visitor_base.py``).
    """

    def __init__(
        self,
        cfunc: Any,
        origin: int,
        obj: Any,
        workspace: ReconWorkspace,
        consts: Consts | None = None,
    ) -> None:
        super().__init__(cfunc, origin, obj, workspace, consts)


class DeepReturnVisitor(NewDeepSearchVisitor):
    """Recursive + caller-driven scanner.

    After the forward scan completes, walk every caller of the current
    function and re-scan with the return value as the seed. The original
    uses this for ``DeepScanReturn`` — to discover how the returned pointer
    is used by callers.
    """

    def __init__(
        self,
        cfunc: Any,
        origin: int,
        obj: Any,
        workspace: ReconWorkspace,
        consts: Consts | None = None,
    ) -> None:
        super().__init__(cfunc, origin, obj, workspace, consts)
        self._callers_ea: set[int] = get_funcs_calling_address(int(cfunc.entry_ea))
        self._call_obj = obj

    def _start(self) -> None:
        for ea in self._callers_ea:
            self._add_scan_tree_info(int(ea), -1)
        assert self._prepare_scanner()

    def _finish(self) -> None:
        if self._prepare_scanner():
            self._recursive_process()

    def _prepare_scanner(self) -> bool:
        try:
            cfunc = next(self._iter_callers())
        except StopIteration:
            return False
        self.prepare_new_scan(cfunc, -1, self._call_obj)
        return True

    def _iter_callers(self) -> Any:
        """Yield the decompiled cfunc of every caller of our original function."""
        for ea in self._callers_ea:
            cfunc = decompile_function(int(ea))
            if cfunc is not None:
                yield cfunc
