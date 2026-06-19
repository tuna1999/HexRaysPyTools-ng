"""4 event handlers: MemberDoubleClick, PotentialNegativeCollector, StructXrefCollector, SilentIfSwapper."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import idaapi  # type: ignore[import-not-found]

from ..ctree.negative_offsets import collect_potential_negatives
from ..ctree.swap_if import SpaghettiVisitor, SwapThenElseVisitor, get_inverted, has_inverted

if TYPE_CHECKING:
    from ..session import Session

logger = logging.getLogger(__name__)


class MemberDoubleClick:
    """Handle hxe_double_click — navigate to virtual function."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def handle(self, event: int, *args: Any) -> None:
        # Real implementation requires UI navigation; stub for now
        logger.debug("MemberDoubleClick.handle: event=%d", event)


class PotentialNegativeCollector:
    """Run at CMAT_BUILT — detect and apply CONTAINING_RECORD patterns."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def handle(self, event: int, *args: Any) -> None:
        cfunc, level_of_maturity = args
        if int(level_of_maturity) == idaapi.CMAT_BUILT:
            collect_potential_negatives(cfunc)


class StructXrefCollector:
    """Run at CMAT_FINAL — populate XrefStorage."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def handle(self, event: int, *args: Any) -> None:
        logger.debug("StructXrefCollector.handle")


class SilentIfSwapper:
    """Run at CMAT_TRANS1+2 — re-apply saved if-swaps + spaghetti transform."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def handle(self, event: int, *args: Any) -> None:
        cfunc, level_of_maturity = args
        level = int(level_of_maturity)
        if level == idaapi.CMAT_TRANS1 and has_inverted(int(cfunc.entry_ea)):
            inverted_rvas = get_inverted(int(cfunc.entry_ea))
            inverted = [n + idaapi.get_imagebase() for n in inverted_rvas]
            visitor = SwapThenElseVisitor(set(inverted))
            visitor.apply_to(cfunc.body, None)
        elif level == idaapi.CMAT_TRANS2:
            visitor = SpaghettiVisitor()
            visitor.apply_to(cfunc.body, None)
