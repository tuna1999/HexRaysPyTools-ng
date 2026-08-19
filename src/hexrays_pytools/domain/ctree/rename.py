"""Rename logic — 6 rename operations.

Ported from the original `callbacks/renames.py` (407 LOC). Five of the six
operations are self-contained and ported here; ``PropagateName`` needs the
``RecursiveObjectDownwardsVisitor`` scanner engine (``api.py``) and is
wired once that engine lands.

Everything here operates on real Hex-Rays ctree objects obtained from a live
``vdui_t``, so this module is not unit-testable with mocks.
"""

from __future__ import annotations

import logging
import re
from typing import Any, NamedTuple

import idaapi  # type: ignore[import-not-found]
import idc  # type: ignore[import-not-found]

from ...infra.arch.arch import to_hex
from ..scanner.ctree_utils import find_asm_address
from ..types.func_type import get_call_argument_info, set_func_arg_name
from ..types.tinfo_utils import change_member_name

logger = logging.getLogger(__name__)


# --- Pure helpers (testable) --------------------------------------------------


def _is_default_name(string: str) -> bool:
    """Return True for IDA's auto-generated names (v1, a2, field_, ...)."""
    return (
        re.match(r"[av]\d+$", string) is not None
        or re.match(r"[qd]?word|field_|off_", string) is not None
    )


def _should_be_renamed(old_name: str, new_name: str) -> bool:
    """Return True if renaming `old_name` to `new_name` is worthwhile."""
    if _is_default_name(new_name):
        return False
    return old_name.lstrip("_") != new_name.lstrip("_")


# --- Rename descriptors -------------------------------------------------------


class RenameOtherInfo(NamedTuple):
    lvar: Any  # idaapi.lvar_t to rename
    name: str  # new name


class RenameInsideInfo(NamedTuple):
    func_tinfo: Any
    func_ea: int
    arg_idx: int
    name: str


class MemberFromFuncInfo(NamedTuple):
    struct_name: str
    offset: int  # bytes
    name: str


# --- RenameOther: take the other side's name in `a = b` -----------------------


def extract_rename_other_info(cfunc: Any, ctree_item: Any) -> RenameOtherInfo | None:
    """`a = b` → rename `a` to `b`'s name."""
    if ctree_item.citype != idaapi.VDI_EXPR:
        return None
    expression = ctree_item.it.to_specific_type
    if expression.op != idaapi.cot_var:
        return None
    parent = cfunc.body.find_parent_of(expression).to_specific_type
    if parent.op != idaapi.cot_asg:
        return None
    other = parent.theother(expression)
    if other.op != idaapi.cot_var:
        return None
    this_lvar = ctree_item.get_lvar()
    other_lvar = cfunc.get_lvars()[other.v.idx]
    if _should_be_renamed(this_lvar.name, other_lvar.name):
        return RenameOtherInfo(this_lvar, other_lvar.name.lstrip("_"))
    return None


def rename_other(hx_view: Any, info: RenameOtherInfo) -> None:
    """Rename the lvar, prefixing with `_` until the rename succeeds."""
    name = info.name
    while not hx_view.rename_lvar(info.lvar, name, True):
        name = "_" + name


# --- RenameInside: push var name into the called function's parameter --------


def extract_rename_inside_info(cfunc: Any, ctree_item: Any) -> RenameInsideInfo | None:
    """`func(var)` → set func's parameter name to var's name."""
    if ctree_item.citype != idaapi.VDI_EXPR:
        return None
    expression = ctree_item.it.to_specific_type
    if expression.op != idaapi.cot_var:
        return None
    parent = cfunc.body.find_parent_of(expression).to_specific_type
    if parent.op != idaapi.cot_call or parent.x.obj_ea == idaapi.BADADDR:
        return None
    lvar = ctree_item.get_lvar()
    arg_index, _ = get_call_argument_info(parent, expression)
    func_tinfo = parent.x.type.get_pointed_object()
    from ..types.func_type import get_func_arg_name

    arg_name = get_func_arg_name(func_tinfo, arg_index)
    if arg_name is not None and _should_be_renamed(arg_name, lvar.name):
        return RenameInsideInfo(func_tinfo, int(parent.x.obj_ea), arg_index, lvar.name.lstrip("_"))
    return None


