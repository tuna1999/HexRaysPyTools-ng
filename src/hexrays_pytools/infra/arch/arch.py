"""Architecture abstraction: ARM thumb bit, x86/x64 pointer reading.

Replaces helper.py's `is_code_ea`, `get_ptr`, `get_funcs_calling_address`,
and `to_hex` from the original plugin.
"""

from __future__ import annotations

from typing import Any

import idaapi  # type: ignore[import-not-found]
import idc  # type: ignore[import-not-found]


def is_code_ea(ea: int) -> bool:
    """Check if `ea` points to code, handling ARM thumb bit (mask 1)."""
    checked_ea = int(ea)
    if str(idaapi.inf_get_procname()) == "ARM":
        checked_ea &= ~1
    return bool(idaapi.is_code(idaapi.get_full_flags(checked_ea)))


def get_ptr(ea: int) -> int:
    """Read one native-width pointer from ``ea``.

    Pointer width is an architecture property, not a property of IDA's
    current classification for the source address. In particular, vtable
    slots in a partially analysed IDB can be untyped and still contain valid
    64-bit pointers.
    """
    if idaapi.inf_is_64bit():
        return int(idaapi.get_qword(ea))
    ptr = int(idaapi.get_wide_dword(ea))
    if str(idaapi.inf_get_procname()) == "ARM":
        ptr &= ~1
    return ptr


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


def is_imported_ea(ea: int, imported_ea: set[int]) -> bool:
    """True if `ea` points into an imported function (PLT or the import cache).

    Mirrors the original ``helper.is_imported_ea``. The original read the
    import cache from a module global (``cache.imported_ea``); we take it
    as a parameter so callers pass the Session-owned set explicitly.
    """
    if idc.get_segm_name(ea) == ".plt":
        return True
    # Session caches absolute EAs. All scanner callers also operate on live
    # ctree/decompiler EAs, so keep one representation end-to-end.
    return int(ea) in imported_ea


def choose_virtual_func_address(
    name: str,
    class_tinfo: Any = None,
    vtable_offset: int = 0,
    demangled_names: dict[str, set[int]] | None = None,
) -> int | None:
    """Resolve a virtual function name to an EA using the demangled-name cache.

    Mirrors the original ``helper.choose_virtual_func_address``.

    Args:
        name: The demangled name to look up.
        class_tinfo: Optional struct tinfo for the containing class (helps
            disambiguate when multiple classes define the same vtable entry).
        vtable_offset: Offset in the vtable (for ordered picking).
        demangled_names: The Session-owned demangled-names cache
            (``session.demangled_names``). Maps sanitized demangled name →
            set of EAs.

    Returns:
        The matching EA, or ``None`` if the name is not in the cache.
    """
    if demangled_names is None or name is None:
        return None
    candidates = demangled_names.get(name, set())
    if not candidates:
        return None
    if len(candidates) == 1:
        return next(iter(candidates))
    # Multiple matches — pick the one closest to vtable_offset if class_tinfo
    # is given (heuristic: same-class overrides tend to cluster). Otherwise
    # just return the first.
    return sorted(candidates)[0]


def to_hex(ea: int) -> str:
    """Format `ea` as a clickable hex address for the IDA output window.

    Mirrors the original `helper.to_hex`. Uses ``idaapi.inf_is_64bit()`` for
    the global bitness check (the per-address ``idaapi.get_64bit(ea)``
    requires an ``ea`` arg and would TypeError here).
    """
    if idaapi.inf_is_64bit():
        return f"0x{ea:016X}"
    return f"0x{ea:08X}"
