r"""CONTAINING_RECORD logic — detect/select/reset containing-structure patterns.

Ported from the original `callbacks/negative_offsets.py` (385 LOC). When a
structure pointer is accessed *outside* its boundaries (negative or
past-the-end offset), the plugin offers to treat it as a field of an outer
``CONTAINING_RECORD``. The selection is stored as a magic ``\`\`name+offset\`\```
comment on the local variable; on re-decompile the ``PotentialNegativeCollector``
rewrites matching accesses into ``CONTAINING_RECORD(addr, TYPE, FIELD)``.

Everything operates on live Hex-Rays ctree objects, so this module is not
unit-testable with mocks.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import idaapi  # type: ignore[import-not-found]

from ..chooser import MyChoose
from ..til.type_library import choose_til, import_type

logger = logging.getLogger(__name__)

# Potential-negative candidates live in Session.potential_negatives (keyed by
# cfunc entry ea so two open views don't collide); the hxe_maturity/CMAT_BUILT
# collector populates them and the Select action consumes them. The functions
# below take the store dict as a parameter — no module-global mutable state.


# --- Magic comment helpers ----------------------------------------------------


def _my_cexpr_t(*args: Any, **kwargs: Any) -> Any:
    """Build a cexpr_t — replacement for the bugged ``cexpr_t(op, x=..)`` ctor.

    The SWIG constructor accepts neither keywords nor (op, x) positionally;
    ported from v1.x ``core/helper.py:my_cexpr_t``. Builds a no-arg cexpr_t
    and fills op/x/y/z through the documented _set_* setters.
    """
    if len(args) == 0:
        return idaapi.cexpr_t()

    if len(args) != 1:
        raise NotImplementedError("my_cexpr_t takes at most one positional arg")

    cexpr = idaapi.cexpr_t()
    cexpr.thisown = False
    if isinstance(args[0], idaapi.cexpr_t):
        cexpr.assign(args[0])
    else:
        cexpr._set_op(args[0])
        if "x" in kwargs:
            cexpr._set_x(kwargs["x"])
        if "y" in kwargs:
            cexpr._set_y(kwargs["y"])
        if "z" in kwargs:
            cexpr._set_z(kwargs["z"])
    return cexpr


def _has_magic_comment(lvar: Any) -> bool:
    """Return True if the lvar carries a CONTAINING_RECORD magic comment."""
    return bool(re.search(r"```.*```", lvar.cmt))


def _parse_magic_comment(lvar: Any) -> Any:
    r"""Parse a ``\`\`StructName+offset\`\``` comment into a NegativeLocalInfo."""
    if not lvar.type().is_ptr():
        return None
    m = re.search(r"```(.+)```", lvar.cmt)
    if not m:
        return None
    try:
        structure_name, offset_str = m.group(1).split("+")
        offset = int(offset_str)
    except ValueError:
        return None
    parent_tinfo = idaapi.tinfo_t()
    if not parent_tinfo.get_named_type(idaapi.get_idati(), structure_name):
        return None
    if parent_tinfo.get_size() <= offset:
        return None
    members = dict(find_deep_members(parent_tinfo, lvar.type().get_pointed_object()))
    member_name = members.get(offset)
    if member_name:
        return NegativeLocalInfo(
            lvar.type().get_pointed_object(), parent_tinfo, offset, member_name
        )
    return None


def find_deep_members(parent_tinfo: Any, target_tinfo: Any) -> list[tuple[int, str]]:
    """Return all (byte_offset, qualified_member_name) where parent embeds target."""
    udt_data = idaapi.udt_type_data_t()
    parent_tinfo.get_udt_details(udt_data)
    result: list[tuple[int, str]] = []
    for udt_member in udt_data:
        if udt_member.type.equals_to(target_tinfo):
            result.append((int(udt_member.offset) // 8, udt_member.name))
        elif udt_member.type.is_udt():
            for offset, name in find_deep_members(udt_member.type, target_tinfo):
                qualified = udt_member.name + "." + name if udt_member.name else name
                result.append((int(udt_member.offset) // 8 + offset, qualified))
    return result


# --- Descriptors --------------------------------------------------------------


class NegativeLocalInfo:
    """A resolved CONTAINING_RECORD: the embedded type, parent, offset, member."""

    def __init__(self, tinfo: Any, parent_tinfo: Any, offset: int, member_name: str) -> None:
        self.tinfo = tinfo
        self.size = int(tinfo.get_size()) if tinfo.is_udt() else 0
        self.parent_tinfo = parent_tinfo
        self.offset = offset
        self.member_name = member_name

    def __repr__(self) -> str:
        return f"Type - {self.tinfo.dstr()}, parent type - {self.parent_tinfo.dstr()}, offset - {self.offset}, member_name - {self.member_name}"


class NegativeLocalCandidate:
    """A struct-pointer lvar with accesses beyond its bounds — a candidate."""

    def __init__(self, tinfo: Any, offset: int) -> None:
        self.tinfo = tinfo
        self.offsets = [offset]

    def __repr__(self) -> str:
        return str(self.tinfo.dstr()) + " " + str(self.offsets)

    def is_structure_offset(self, tinfo: Any, offset: int) -> bool:
        """Return True if `tinfo` has a member at byte `offset`."""
        udt_member = idaapi.udt_member_t()
        udt_member.offset = offset * 8
        if offset >= 0 and tinfo.find_udt_member(udt_member, idaapi.STRMEM_OFFSET) != -1:
            if udt_member.type.is_udt():
                return self.is_structure_offset(
                    udt_member.type, offset - int(udt_member.offset) // 8
                )
            return int(udt_member.offset) == offset * 8
        return False

    def find_containing_structures(self, type_library: Any) -> list[tuple[int, int, str, str]]:
        """Find library structs that embed this struct at a viable offset.

        Returns list of (ordinal, offset, member_name, parent_struct_name).
        """
        min_offset = min(self.offsets)
        min_offset = min_offset if min_offset < 0 else 0
        max_offset = max(self.offsets)
        max_offset = max_offset if max_offset > 0 else int(self.tinfo.get_size())
        min_struct_size = max_offset - min_offset
        result: list[tuple[int, int, str, str]] = []
        target_tinfo = idaapi.tinfo_t()
        if not target_tinfo.get_named_type(type_library, self.tinfo.dstr()):
            logger.warning("Type '%s' not in library '%s'", self.tinfo.dstr(), type_library.name)
            return result
        for ordinal in range(1, int(idaapi.get_ordinal_count(type_library))):
            parent_tinfo = idaapi.tinfo_t()
            parent_tinfo.create_typedef(type_library, ordinal)
            if parent_tinfo.get_size() >= min_struct_size:
                for offset, name in find_deep_members(parent_tinfo, target_tinfo):
                    if offset + min_offset >= 0 and offset + max_offset <= parent_tinfo.get_size():
                        result.append((ordinal, offset, name, parent_tinfo.dstr()))
        return result


# --- ctree visitors -----------------------------------------------------------


def _make_num(value: int) -> Any:
    number = idaapi.make_num(value)
    number.thisown = False
    return number


def _helper_expr(tinfo: Any, text: str) -> Any:
    cexpr = idaapi.create_helper(True, tinfo, text)
    out = idaapi.carg_t()
    out.assign(cexpr)
    return out


class ReplaceVisitor(idaapi.ctree_parentee_t):  # type: ignore[misc]
    """Rewrite out-of-bounds struct accesses as CONTAINING_RECORD macros."""

    def __init__(self, negative_lvars: dict[int, Any]) -> None:
        super().__init__()
        self.negative_lvars = negative_lvars
        self.pvoid_tinfo = idaapi.tinfo_t(idaapi.BT_VOID)
        self.pvoid_tinfo.create_ptr(self.pvoid_tinfo)

    def visit_expr(self, expression: Any) -> int:
        if (
            expression.op == idaapi.cot_add
            and expression.x.op == idaapi.cot_var
            and expression.y.op == idaapi.cot_num
        ):
            idx = expression.x.v.idx
            if idx in self.negative_lvars:
                offset = expression.y.numval()
                if offset >= self.negative_lvars[idx].size:
                    self._create_containing_record(expression, idx, offset)
        elif (
            expression.op == idaapi.cot_sub
            and expression.x.op == idaapi.cot_var
            and expression.y.op == idaapi.cot_num
        ):
            idx = expression.x.v.idx
            if idx in self.negative_lvars:
                offset = -int(expression.y.n.value(idaapi.tinfo_t(idaapi.BT_INT)))
                self._create_containing_record(expression, idx, offset)
        return 0

    def _create_containing_record(self, expression: Any, idx: int, offset: int) -> None:
        negative_lvar = self.negative_lvars[idx]
        logger.debug(
            "Creating CONTAINING_RECORD: offset=%s negative_offset=%s TYPE=%s",
            negative_lvar.offset,
            offset,
            negative_lvar.parent_tinfo.dstr(),
        )

        arg_address = idaapi.carg_t()
        if expression.op == idaapi.cot_var:
            arg_address.assign(expression)
        else:
            arg_address.assign(expression.x)

        arg_type = _helper_expr(self.pvoid_tinfo, negative_lvar.parent_tinfo.dstr())
        arg_field = _helper_expr(self.pvoid_tinfo, negative_lvar.member_name)

        return_tinfo = idaapi.tinfo_t(negative_lvar.parent_tinfo)
        return_tinfo.create_ptr(return_tinfo)
        new_call = idaapi.call_helper(return_tinfo, None, "CONTAINING_RECORD")
        new_call.a.push_back(arg_address)
        new_call.a.push_back(arg_type)
        new_call.a.push_back(arg_field)
        new_call.thisown = False

        parent = next(reversed(self.parents)).cexpr
        diff = negative_lvar.offset + offset

        def _wrap_in_cast(inner: Any) -> None:
            tmp_tinfo = idaapi.tinfo_t()
            tmp_tinfo.create_ptr(parent.type)
            new_cast = _my_cexpr_t(idaapi.cot_cast, x=inner)
            new_cast.thisown = False
            new_cast.type = tmp_tinfo
            expression.assign(new_cast)

        if diff:
            number = _make_num(diff)
            new_add = _my_cexpr_t(idaapi.cot_add, x=new_call, y=number)
            new_add.type = return_tinfo
            if parent.op == idaapi.cot_ptr:
                _wrap_in_cast(new_add)
            else:
                expression.assign(new_add)
        else:
            if parent.op == idaapi.cot_ptr:
                _wrap_in_cast(new_call)
            else:
                expression.assign(new_call)


class SearchVisitor(idaapi.ctree_parentee_t):  # type: ignore[misc]
    """Find existing CONTAINING_RECORD macros in a cfunc."""

    def __init__(self, cfunc: Any) -> None:
        super().__init__()
        self.cfunc = cfunc
        self.result: dict[int, Any] = {}

    def visit_expr(self, expression: Any) -> int:
        if (
            expression.op == idaapi.cot_call
            and expression.x.op == idaapi.cot_helper
            and len(expression.a) == 3
            and expression.x.helper == "CONTAINING_RECORD"
            and expression.a[0].op == idaapi.cot_var
        ):
            idx = expression.a[0].v.idx
            if expression.a[1].op == idaapi.cot_helper and expression.a[2].op == idaapi.cot_helper:
                parent_name = expression.a[1].helper
                member_name = expression.a[2].helper
                parent_tinfo = idaapi.tinfo_t()
                if not parent_tinfo.get_named_type(idaapi.get_idati(), parent_name):
                    return 0
                udt_data = idaapi.udt_type_data_t()
                parent_tinfo.get_udt_details(udt_data)
                matches = [x for x in udt_data if x.name == member_name]
                if matches:
                    tinfo = matches[0].type
                    self.result[idx] = NegativeLocalInfo(
                        tinfo,
                        parent_tinfo,
                        int(matches[0].offset) // 8,
                        member_name,
                    )
                    return 1
        return 0


class AnalyseVisitor(idaapi.ctree_parentee_t):  # type: ignore[misc]
    """Detect struct-pointer lvars accessed beyond their bounds."""

    def __init__(self, candidates: dict[int, Any], store: dict[int, Any]) -> None:
        super().__init__()
        self.candidates = candidates
        self.potential_negatives = store

    def visit_expr(self, expression: Any) -> int:
        if expression.op == idaapi.cot_add and expression.y.op == idaapi.cot_num:
            if expression.x.op == idaapi.cot_var and expression.x.v.idx in self.candidates:
                idx = expression.x.v.idx
                number = expression.y.numval()
                if self.candidates[idx].get_size() <= number:
                    if idx in self.potential_negatives:
                        self.potential_negatives[idx].offsets.append(number)
                    else:
                        self.potential_negatives[idx] = NegativeLocalCandidate(
                            self.candidates[idx], number
                        )
        elif (
            expression.op == idaapi.cot_sub
            and expression.y.op == idaapi.cot_num
            and expression.x.op == idaapi.cot_var
            and expression.x.v.idx in self.candidates
        ):
            idx = expression.x.v.idx
            number = -expression.y.numval()
            if idx in self.potential_negatives:
                self.potential_negatives[idx].offsets.append(number)
            else:
                self.potential_negatives[idx] = NegativeLocalCandidate(self.candidates[idx], number)
        return 0


# --- The hxe_maturity collector (CMAT_BUILT) ----------------------------------


def collect_potential_negatives(cfunc: Any, potential_negatives: dict[int, dict[int, Any]]) -> None:
    """Run at CMAT_BUILT: find + apply CONTAINING_RECORD patterns.

    Mirrors the original PotentialNegativeCollector handler:
      1. search for existing CONTAINING_RECORD macros
      2. parse magic comments on lvars
      3. analyse struct-pointer accesses for out-of-bounds candidates
      4. rewrite resolved negatives as CONTAINING_RECORD

    ``potential_negatives`` is the Session-owned store (entry_ea -> candidates)
    updated in place.
    """
    entry_ea = int(cfunc.entry_ea)
    # Step 1: existing CONTAINING_RECORD macros
    searcher = SearchVisitor(cfunc)
    searcher.apply_to(cfunc.body, None)
    negative_lvars: dict[int, Any] = dict(searcher.result)

    # Step 2: magic comments
    lvars = cfunc.get_lvars()
    for idx in range(len(lvars)):
        parsed = _parse_magic_comment(lvars[idx])
        if parsed and parsed.tinfo.equals_to(lvars[idx].type().get_pointed_object()):
            negative_lvars[idx] = parsed

    # Step 3: detect potential negatives among the remaining struct pointers
    store: dict[int, Any] = {}
    potential_negatives[entry_ea] = store
    structure_pointers: dict[int, Any] = {}
    for idx in set(range(len(lvars))) - set(negative_lvars.keys()):
        if lvars[idx].type().is_ptr():
            pointed = lvars[idx].type().get_pointed_object()
            if pointed.is_udt():
                structure_pointers[idx] = pointed
    if structure_pointers:
        analyser = AnalyseVisitor(structure_pointers, store)
        analyser.apply_to(cfunc.body, None)

    # Step 4: rewrite resolved negatives
    if negative_lvars:
        replacer = ReplaceVisitor(negative_lvars)
        replacer.apply_to(cfunc.body, None)


# --- Action helpers (Select / Reset) ------------------------------------------


def can_select_containing(hx_view: Any, potential_negatives: dict[int, dict[int, Any]]) -> bool:
    """True when the cursor is on a struct-pointer lvar that's a candidate."""
    if hx_view is None:
        return False
    item = hx_view.item
    if item.citype != idaapi.VDI_EXPR or item.e.op != idaapi.cot_var:
        return False
    entry_ea = int(hx_view.cfunc.entry_ea)
    return item.e.v.idx in potential_negatives.get(entry_ea, {})


def can_reset_containing(hx_view: Any) -> bool:
    """True when the cursor is on an lvar that has a magic comment."""
    if hx_view is None:
        return False
    item = hx_view.item
    if item.citype != idaapi.VDI_EXPR or item.e.op != idaapi.cot_var:
        return False
    lvars = hx_view.cfunc.get_lvars()
    return _has_magic_comment(lvars[item.e.v.idx])


def select_containing_structure(
    hx_view: Any, potential_negatives: dict[int, dict[int, Any]]
) -> bool:
    """Prompt for a containing struct, write its magic comment on the lvar."""
    if hx_view is None:
        return False
    result = choose_til()
    if not result:
        return False
    selected_library, _max_ord, is_local_types = result
    lvar_idx = hx_view.item.e.v.idx
    entry_ea = int(hx_view.cfunc.entry_ea)
    candidate = potential_negatives.get(entry_ea, {}).get(lvar_idx)
    if candidate is None:
        return False
    structures = candidate.find_containing_structures(selected_library)
    items = [[str(x[0]), f"0x{x[1]:08X}", x[2], x[3]] for x in structures]
    chooser = MyChoose(
        items,
        "Select Containing Structure",
        [["Ordinal", 5], ["Offset", 10], ["Member_name", 20], ["Structure Name", 20]],
        165,
    )
    selected_idx = chooser.Show(modal=True)
    if selected_idx == -1:
        return False
    if not is_local_types:
        import_type(selected_library, items[selected_idx][3])
    lvar = hx_view.cfunc.get_lvars()[lvar_idx]
    lvar_cmt = re.sub(r"```.*```", "", lvar.cmt)
    hx_view.set_lvar_cmt(
        lvar,
        lvar_cmt + f"```{structures[selected_idx][3]}+{structures[selected_idx][1]}```",
    )
    hx_view.refresh_view(True)
    return True


def reset_containing_structure(hx_view: Any) -> bool:
    """Remove the CONTAINING_RECORD magic comment from the lvar."""
    if hx_view is None:
        return False
    lvar = hx_view.cfunc.get_lvars()[hx_view.item.e.v.idx]
    hx_view.set_lvar_cmt(lvar, re.sub(r"```.*```", "", lvar.cmt))
    hx_view.refresh_view(True)
    return True
