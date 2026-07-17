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
        logger.debug(
            "  created member offset=%d tinfo=%s scanned=%s",
            int(member.offset),
            str(member.tinfo),
            str(member.scanned_variables),
        )
        model = self._workspace.model
        if model is not None:
            model.add_row(member)

    # --- Member construction ------------------------------------------------

    def _get_member(
        self,
        offset: int,
        cexpr: Any,
        obj: Any,
        tinfo: Any = None,
        obj_ea: Any = None,
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
                return Member(offset=int(offset), tinfo=tinfo, origin=self._origin)

        if (
            tinfo is None
            or (self._void_tinfo is not None and tinfo.equals_to(self._void_tinfo))
            or (self._const_void_tinfo is not None and tinfo.equals_to(self._const_void_tinfo))
        ):
            logger.debug("    _get_member off=%d -> VoidMember", int(offset))
            return VoidMember(offset=int(offset), origin=self._origin)

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
        return Member(offset=int(offset), tinfo=tinfo, origin=self._origin)

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
                # Dynamic offset — can't reason about it.
                logger.debug("  ptr: skip '%s' (dynamic %s offset)", str(obj.name), parents_type[0])
                return None
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
            if len(parents_type) >= 2 and parents_type[1] == "cast":
                default_tinfo = parents[1].type
                cexpr = parents[0]
                del parents_type[0]
                del parents[0]
            else:
                default_tinfo = self._deref_tinfo(default_tinfo)

            if len(parents_type) >= 2 and parents_type[1] == "asg":
                if parents[1].x == parents[0]:
                    # *(TYPE *)(var + x) = ???
                    obj_ea = self._extract_obj_ea(parents[1].y)
                    return self._get_member(int(offset), cexpr, obj, parents[1].y.type, obj_ea)
                return self._get_member(int(offset), cexpr, obj, parents[1].x.type)
            if len(parents_type) >= 2 and parents_type[1] == "call":
                if parents[1].x == parents[0]:
                    # ((type (__some_call *)(..., ..., ...))(var[idx]))(...)
                    return self._get_member(int(offset), cexpr, obj, parents[0].type)
                _idx, tinfo = get_call_argument_info(parents[1], parents[0])
                if tinfo is None:
                    tinfo = self._pchar_tinfo
                return self._get_member(int(offset), cexpr, obj, tinfo)
            return self._get_member(int(offset), cexpr, obj, default_tinfo)

        if len(parents_type) >= 1 and parents_type[0] == "call":
            # call(..., (TYPE)(var + x), ...)
            tinfo = self._parse_call(parents[0], cexpr, int(offset))
            return self._get_member(int(offset), cexpr, obj, tinfo)

        if len(parents_type) >= 1 and parents_type[0] == "asg" and parents[0].y == cexpr:
            # other_obj = (TYPE) (var + offset)
            self._parse_left_assignee(parents[1].x, int(offset))
        return self._get_member(int(offset), cexpr, obj, self._deref_tinfo(default_tinfo))

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
