"""4 event handlers: MemberDoubleClick, PotentialNegativeCollector, StructXrefCollector, SilentIfSwapper."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

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
    """Run at CMAT_BUILT — detect CONTAINING_RECORD patterns."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def handle(self, event: int, *args: Any) -> None:
        logger.debug("PotentialNegativeCollector.handle")


class StructXrefCollector:
    """Run at CMAT_FINAL — populate XrefStorage."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def handle(self, event: int, *args: Any) -> None:
        logger.debug("StructXrefCollector.handle")


class SilentIfSwapper:
    """Run at CMAT_TRANS1+2 — re-apply saved if-swaps."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def handle(self, event: int, *args: Any) -> None:
        logger.debug("SilentIfSwapper.handle")
