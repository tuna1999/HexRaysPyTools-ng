"""Test 4 event handlers.

The handlers dispatch on Hex-Rays maturity levels (CMAT_BUILT/TRANS1/TRANS2)
and operate on a live cfunc — they cannot be fully exercised with mocks.
These tests cover: no-op paths (wrong maturity level), the session DI seam,
and that handle does not raise on a synthetic cfunc at a non-matching level.
"""
from unittest.mock import MagicMock

import idaapi

from hexrays_pytools.domain.actions.hx_events import (
    MemberDoubleClick,
    PotentialNegativeCollector,
    SilentIfSwapper,
    StructXrefCollector,
)


def _evt(cfunc: object = None, level: int = idaapi.CMAT_FINAL) -> tuple:
    """Build (event, cfunc, level) matching how the Hex-Rays maturity
    callback dispatches into handle(event, *args)."""
    return (int(idaapi.hxe_maturity), cfunc, level)


def test_member_double_click_handle() -> None:
    h = MemberDoubleClick()
    h.handle(int(idaapi.hxe_double_click))  # should not raise


def test_potential_negative_collector_handle_non_matching_level() -> None:
    """At CMAT_FINAL (not CMAT_BUILT) the collector is a no-op."""
    cfunc = MagicMock()
    PotentialNegativeCollector().handle(*_evt(cfunc, idaapi.CMAT_FINAL))


def test_struct_xref_collector_handle() -> None:
    cfunc = MagicMock()
    StructXrefCollector().handle(*_evt(cfunc, idaapi.CMAT_FINAL))


def test_silent_if_swapper_handle_non_matching_level() -> None:
    """At CMAT_FINAL (not TRANS1/TRANS2) the swapper is a no-op."""
    cfunc = MagicMock()
    SilentIfSwapper().handle(*_evt(cfunc, idaapi.CMAT_FINAL))


def test_handlers_accept_session() -> None:
    session = MagicMock()
    h = MemberDoubleClick(session=session)
    assert h._session is session
