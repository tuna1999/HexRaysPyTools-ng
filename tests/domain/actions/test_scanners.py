"""Test scanner actions (ShallowScanVariable, DeepScanVariable, RecognizeShape, DeepScanReturn, DeepScanFunctions)."""
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
    assert issubclass(Scanner, HexRaysPopupAction)
    assert Scanner.hotkey is None


def test_shallow_scan_variable_hotkey_f() -> None:
    assert ShallowScanVariable.description == "Scan Variable"
    assert ShallowScanVariable.hotkey == "F"


def test_shallow_scan_variable_instantiable_and_activates() -> None:
    a = ShallowScanVariable()
    assert a.name == "HexRaysPyTools:ShallowScanVariable"
    assert a.check(MagicMock()) is True
    a.activate(MagicMock())


def test_deep_scan_variable_hotkey_shift_alt_f() -> None:
    assert DeepScanVariable.description == "Deep Scan Variable"
    assert DeepScanVariable.hotkey == "Shift+Alt+F"


def test_deep_scan_variable_instantiable_and_activates() -> None:
    a = DeepScanVariable()
    assert a.name == "HexRaysPyTools:DeepScanVariable"
    a.activate(MagicMock())


def test_recognize_shape_no_hotkey() -> None:
    assert RecognizeShape.description == "Recognize Shape"
    # RecognizeShape inherits Scanner.hotkey (None)
    assert RecognizeShape.hotkey is None


def test_recognize_shape_instantiable_and_activates() -> None:
    a = RecognizeShape()
    assert a.name == "HexRaysPyTools:RecognizeShape"
    a.activate(MagicMock())


def test_deep_scan_return_instantiable_and_activates() -> None:
    a = DeepScanReturn()
    assert a.name == "HexRaysPyTools:DeepScanReturn"
    assert DeepScanReturn.description == "Deep Scan Returned Variables"
    a.activate(MagicMock())


def test_deep_scan_functions_is_action() -> None:
    assert issubclass(DeepScanFunctions, Action)
    assert DeepScanFunctions.description == "Scan First Argument"


def test_deep_scan_functions_instantiable_and_activates() -> None:
    a = DeepScanFunctions()
    assert a.name == "HexRaysPyTools:DeepScanFunctions"
    a.activate(MagicMock())


def test_all_five_accept_session() -> None:
    session = MagicMock()
    for cls in (ShallowScanVariable, DeepScanVariable, RecognizeShape, DeepScanReturn, DeepScanFunctions):
        a = cls(session=session)
        assert a._session is session
