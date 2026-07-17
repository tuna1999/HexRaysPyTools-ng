"""Recast logic — change types of variables/fields/returns to match a cast or assignment.

Ported from the original `callbacks/recasts.py` (299 LOC). Two actions share
this engine:

  * **Left** (Shift+L): walk from the cursor up to the nearest assignment /
    return / call and recast the **target** side (the var being assigned, the
    function return, the argument, or a struct field) to the cast type.
  * **Right** (Shift+R): walk up to the nearest **cast** and recast the
    **source** side (the var / global / field / function-return *inside* the
    cast) to the cast type. Also detects the `func(&buf, ..., N)` idiom and
    recasts `buf` to `char[N]`.

Everything here operates on real Hex-Rays ctree objects (``cfunc_t``,
``cexpr_t``, ``ctree_item_t``) obtained from a live ``vdui_t``, so this module
is not unit-testable with mocks — it is exercised by loading the plugin in a
real IDA and right-clicking in the pseudocode view.
"""

from __future__ import annotations

import logging
from typing import Any, NamedTuple

import idaapi  # type: ignore[import-not-found]

from ..types.func_type import (
    get_call_argument_info,
    set_func_argument,
    set_func_return,
    set_funcptr_argument,
)

logger = logging.getLogger(__name__)


# --- Recast target descriptors ------------------------------------------------


class RecastLocalVariable(NamedTuple):
    recast_tinfo: Any
    local_variable: Any  # idaapi.lvar_t


class RecastGlobalVariable(NamedTuple):
    recast_tinfo: Any
    global_variable_ea: int


class RecastArgument(NamedTuple):
    recast_tinfo: Any
    arg_idx: int
    func_ea: int
    func_tinfo: Any


class RecastReturn(NamedTuple):
    recast_tinfo: Any
    func_ea: int


class RecastStructure(NamedTuple):
    recast_tinfo: Any
    structure_name: str
    field_offset: int  # bytes


RecastInfo = Any  # Union of the five NamedTuples above


# --- IDA thin wrappers --------------------------------------------------------


def decompile_function(address: int) -> Any:
    """Decompile the function at `address`, returning a cfunc_t or None.

    Catches any exception (not just ``DecompilationFailure``) so a bad
    function can't break the caller's flow — decompile is best-effort here.
    """
    try:
        cfunc = idaapi.decompile(address)
    except Exception as e:  # noqa: BLE001 — decompile is best-effort
        logger.warning("Failed to decompile function at 0x%X: %s", address, e)
        return None
    if not cfunc:
        logger.warning("Failed to decompile function at 0x%X", address)
    return cfunc


def _is_code_ea(ea: int) -> bool:
    flags = idaapi.get_full_flags(ea & ~1)  # strip ARM THUMB bit
    return bool(idaapi.is_code(flags))


# --- Extract: figure out WHAT to recast ---------------------------------------


