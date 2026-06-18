"""Architecture abstraction: ARM thumb bit, x86/x64 pointer reading.

Replaces helper.py's `is_code_ea` and `get_ptr` from the original plugin.
Centralizes architecture-specific code so other modules don't deal with
ARM thumb bit masking or 32/64-bit pointer widths.
"""
from __future__ import annotations

import idaapi  # type: ignore[import-not-found]


def is_code_ea(ea: int) -> bool:
    """Check if `ea` points to code, handling ARM thumb bit (mask 1)."""
    return bool(idaapi.is_code(idaapi.get_full_flags(ea & ~1)))


def get_ptr(ea: int) -> int:
    """Read a pointer (4 or 8 bytes) at `ea`, stripping ARM thumb bit."""
    flags = idaapi.get_full_flags(ea & ~1)
    if idaapi.get_64bit():
        return int(idaapi.get_qword(ea & ~1)) if idaapi.is_data(flags) else int(idaapi.get_wide_dword(ea & ~1))
    return int(idaapi.get_wide_dword(ea & ~1))
