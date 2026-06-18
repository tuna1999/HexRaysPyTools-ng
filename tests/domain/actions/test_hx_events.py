"""Test 4 event handlers."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.hx_events import (
    MemberDoubleClick,
    PotentialNegativeCollector,
    SilentIfSwapper,
    StructXrefCollector,
)


def test_member_double_click_handle() -> None:
    h = MemberDoubleClick()
    h.handle(0)  # should not raise


def test_potential_negative_collector_handle() -> None:
    h = PotentialNegativeCollector()
    h.handle(0)


def test_struct_xref_collector_handle() -> None:
    h = StructXrefCollector()
    h.handle(0)


def test_silent_if_swapper_handle() -> None:
    h = SilentIfSwapper()
    h.handle(0)


def test_handlers_accept_session() -> None:
    session = MagicMock()
    h = MemberDoubleClick(session=session)
    assert h._session is session
