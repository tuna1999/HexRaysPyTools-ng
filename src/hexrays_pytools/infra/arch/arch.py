"""Architecture abstraction: ARM thumb bit, x86/x64 pointer reading.

Replaces helper.py's `is_code_ea`, `get_ptr`, `get_funcs_calling_address`,
and `to_hex` from the original plugin.
"""
from __future__ import annotations

import idaapi  # type: ignore[import-not-found]
import idc  # type: ignore[import-not-found]


def is_code_ea(ea: int) -> bool:
    """Check if `ea` points to code, handling ARM thumb bit (mask 1)."""
    return bool(idaapi.is_code(idaapi.get_full_flags(ea & ~1)))


def get_ptr(ea: int) -> int:
    """Read a pointer (4 or 8 bytes) at `ea`, stripping ARM thumb bit."""
    flags = idaapi.get_full_flags(ea & ~1)
    if idaapi.get_64bit():
        return int(idaapi.get_qword(ea & ~1)) if idaapi.is_data(flags) else int(idaapi.get_wide_dword(ea & ~1))
    return int(idaapi.get_wide_dword(ea & ~1))


def get_funcs_calling_address(ea: int) -> set[int]:
    """Return all function-start addresses that call the function at `ea`.

    Mirrors the original `helper.get_funcs_calling_address`.
    """
    xref_ea = int(idaapi.get_first_cref_to(ea))
    xrefs: set[int] = set()
    while xref_ea != idaapi.BADADDR:
        xref_func_ea = int(idc.get_func_attr(xref_ea, idc.FUNCATTR_START))
        if xref_func_ea != idaapi.BADADDR:
            xrefs.add(xref_func_ea)
        xref_ea = int(idaapi.get_next_cref_to(ea, xref_ea))
    return xrefs


def to_hex(ea: int) -> str:
    """Format `ea` as a clickable hex address for the IDA output window.

    Mirrors the original `helper.to_hex`.
    """
    if idaapi.get_64bit():
        return f"0x{ea:016X}"
    return f"0x{ea:08X}"

