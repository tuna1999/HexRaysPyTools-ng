"""Function type manipulation helpers.

Extracted from the original `core/helper.py`. Wraps `idaapi.func_type_data_t`
operations on function arguments, return type, and argument names.
"""
from __future__ import annotations

import idaapi  # type: ignore[import-not-found]


def get_func_argument_info(func_tinfo: idaapi.tinfo_t, arg_index: int) -> tuple[str, idaapi.tinfo_t]:
    """Get (name, type) of the function argument at `arg_index`.

    Returns ("", empty tinfo) if the argument doesn't exist.
    """
    func_data = idaapi.func_type_data_t()
    if not func_tinfo.get_func_details(func_data):
        return "", idaapi.tinfo_t()
    if arg_index >= len(func_data):
        return "", idaapi.tinfo_t()
    arg = func_data[arg_index]
    return arg.name, arg.type


def set_func_argument(func_tinfo: idaapi.tinfo_t, arg_index: int, new_type: idaapi.tinfo_t) -> bool:
    """Set the type of function argument at `arg_index` to `new_type`."""
    func_data = idaapi.func_type_data_t()
    if not func_tinfo.get_func_details(func_data):
        return False
    if arg_index >= len(func_data):
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
