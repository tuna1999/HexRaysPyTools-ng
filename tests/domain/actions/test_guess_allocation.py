"""Test guess_allocation action (GuessAllocation).

Phase A.7: the action is now wired to a real visitor + chooser. The end-to-end
ctree walk + IDA chooser are exercised in real IDA via idat headless; these
tests cover the action's metadata + the check predicate.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import idaapi  # type: ignore[import-not-found]

from hexrays_pytools.domain.actions.action import HexRaysPopupAction
from hexrays_pytools.domain.actions.guess_allocation import GuessAllocation


def test_guess_allocation_is_popup_action() -> None:
    """GuessAllocation subclasses HexRaysPopupAction and carries the right metadata."""
    assert issubclass(GuessAllocation, HexRaysPopupAction)
    assert GuessAllocation.description == "Guess allocation"
    assert GuessAllocation.hotkey is None


def test_guess_allocation_instantiable_with_session() -> None:
    """GuessAllocation(session=...) stores the session for later use."""
    session = MagicMock()
    a = GuessAllocation(session=session)
    assert a._session is session


def test_guess_allocation_name_includes_class_name() -> None:
    """Action name follows the `HexRaysPyTools:<ClassName>` convention."""
    a = GuessAllocation()
    assert a.name == "HexRaysPyTools:GuessAllocation"


def test_guess_allocation_check_rejects_non_vdi_expr() -> None:
    """check() returns False when the ctree item is not a VDI_EXPR."""
    hx_view = MagicMock()
    hx_view.item.citype = int(idaapi.VDI_FUNC)  # not VDI_EXPR
    assert GuessAllocation().check(hx_view) is False


def test_guess_allocation_check_rejects_unknown_scan_obj() -> None:
    """check() returns False when ScanObject.create returns None."""
    hx_view = MagicMock()
    hx_view.item.citype = int(idaapi.VDI_EXPR)
    # ScanObject.create with MagicMock args → unreachable path. Easier to
    # mock ScanObject.create at the call site.
    from hexrays_pytools.domain.actions import guess_allocation

    with (
        __import__("unittest.mock", fromlist=["patch"]).patch.object(
            guess_allocation, "ScanObject", create=True
        ),
    ):
        pass  # placeholder; see simpler direct test below

    # Direct test: when ScanObject.create returns None, check returns False.
    hx_view2 = MagicMock()
    hx_view2.item.citype = int(idaapi.VDI_EXPR)
    # Reach into the module to monkey-patch ScanObject.create
    from hexrays_pytools.domain.actions import guess_allocation as ga_module

    original_create = ga_module.ScanObject.create
    ga_module.ScanObject.create = lambda *_args, **_kw: None  # type: ignore[assignment]
    try:
        assert GuessAllocation().check(hx_view2) is False
    finally:
        ga_module.ScanObject.create = original_create


def test_guess_allocation_check_accepts_vdi_expr_with_scan_obj() -> None:
    """check() returns True when citype is VDI_EXPR and ScanObject.create succeeds."""
    hx_view = MagicMock()
    hx_view.item.citype = int(idaapi.VDI_EXPR)
    from hexrays_pytools.domain.actions import guess_allocation as ga_module

    original_create = ga_module.ScanObject.create
    ga_module.ScanObject.create = lambda *_args, **_kw: MagicMock()  # type: ignore[assignment]
    try:
        assert GuessAllocation().check(hx_view) is True
    finally:
        ga_module.ScanObject.create = original_create