def rename_inside(hx_view: Any, info: RenameInsideInfo) -> None:
    """Set the arg name on the function type and apply it."""
    set_func_arg_name(info.func_tinfo, info.arg_idx, info.name)
    idaapi.apply_tinfo(info.func_ea, info.func_tinfo, idaapi.TINFO_DEFINITE)
    hx_view.refresh_view(True)


# --- RenameOutside: take the called function's parameter name for a var ------


def extract_rename_outside_info(cfunc: Any, ctree_item: Any) -> RenameOtherInfo | None:
    """`func(var)` → rename `var` to func's parameter name."""
    if ctree_item.citype != idaapi.VDI_EXPR:
        return None
    expression = ctree_item.it.to_specific_type
    if expression.op != idaapi.cot_var:
        return None
    parent = cfunc.body.find_parent_of(expression).to_specific_type
    if parent.op != idaapi.cot_call or parent.x.obj_ea == idaapi.BADADDR:
        return None
    lvar = ctree_item.get_lvar()
    arg_index, _ = get_call_argument_info(parent, expression)
    func_tinfo = parent.x.type.get_pointed_object()
    from ..types.func_type import get_func_arg_name

    arg_name = get_func_arg_name(func_tinfo, arg_index)
    if arg_name and _should_be_renamed(lvar.name, arg_name):
        return RenameOtherInfo(lvar, arg_name.lstrip("_"))
    return None


# rename_outside reuses rename_other (same lvar-rename mechanics).
rename_outside = rename_other


# --- RenameMemberFromFunctionName: infer member name from getter/setter ------


def extract_member_from_func_info(cfunc: Any, ctree_item: Any) -> MemberFromFuncInfo | None:
    """`obj->member` → name the member after the enclosing function (m_xxx)."""
    if ctree_item.citype != idaapi.VDI_EXPR:
        return None
    expr = ctree_item.it.to_specific_type
    if expr.op == idaapi.cot_memptr:
        t = expr.x.type.get_pointed_object()
    elif expr.op == idaapi.cot_memref:
        t = expr.x.type
    else:
        return None

    result_name = idaapi.get_name(cfunc.entry_ea)
    if idaapi.is_valid_typename(result_name):
        return MemberFromFuncInfo(t.dstr(), int(expr.m), result_name)

    demangled = idc.demangle_name(result_name, idc.get_inf_attr(idc.INF_SHORT_DN))
    if demangled is None:
        return None
    result_name = re.sub(r"^.*:", "", demangled)
    if not result_name:
        return None
    return MemberFromFuncInfo(t.dstr(), int(expr.m), result_name)


def rename_member_from_function_name(hx_view: Any, info: MemberFromFuncInfo) -> None:
    """Rename the struct member, deriving `m_xxx` from the function name."""
    sname = re.sub(r"struct ", "", info.struct_name)
    mname = info.name
    if not re.search(r"_vtbl$", sname):
        mname = re.sub(r"^(get|set)*", "m", mname, flags=re.IGNORECASE)
    if not change_member_name(sname, info.offset, mname):
        mname = mname + "_" + format(info.offset, "x")
        change_member_name(sname, info.offset, mname)
    hx_view.refresh_view(True)


# --- RenameUsingAssert: rename callers by an assert-like string argument -----


