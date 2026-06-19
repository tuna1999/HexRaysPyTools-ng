"""ctree traversal helpers.

Extracted from `core/helper.py:find_asm_address` and `api.py:parent walker`.
"""
from __future__ import annotations

from typing import Any

import idaapi  # type: ignore[import-not-found]


def find_asm_address(cexpr: Any, parents: Any = None) -> int:
    """Find the nearest ancestor citem with a real (non-BADADDR) address.

    When `parents` (the ctree_parentee_t parents stack) is provided, walk it
    upwards — used inside a ctree visitor. Otherwise just check the cexpr's
    own address. Returns BADADDR if no real address is found.
    """
    if parents is not None:
        # parents is the parent stack from a ctree_parentee_t; iterate reversed.
        for parent in reversed(parents):
            cexpr_p = parent.cexpr if hasattr(parent, "cexpr") else None
            if cexpr_p is not None and cexpr_p.ea != idaapi.BADADDR:
                return int(cexpr_p.ea)
        return int(idaapi.BADADDR)
    while cexpr and cexpr.ea == idaapi.BADADDR:
        return int(idaapi.BADADDR)
    return int(cexpr.ea) if cexpr else int(idaapi.BADADDR)