def extract_recast_info_left(cfunc: Any, ctree_item: Any) -> RecastInfo | None:
    """Left-recast: target side of the enclosing assignment / return / call.

    Walks parents from the cursor expression until it hits ``cot_asg``,
    ``cit_return`` or ``cot_call``, then decides the recast target + type.
    Returns a Recast* namedtuple or None if nothing applicable.
    """
    if ctree_item.citype != idaapi.VDI_EXPR:
        return None

    expression = ctree_item.it.to_specific_type
    child: Any = None
    # Walk up until we reach an assignment, a return, or a call.
    while expression and expression.op not in (idaapi.cot_asg, idaapi.cit_return, idaapi.cot_call):
        child = expression.to_specific_type
        expression = cfunc.body.find_parent_of(expression)
    if not expression:
        return None

    expression = expression.to_specific_type

    # --- assignment: v = ... ; s->field = ... ; gvar = ... ---
    if expression.op == idaapi.cot_asg:
        if expression.x.opname not in ("var", "obj", "memptr", "memref"):
            return None

        right_expr = expression.y
        right_tinfo = right_expr.x.type if right_expr.op == idaapi.cot_cast else right_expr.type
        # Bail if both sides already display the same type.
        if right_tinfo.dstr() == expression.x.type.dstr():
            return None

        if expression.x.op == idaapi.cot_var:
            return RecastLocalVariable(right_tinfo, cfunc.get_lvars()[expression.x.v.idx])
        if expression.x.op == idaapi.cot_obj:
            return RecastGlobalVariable(right_tinfo, int(expression.x.obj_ea))
        if expression.x.op == idaapi.cot_memptr:
            struct_name = expression.x.x.type.get_pointed_object().dstr()
            if struct_name == "?":
                struct_name = expression.x.x.type.dstr()
            return RecastStructure(right_tinfo, struct_name, int(expression.x.m))
        # cot_memref (value-form member access)
        struct_name = expression.x.x.type.dstr()
        return RecastStructure(right_tinfo, struct_name, int(expression.x.m))

    # --- return: return (TYPE) ... ; / return ... ; ---
    if expression.op == idaapi.cit_return:
        child = child or expression.creturn.expr
        if child.op == idaapi.cot_cast:
            return RecastReturn(child.x.type, int(cfunc.entry_ea))
        func_tinfo = idaapi.tinfo_t()
        cfunc.get_func_type(func_tinfo)
        rettype = func_tinfo.get_rettype()
        # Only triggers when both are pointers to different types.
        if rettype.dstr() != child.type.dstr():
            return RecastReturn(child.type, int(cfunc.entry_ea))
        return None

    # --- call: f(..., arg, ...) ; obj->method(..., arg, ...) ---
    if expression.op == idaapi.cot_call:
        if expression.x == child:
            return None  # cursor was on the callee itself
        func_ea = int(expression.x.obj_ea)
        arg_index, param_tinfo = get_call_argument_info(expression, child)

        if expression.x.op == idaapi.cot_memptr:
            # Method call: recast the struct field holding the function ptr.
            if child.op == idaapi.cot_cast:
                arg_tinfo = child.x.type
            else:
                if param_tinfo is not None and param_tinfo.equals_to(child.type):
                    return None
                arg_tinfo = child.type
            struct_tinfo = expression.x.x.type.get_pointed_object()
            funcptr_tinfo = expression.x.type
            set_funcptr_argument(funcptr_tinfo, arg_index, arg_tinfo)
            return RecastStructure(funcptr_tinfo, struct_tinfo.dstr(), int(expression.x.m))

        # Plain function call: recast one argument.
        if child.op == idaapi.cot_ref:
            if child.x.op == idaapi.cot_memref and child.x.m == 0:
                # func(..., &struct.field_0, ...)
                arg_tinfo = idaapi.tinfo_t()
                arg_tinfo.create_ptr(child.x.x.type)
            elif child.x.op == idaapi.cot_memptr and child.x.m == 0:
                # func(..., &struct->field_0, ...)
                arg_tinfo = child.x.x.type
            else:
                arg_tinfo = child.type
        elif child.op == idaapi.cot_cast:
            arg_tinfo = child.x.type
        else:
            arg_tinfo = child.type

        func_tinfo = expression.x.type.get_pointed_object()
        return RecastArgument(arg_tinfo, arg_index, func_ea, func_tinfo)

    return None


def _check_potential_array(cfunc: Any, expr: Any) -> RecastLocalVariable | None:
    """Detect `call(..., &buffer, ..., number)` and recast buffer to char[N]."""
    if expr.op != idaapi.cot_var:
        return None

    var_expr = expr.to_specific_type
    parent = cfunc.body.find_parent_of(expr)
    if parent is None or parent.op != idaapi.cot_ref:
        return None

    parent = cfunc.body.find_parent_of(parent)
    if parent is None or parent.op != idaapi.cot_call:
        return None

    call_expr = parent.to_specific_type
    for arg_expr in call_expr.a:
        if arg_expr.op == idaapi.cot_num:
            number = arg_expr.numval()
            if number:
                variable = cfunc.lvars[var_expr.v.idx]
                char_array_tinfo = idaapi.tinfo_t()
                char_array_tinfo.create_array(idaapi.tinfo_t(idaapi.BTF_CHAR), int(number))
                return RecastLocalVariable(char_array_tinfo, variable)
    return None


