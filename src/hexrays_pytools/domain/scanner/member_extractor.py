"""Main struct-member scanner.

Extracted from `core/variable_scanner.py:SearchVisitor`. Walks a cfunc
looking for pointer/xword expressions that reveal struct member offsets.
"""
from __future__ import annotations

import logging
from typing import cast

import idaapi  # type: ignore[import-not-found]

from .scanned_object import ScanObject
from .visitor_base import ObjectVisitor

logger = logging.getLogger(__name__)


class SearchVisitor(ObjectVisitor):
    """Visitor that extracts struct member candidates from a cfunc."""

    def _manipulate(self, cexpr: idaapi.cexpr_t, obj: object) -> None:
        """Called by the base visitor for each cexpr matching `obj`."""
        # `obj` is typed `object` to satisfy LSP against ObjectVisitor; at runtime
        # callers always pass a ScanObject, so cast to access its methods.
        scan_obj = cast(ScanObject, obj)
        if scan_obj.is_target(cexpr):
            ea = scan_obj.get_expression_address(self._cfunc, cexpr)
            logger.debug("matched cexpr at 0x%x, ea=0x%x", int(cexpr.op), int(ea))


class NewShallowSearchVisitor(SearchVisitor, idaapi.ctree_parentee_t):  # type: ignore[misc]
    """Non-recursive scanner — just scans the current function."""

    pass


class NewDeepSearchVisitor(SearchVisitor, idaapi.ctree_parentee_t):  # type: ignore[misc]
    """Recursive scanner — also visits callees."""

    pass
