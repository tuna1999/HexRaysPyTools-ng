"""Test scanner actions (ShallowScanVariable, DeepScanVariable, RecognizeShape, DeepScanReturn, DeepScanFunctions).

Phase A.7: the actions are wired to the SearchVisitor engine. The end-to-end
ctree walk is verified in real IDA via idat headless; these tests cover the
action metadata, the check predicates, and the no-crash contract for
``activate()`` with a bare MagicMock context.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.action import Action, HexRaysPopupAction
from hexrays_pytools.domain.actions.scanners import (
    DeepScanFunctions,
    DeepScanReturn,
    DeepScanVariable,
    RecognizeShape,
    Scanner,
    ShallowScanVariable,
)


def test_scanner_is_popup_action() -> None:
    """Scanner subclasses HexRaysPopupAction; default hotkey is None."""
    assert issubclass(Scanner, HexRaysPopupAction)
    assert Scanner.hotkey is None


def test_shallow_scan_variable_hotkey_f() -> None:
    """ShallowScanVariable has the F hotkey + correct description."""
    assert ShallowScanVariable.description == "Scan Variable"
    assert ShallowScanVariable.hotkey == "F"


def test_shallow_scan_variable_instantiable() -> None:
    """ShallowScanVariable is constructible with no args + a session."""
    a = ShallowScanVariable()
    assert a.name == "HexRaysPyTools:ShallowScanVariable"
    # activate() with bare MagicMock must not raise (early-return on no workspace).
    a.activate(MagicMock())


def test_deep_scan_variable_hotkey_shift_alt_f() -> None:
    """DeepScanVariable has the Shift+Alt+F hotkey + correct description."""
    assert DeepScanVariable.description == "Deep Scan Variable"
    assert DeepScanVariable.hotkey == "Shift+Alt+F"


def test_deep_scan_variable_instantiable() -> None:
    """DeepScanVariable is constructible; activate() must not raise on bare MagicMock."""
    a = DeepScanVariable()
    assert a.name == "HexRaysPyTools:DeepScanVariable"
    a.activate(MagicMock())


def test_recognize_shape_no_hotkey() -> None:
    """RecognizeShape inherits Scanner.hotkey (None)."""
    assert RecognizeShape.description == "Recognize Shape"
    assert RecognizeShape.hotkey is None


def test_recognize_shape_instantiable() -> None:
    """RecognizeShape is constructible; activate() must not raise on bare MagicMock."""
    a = RecognizeShape()
    assert a.name == "HexRaysPyTools:RecognizeShape"
    a.activate(MagicMock())


def test_deep_scan_return_metadata() -> None:
    """DeepScanReturn has the correct description."""
    assert DeepScanReturn.description == "Deep Scan Returned Variables"


def test_deep_scan_return_instantiable() -> None:
    """DeepScanReturn is constructible; activate() must not raise on bare MagicMock."""
    a = DeepScanReturn()
    assert a.name == "HexRaysPyTools:DeepScanReturn"
    a.activate(MagicMock())


def test_deep_scan_return_check_rejects_non_func_item() -> None:
    """DeepScanReturn.check returns False when ctree_item.citype != VDI_FUNC."""
    import idaapi  # type: ignore[import-not-found]

    hx_view = MagicMock()
    hx_view.item.citype = int(idaapi.VDI_EXPR)  # not VDI_FUNC
    assert DeepScanReturn().check(hx_view) is False


def test_deep_scan_functions_is_action() -> None:
    """DeepScanFunctions subclasses Action (not HexRaysPopupAction)."""
    assert issubclass(DeepScanFunctions, Action)
    assert DeepScanFunctions.description == "Scan First Argument"


def test_deep_scan_functions_instantiable() -> None:
    """DeepScanFunctions is constructible; activate() must not raise on bare MagicMock."""
    a = DeepScanFunctions()
    assert a.name == "HexRaysPyTools:DeepScanFunctions"
    a.activate(MagicMock())


def test_all_six_actions_accept_session() -> None:
    """All 5 scanners + DeepScanFunctions accept session= in their constructor."""
    session = MagicMock()
    for cls in (
        ShallowScanVariable,
        DeepScanVariable,
        RecognizeShape,
        DeepScanReturn,
        DeepScanFunctions,
    ):
        a = cls(session=session)
        assert a._session is session