def extract_recast_info_right(cfunc: Any, ctree_item: Any) -> RecastInfo | None:
    """Right-recast: source side of the enclosing cast.

    Walks parents from the cursor to the nearest ``cot_cast`` and recasts the
    var/global/return/field *inside* the cast. Also tries the array shortcut.
    """
    if ctree_item.citype != idaapi.VDI_EXPR:
        return None

    expression = ctree_item.it
    result = _check_potential_array(cfunc, expression)
    if result:
        return result

    # Walk up until we reach a cast.
    while expression and expression.op != idaapi.cot_cast:
        expression = expression.to_specific_type
        expression = cfunc.body.find_parent_of(expression)
    if not expression:
        return None

    expression = expression.to_specific_type

    # (TYPE) &something ; or (TYPE) something ;
    if expression.x.op == idaapi.cot_ref:
        tinfo = expression.type.get_pointed_object()
        expression = expression.x
    else:
        tinfo = expression.type

    if expression.x.op == idaapi.cot_var:
        # (TYPE) var;
        variable = cfunc.get_lvars()[expression.x.v.idx]
        return RecastLocalVariable(tinfo, variable)

    if expression.x.op == idaapi.cot_obj:
        # (TYPE) g_var; — also (FUNCPTR) sub_XXXX → set the function type.
        if _is_code_ea(int(expression.x.obj_ea)) and tinfo.is_funcptr():
            tinfo = tinfo.get_pointed_object()
        return RecastGlobalVariable(tinfo, int(expression.x.obj_ea))

    if expression.x.op == idaapi.cot_call:
        # (TYPE) call();
        func_ea = int(expression.x.x.obj_ea)
        return RecastReturn(tinfo, func_ea)

    if expression.x.op == idaapi.cot_memptr:
        # (TYPE) var->member;
        struct_name = expression.x.x.type.get_pointed_object().dstr()
        return RecastStructure(tinfo, struct_name, int(expression.x.m))

    return None


# --- Apply: perform the recast on a live pseudocode view ----------------------


def apply_recast(hx_view: Any, ri: RecastInfo) -> bool:
    """Apply a recast descriptor to the decompiler view. Returns True if applied."""
    if isinstance(ri, RecastLocalVariable):
        hx_view.set_lvar_type(ri.local_variable, ri.recast_tinfo)

    elif isinstance(ri, RecastGlobalVariable):
        idaapi.apply_tinfo(ri.global_variable_ea, ri.recast_tinfo, idaapi.TINFO_DEFINITE)

    elif isinstance(ri, RecastArgument):
        recast = ri.recast_tinfo
        if recast.is_array():
            recast.convert_array_to_ptr()
        set_func_argument(ri.func_tinfo, ri.arg_idx, recast)
        idaapi.apply_tinfo(ri.func_ea, ri.func_tinfo, idaapi.TINFO_DEFINITE)

    elif isinstance(ri, RecastReturn):
        cfunc = decompile_function(ri.func_ea)
        if not cfunc:
            return False
        func_tinfo = idaapi.tinfo_t()
        cfunc.get_func_type(func_tinfo)
        set_func_return(func_tinfo, ri.recast_tinfo)
        idaapi.apply_tinfo(int(cfunc.entry_ea), func_tinfo, idaapi.TINFO_DEFINITE)

    elif isinstance(ri, RecastStructure):
        tinfo = idaapi.tinfo_t()
        tinfo.get_named_type(idaapi.get_idati(), ri.structure_name)
        ordinal = int(idaapi.get_type_ordinal(idaapi.get_idati(), ri.structure_name))
        if ordinal == 0:
            return False

        udt_member = idaapi.udt_member_t()
        udt_member.offset = ri.field_offset * 8  # bytes → bits
        idx = tinfo.find_udt_member(udt_member, idaapi.STRMEM_OFFSET)
        if udt_member.offset != ri.field_offset * 8:
            logger.info("Can't handle with arrays yet")
            return False
        if udt_member.type.get_size() != ri.recast_tinfo.get_size():
            logger.info("Can't recast different sizes yet")
            return False
        udt_data = idaapi.udt_type_data_t()
        tinfo.get_udt_details(udt_data)
        udt_data[idx].type = ri.recast_tinfo
        tinfo.create_udt(udt_data, idaapi.BTF_STRUCT)
        tinfo.set_numbered_type(idaapi.get_idati(), ordinal, idaapi.NTF_REPLACE, ri.structure_name)
    else:
        logger.warning("Unknown recast descriptor: %r", type(ri))
        return False

    hx_view.refresh_view(True)
    return True


# --- Label: build the menu label for a recast descriptor ----------------------


def recast_label(ri: RecastInfo) -> str:
    """Build the human-readable menu label for a recast descriptor."""
    if isinstance(ri, RecastLocalVariable):
        return f'Recast Variable "{ri.local_variable.name}" to {ri.recast_tinfo.dstr()}'
    if isinstance(ri, RecastGlobalVariable):
        gvar_name = idaapi.get_name(ri.global_variable_ea)
        return f'Recast Global Variable "{gvar_name}" to {ri.recast_tinfo.dstr()}'
    if isinstance(ri, RecastArgument):
        return "Recast Argument"
    if isinstance(ri, RecastStructure):
        return f"Recast Field of {ri.structure_name} structure"
    if isinstance(ri, RecastReturn):
        # FIX B9 (original bug): missing {} placeholder dropped the type name.
        return f"Recast Return to {ri.recast_tinfo.dstr()}"
    return "Recast Item"
