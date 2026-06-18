"""ScanObject hierarchy — represents items found during ctree traversal.

Extracted from the original `api.py`. Used by `ObjectVisitor` subclasses
to track which expressions/variables/functions to operate on.
"""
from __future__ import annotations

import idaapi  # type: ignore[import-not-found]

# Object kind constants (used by `ScanObject.create()` factory)
SO_LOCAL_VARIABLE = 1
SO_STRUCT_POINTER = 2
SO_STRUCT_REFERENCE = 3
SO_GLOBAL_OBJECT = 4
SO_CALL_ARGUMENT = 5
SO_MEMORY_ALLOCATOR = 6
SO_RETURNED_OBJECT = 7


class ScanObject:
    """Base class for a single scanned item."""

    def __init__(self, ea: int, name: str, tinfo: idaapi.tinfo_t, op: int) -> None:
        self.ea = ea
        self.name = name
        self.tinfo = tinfo
        self.id = op

    def is_target(self, cexpr: idaapi.cexpr_t) -> bool:
        """Return True if `cexpr` represents this object."""
        return bool(cexpr.op == self.id)

    def get_expression_address(self, cfunc: idaapi.cfunc_t, cexpr: idaapi.cexpr_t) -> int:
        """Walk up ctree parents to find a real address for `cexpr`."""
        while cexpr and cexpr.ea == idaapi.BADADDR:
            parent = cfunc.body.find_parent_of(cexpr)
            if not parent:
                return int(idaapi.BADADDR)
            cexpr = parent.cexpr
        return int(cexpr.ea) if cexpr else int(idaapi.BADADDR)
