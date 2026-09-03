"""Test scanner actions (ShallowScanVariable, DeepScanVariable, RecognizeShape, DeepScanReturn, DeepScanFunctions).

Phase A.7: the actions are wired to the SearchVisitor engine. The end-to-end
ctree walk is verified in real IDA via idat headless; these tests cover the
action metadata, the check predicates, and the no-crash contract for
``activate()`` with a bare MagicMock context.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

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


def test_deep_scan_captures_object_before_touching_ctree() -> None:
    """Deep scan must not recreate its ScanObject after FunctionTouchVisitor refreshes ctree."""
    import idaapi  # type: ignore[import-not-found]

    from hexrays_pytools.domain.actions import scanners

    session = MagicMock()
    session.recon = MagicMock()
    session.recon.main_offset = 0
    session.imported_ea = set()
    session.touched_functions = set()
    action = DeepScanVariable(session=session)

    ctx = MagicMock()
    hx_view = MagicMock()
    cfunc_before = MagicMock()
    cfunc_before.entry_ea = 0x401000
    cfunc_after = MagicMock()
    cfunc_after.entry_ea = 0x401000
    hx_view.cfunc = cfunc_before
    scan_obj = MagicMock()
    scan_obj.tinfo = MagicMock()

    with patch.object(idaapi, "get_widget_vdui", return_value=hx_view), patch.object(
        action, "_can_be_scanned", return_value=True
    ), patch.object(scanners.ScanObject, "create", return_value=scan_obj) as create, patch.object(
        scanners, "FunctionTouchVisitor"
    ) as touch_cls, patch.object(scanners, "NewDeepSearchVisitor") as visitor_cls, patch.object(
        action, "_log_scan_start"
    ):
        touch_cls.return_value.process.side_effect = lambda: setattr(hx_view, "cfunc", cfunc_after) or True
        action.activate(ctx)

    create.assert_called_once_with(cfunc_before, hx_view.item)
    hx_view.refresh_view.assert_called_once_with(True)
    visitor_cls.assert_called_once_with(
        cfunc_after,
        0,
        scan_obj,
        session.recon,
        consts=session.consts,
    )


def test_scan_start_log_uses_debug(caplog) -> None:
    """Scan markers are only visible when DEBUG logging is enabled."""
    import idaapi  # type: ignore[import-not-found]

    cfunc = MagicMock()
    cfunc.entry_ea = 0x401000
    obj = MagicMock()
    obj.name = "this"
    with patch.object(idaapi, "get_name", return_value="Foo_method"), caplog.at_level("DEBUG"):
        Scanner._log_scan_start("Deep Scan", cfunc, obj, 0x20)

    assert "[HexRaysPyTools][Deep Scan] this in Foo_method @ 0x401000 (origin=0x20)" in caplog.text


def test_scanner_output_uses_debug(caplog) -> None:
    """Scanner diagnostics respect the configurable DEBUG threshold."""
    with caplog.at_level("DEBUG"):
        Scanner._output("[HexRaysPyTools][Scan] action invoked")

    assert "[HexRaysPyTools][Scan] action invoked" in caplog.text


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


def _make_session(scan_any_type: bool) -> tuple[MagicMock, MagicMock]:
    session = MagicMock()
    session.scan_any_type = scan_any_type
    legal_type = MagicMock()
    legal_type.equals_to.return_value = False
    session.consts.legal_types = [legal_type]
    return session, legal_type


def _basic_tinfo() -> MagicMock:
    """A mock tinfo that passes the base is_legal_type checks (not ptr/unknown)."""
    tinfo = MagicMock()
    tinfo.is_ptr.return_value = False
    tinfo.is_unknown.return_value = False
    return tinfo


def test_is_scannable_scan_any_type_true_accepts_any_type() -> None:
    session, legal = _make_session(scan_any_type=True)
    action = ShallowScanVariable(session=session)
    assert action._is_scannable(_basic_tinfo()) is True
    legal.equals_to.assert_not_called()


def test_is_scannable_scan_any_type_false_rejects_non_legal_type() -> None:
    session, legal = _make_session(scan_any_type=False)
    action = ShallowScanVariable(session=session)
    assert action._is_scannable(_basic_tinfo()) is False
    legal.equals_to.assert_called_once()


def test_is_scannable_scan_any_type_false_accepts_legal_type() -> None:
    session, legal = _make_session(scan_any_type=False)
    legal.equals_to.return_value = True
    action = ShallowScanVariable(session=session)
    assert action._is_scannable(_basic_tinfo()) is True


def test_is_scannable_scan_any_type_false_accepts_forward_decl_pointer() -> None:
    session, _legal = _make_session(scan_any_type=False)
    tinfo = MagicMock()
    tinfo.is_ptr.return_value = True
    tinfo.get_pointed_object.return_value.is_forward_decl.return_value = True
    tinfo.get_pointed_object.return_value.get_size.return_value = object()  # != BADSIZE
    action = ShallowScanVariable(session=session)
    assert action._is_scannable(tinfo) is True


def test_deep_scan_functions_update_attaches_to_funcs_popup() -> None:
    """In the Functions chooser, the action must attach itself to the popup."""
    import idaapi  # type: ignore[import-not-found]

    a = DeepScanFunctions()
    ctx = MagicMock()
    with patch.object(idaapi, "BWN_FUNCS", 40), patch.object(
        idaapi, "AST_ENABLE_FOR_WIDGET", 1
    ) as _ast, patch.object(idaapi, "attach_action_to_popup") as attach:
        ctx.widget_type = 40
        result = a.update(ctx)
    assert result == 1
    attach.assert_called_once_with(ctx.widget, None, a.name)


def test_deep_scan_functions_update_other_widget_no_attach() -> None:
    import idaapi  # type: ignore[import-not-found]

    a = DeepScanFunctions()
    ctx = MagicMock()
    with patch.object(idaapi, "BWN_FUNCS", 40), patch.object(
        idaapi, "AST_DISABLE_FOR_WIDGET", 2
    ) as _ast, patch.object(idaapi, "attach_action_to_popup") as attach:
        ctx.widget_type = 99
        result = a.update(ctx)
    assert result == 2
    attach.assert_not_called()