class _RenameUsingAssertVisitor(idaapi.ctree_parentee_t):  # type: ignore[misc]
    """Walk a function, find calls to `func_addr` with a string arg, collect candidate names."""

    def __init__(self, cfunc: Any, func_addr: int, arg_idx: int) -> None:
        super().__init__()
        self._cfunc = cfunc
        self._func_addr = func_addr
        self._arg_idx = arg_idx
        self._possible_names: set[str] = set()

    def visit_expr(self, expr: Any) -> int:
        if (
            expr.op == idaapi.cot_call
            and expr.x.op == idaapi.cot_obj
            and expr.x.obj_ea == self._func_addr
        ):
            arg_expr = expr.a[self._arg_idx]
            if arg_expr.op != idaapi.cot_obj:
                cexpr_ea = find_asm_address(expr, self.parents)
                logger.error("Argument is not a string at %s", to_hex(int(cexpr_ea)))
                return 1
            self._add_func_name(arg_expr)
        return 0

    def process(self) -> None:
        self.apply_to(self._cfunc.body, None)
        if len(self._possible_names) == 1:
            new_name = self._possible_names.pop()
            logger.info(
                "Renaming function at %s to `%s`",
                to_hex(int(self._cfunc.entry_ea)),
                new_name,
            )
            idc.set_name(self._cfunc.entry_ea, new_name)
        elif len(self._possible_names) > 1:
            logger.error(
                "Function at %s has more than one candidate for renaming: %s",
                to_hex(int(self._cfunc.entry_ea)),
                ", ".join(self._possible_names),
            )

    def _add_func_name(self, arg_expr: Any) -> None:
        new_name = idc.get_strlit_contents(arg_expr.obj_ea)
        if isinstance(new_name, bytes):
            new_name = new_name.decode("ascii")
        if not idaapi.is_valid_typename(new_name):
            logger.warning(
                "Argument has a weird name `%s`",
                new_name,
            )
            return
        self._possible_names.add(new_name)


def _can_be_part_of_assert(cfunc: Any, ctree_item: Any) -> bool:
    """Return True if the cursor is on a string arg of a call (assert-like)."""
    if ctree_item.citype != idaapi.VDI_EXPR:
        return False
    expression = ctree_item.it.to_specific_type
    if expression.op != idaapi.cot_obj:
        return False
    parent = cfunc.body.find_parent_of(expression).to_specific_type
    if parent.op != idaapi.cot_call or parent.x.op != idaapi.cot_obj:
        return False
    obj_ea = int(expression.obj_ea)
    from ...infra.arch.arch import is_code_ea

    if not is_code_ea(obj_ea) and idc.get_str_type(obj_ea) == idc.STRTYPE_C:
        str_potential_name = idc.get_strlit_contents(obj_ea)
        if isinstance(str_potential_name, bytes):
            str_potential_name = str_potential_name.decode("ascii")
        return bool(idaapi.is_valid_typename(str_potential_name))
    return False


def extract_assert_info(cfunc: Any, ctree_item: Any) -> bool:
    """Check-only: returns True when the cursor is an assert-like string arg."""
    return _can_be_part_of_assert(cfunc, ctree_item)


def rename_using_assert(hx_view: Any, cfunc: Any, ctree_item: Any) -> None:
    """Find all callers of the assert function and rename each by its string arg."""
    if not _can_be_part_of_assert(cfunc, ctree_item):
        return
    expr_arg = ctree_item.it.to_specific_type
    expr_call = cfunc.body.find_parent_of(expr_arg).to_specific_type
    arg_idx, _ = get_call_argument_info(expr_call, expr_arg)
    assert_func_ea = int(expr_call.x.obj_ea)

    from ...infra.arch.arch import get_funcs_calling_address
    from .recast import decompile_function

    for caller_ea in get_funcs_calling_address(assert_func_ea):
        caller_cfunc = decompile_function(caller_ea)
        if caller_cfunc:
            _RenameUsingAssertVisitor(caller_cfunc, assert_func_ea, arg_idx).process()
    hx_view.refresh_view(True)


# PropagateName lives in ``domain/actions/rename_action.py`` because it is
# implemented directly on top of the recursive scanner visitor and needs the
# action's Session settings. The rest of the rename operations stay here.
