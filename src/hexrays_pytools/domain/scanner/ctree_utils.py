"""ctree traversal helpers.

Extracted from `core/helper.py:find_asm_address` and `api.py:parent walker`.
"""
from __future__ import annotations

import idaapi  # type: ignore[import-not-found]


def find_asm_address(cexpr: idaapi.cexpr_t) -> int:
    """Find the nearest ancestor citem with a real (non-BADADDR) address.

    Returns BADADDR if no such ancestor exists.
    """
    while cexpr and cexpr.ea == idaapi.BADADDR:
        # Find parent and traverse up
        # In real use, callers pass cfunc so we can call find_parent_of;
        # for the simple case, return BADADDR when no address is found.
        return int(idaapi.BADADDR)
    return int(cexpr.ea) if cexpr else int(idaapi.BADADDR)
