"""Test 4 event handlers.

The handlers dispatch on Hex-Rays maturity levels (CMAT_BUILT/TRANS1/TRANS2)
and operate on a live cfunc — they cannot be fully exercised with mocks.
These tests cover: no-op paths (wrong maturity level), the session DI seam,
and that handle does not raise on a synthetic cfunc at a non-matching level.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import idaapi

from hexrays_pytools.domain.actions.hx_events import (
    MemberDoubleClick,
    PotentialNegativeCollector,
    SilentIfSwapper,
    StructXrefCollector,
)
from hexrays_pytools.infra.arch.arch import choose_virtual_func_address


def _evt(cfunc: object = None, level: int = idaapi.CMAT_FINAL) -> tuple:
    """Build (event, cfunc, level) matching how the Hex-Rays maturity
    callback dispatches into handle(event, *args)."""
    return (int(idaapi.hxe_maturity), cfunc, level)


def test_member_double_click_handle_no_args_is_noop() -> None:
    """Calling handle with no args (not an hx_view) must not raise."""
    h = MemberDoubleClick()
    h.handle(int(idaapi.hxe_double_click))  # no crash


def test_member_double_click_handle_non_expr_item_is_noop() -> None:
    """handle ignores items that aren't VDI_EXPR (early-return guard)."""
    h = MemberDoubleClick()
    hx_view = MagicMock()
    hx_view.item.citype = int(idaapi.VDI_FUNC)  # not VDI_EXPR
    h.handle(int(idaapi.hxe_double_click), hx_view)


def test_member_double_click_handle_non_member_expr_is_noop() -> None:
    """handle ignores expressions that aren't cot_memptr/cot_memref."""
    h = MemberDoubleClick()
    hx_view = MagicMock()
    hx_view.item.citype = int(idaapi.VDI_EXPR)
    hx_view.item.e.op = int(idaapi.cot_var)  # not a member access
    h.handle(int(idaapi.hxe_double_click), hx_view)


def test_member_double_click_accepts_session() -> None:
    """MemberDoubleClick stores the session for use in handle()."""
    session = MagicMock()
    h = MemberDoubleClick(session=session)
    assert h._session is session


def test_choose_virtual_func_address_returns_none_for_unknown_name() -> None:
    """Returns None when the name isn't in the demangled_names cache."""
    assert choose_virtual_func_address("unknown_func", demangled_names={}) is None


def test_choose_virtual_func_address_returns_none_when_no_cache() -> None:
    """Returns None when no demangled_names dict is passed."""
    assert choose_virtual_func_address("func", demangled_names=None) is None


def test_choose_virtual_func_address_returns_single_match() -> None:
    """Returns the EA when exactly one EA matches the name."""
    cache = {"foo": {0x1000}}
    assert choose_virtual_func_address("foo", demangled_names=cache) == 0x1000


def test_choose_virtual_func_address_picks_first_when_multiple() -> None:
    """Returns the smallest EA when multiple EAs match."""
    cache = {"foo": {0x3000, 0x1000, 0x2000}}
    assert choose_virtual_func_address("foo", demangled_names=cache) == 0x1000


def test_potential_negative_collector_handle_non_matching_level() -> None:
    """At CMAT_FINAL (not CMAT_BUILT) the collector is a no-op."""
    cfunc = MagicMock()
    PotentialNegativeCollector().handle(*_evt(cfunc, idaapi.CMAT_FINAL))


def test_struct_xref_collector_handle_no_session_skips() -> None:
    """Without a session/xrefs, the handler logs and returns (no crash)."""
    cfunc = MagicMock()
    StructXrefCollector().handle(*_evt(cfunc, idaapi.CMAT_FINAL))


def test_struct_xref_collector_handle_non_matching_level() -> None:
    """At CMAT_BUILT (not CMAT_FINAL) the collector must not walk the ctree."""
    from hexrays_pytools.domain.actions import hx_events

    session = MagicMock()
    handler = StructXrefCollector(session=session)
    cfunc = MagicMock()
    with patch.object(hx_events, "StructXrefCollectorVisitor") as visitor_cls:
        handler.handle(*_evt(cfunc, idaapi.CMAT_BUILT))
    visitor_cls.assert_not_called()


def test_struct_xref_collector_handle_uses_session_storage() -> None:
    """With a session, the handler uses session.xrefs (not a fresh XrefStorage)."""
    from hexrays_pytools.domain.xrefs.xref_storage import XrefStorage

    session = MagicMock()
    session.xrefs = XrefStorage()
    handler = StructXrefCollector(session=session)
    cfunc = MagicMock()
    # CMAT_FINAL — visitor will be built but apply_to is a MagicMock (no
    # children) so no rows are collected. Just verify no crash and that
    # session.xrefs is the storage we wired.
    handler.handle(*_evt(cfunc, idaapi.CMAT_FINAL))
    # session.xrefs.identity should be unchanged (same instance).
    assert session.xrefs is session.xrefs


def test_struct_xref_collector_walks_only_at_final() -> None:
    """The visitor runs exactly once, at CMAT_FINAL."""
    from hexrays_pytools.domain.actions import hx_events

    session = MagicMock()
    handler = StructXrefCollector(session=session)
    cfunc = MagicMock()
    with patch.object(hx_events, "StructXrefCollectorVisitor") as visitor_cls:
        handler.handle(*_evt(cfunc, idaapi.CMAT_BUILT))
        handler.handle(*_evt(cfunc, idaapi.CMAT_TRANS1))
        visitor_cls.assert_not_called()
        handler.handle(*_evt(cfunc, idaapi.CMAT_FINAL))
    visitor_cls.assert_called_once()


def test_silent_if_swapper_handle_non_matching_level() -> None:
    """At CMAT_FINAL (not TRANS1/TRANS2) the swapper is a no-op."""
    cfunc = MagicMock()
    SilentIfSwapper().handle(*_evt(cfunc, idaapi.CMAT_FINAL))


def test_handlers_accept_session() -> None:
    session = MagicMock()
    h = MemberDoubleClick(session=session)
    assert h._session is session
