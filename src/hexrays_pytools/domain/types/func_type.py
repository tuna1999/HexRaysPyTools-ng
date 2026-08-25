"""Function type manipulation helpers.

Extracted from the original `core/helper.py`. Wraps `idaapi.func_type_data_t`
operations on function arguments, return type, and argument names.
"""

from __future__ import annotations

import idaapi  # type: ignore[import-not-found]


def get_arg_name_and_type(func_tinfo: idaapi.tinfo_t, arg_index: int) -> tuple[str, idaapi.tinfo_t]:
    """Get (name, type) of the function argument at `arg_index`.

    Returns ("", empty tinfo) if the argument doesn't exist.
    """
    func_data = idaapi.func_type_data_t()
    if not func_tinfo.get_func_details(func_data):
        return "", idaapi.tinfo_t()
    if arg_index < 0 or arg_index >= len(func_data):
        return "", idaapi.tinfo_t()
    arg = func_data[arg_index]
    return arg.name, arg.type


def set_func_argument(func_tinfo: idaapi.tinfo_t, arg_index: int, new_type: idaapi.tinfo_t) -> bool:
    """Set the type of function argument at `arg_index` to `new_type`."""
    func_data = idaapi.func_type_data_t()
    if not func_tinfo.get_func_details(func_data):
        return False
    if arg_index < 0 or arg_index >= len(func_data):
        return False
    func_data[arg_index].type = new_type
    return bool(func_tinfo.create_func(func_data, idaapi.BT_FUNC))


def set_func_return(func_tinfo: idaapi.tinfo_t, new_type: idaapi.tinfo_t) -> bool:
    """Set the return type of the function."""
    func_data = idaapi.func_type_data_t()
    if not func_tinfo.get_func_details(func_data):
        return False
    func_data.rettype = new_type
    return bool(func_tinfo.create_func(func_data, idaapi.BT_FUNC))


def get_call_argument_info(
    call_expr: idaapi.tinfo_t,
    child_expr: idaapi.tinfo_t,
) -> tuple[int, idaapi.tinfo_t | None]:
    """Find which argument of `call_expr` is `child_expr`.

    Returns (arg_index, declared_param_type). The param type comes from the
    callee's function type (the call's `.x.type.get_nth_arg(idx)`); None if
    the callee has no declared arg at that index.

    Mirrors the original `helper.get_func_arg_name`.
    """
    arg_index = -1
    for i, arg in enumerate(call_expr.a):
        if arg == child_expr:
            arg_index = i
            break
    if arg_index == -1:
        return -1, None
    func_tinfo = call_expr.x.type.get_pointed_object()
    nargs = func_tinfo.get_nargs() if hasattr(func_tinfo, "get_nargs") else 0
    param: idaapi.tinfo_t | None = None
    if arg_index < int(nargs):
        param = func_tinfo.get_nth_arg(arg_index)
    return arg_index, param


def set_funcptr_argument(
    funcptr_tinfo: idaapi.tinfo_t,
    index: int,
    arg_tinfo: idaapi.tinfo_t,
) -> bool:
    """Set one argument type on a function-pointer tinfo (re-wraps the ptr).

    Mirrors the original `helper.set_funcptr_argument`.
    """
    func_tinfo = funcptr_tinfo.get_pointed_object()
    if not set_func_argument(func_tinfo, index, arg_tinfo):
        return False
    return bool(funcptr_tinfo.create_ptr(func_tinfo))


def get_func_arg_name(func_tinfo: idaapi.tinfo_t, arg_idx: int) -> str | None:
    """Get the name of the function argument at `arg_idx`, or None if out of range.

    Mirrors the original `helper.get_func_arg_name`.
    """
    func_data = idaapi.func_type_data_t()
    if arg_idx < 0 or not func_tinfo.get_func_details(func_data):
        return None
    if arg_idx < int(func_tinfo.get_nargs()):
        return str(func_data[arg_idx].name)
    return None


def set_func_arg_name(func_tinfo: idaapi.tinfo_t, arg_idx: int, name: str) -> None:
    """Set the name of the function argument at `arg_idx`.

    Mirrors the original `helper.set_func_arg_name`.
    """
    func_data = idaapi.func_type_data_t()
    if arg_idx < 0 or not func_tinfo.get_func_details(func_data) or arg_idx >= len(func_data):
        return
    func_data[arg_idx].name = name
    func_tinfo.create_func(func_data)
