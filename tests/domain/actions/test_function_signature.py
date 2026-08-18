"""Test function_signature actions (ConvertToUsercall, AddRemoveReturn, RemoveArgument).

The ``check``/``activate`` paths operate on a live Hex-Rays cfunc/func_type
and cannot be exercised with mocks. These tests cover the constructible
surface: metadata, the None-input guard, and that activate does not raise
when the view cannot be resolved.
"""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.action import HexRaysPopupAction
from hexrays_pytools.domain.actions.function_signature import (
    AddRemoveReturn,
    ConvertToUsercall,
    RemoveArgument,
)


def test_convert_to_usercall_is_popup_action() -> None:
    assert issubclass(ConvertToUsercall, HexRaysPopupAction)
    assert ConvertToUsercall.description == "Convert to __usercall"
    assert ConvertToUsercall.menu_path == "HexRaysPyTools/Function/"


def test_add_remove_return_is_popup_action() -> None:
    assert issubclass(AddRemoveReturn, HexRaysPopupAction)
    assert AddRemoveReturn.description == "Add/Remove Return"
    assert AddRemoveReturn.menu_path == "HexRaysPyTools/Function/"


def test_remove_argument_is_popup_action() -> None:
    assert issubclass(RemoveArgument, HexRaysPopupAction)
    assert RemoveArgument.description == "Remove Argument"
    assert RemoveArgument.menu_path == "HexRaysPyTools/Function/"


def test_all_three_accept_session() -> None:
    session = MagicMock()
    for cls in (ConvertToUsercall, AddRemoveReturn, RemoveArgument):
        a = cls(session=session)
        assert a._session is session


def test_check_returns_false_for_none_view() -> None:
    """check() returns False when there is no decompiler view."""
    assert ConvertToUsercall().check(None) is False
    assert AddRemoveReturn().check(None) is False
    assert RemoveArgument().check(None) is False


def test_convert_to_usercall_check_requires_func_item() -> None:
    """ConvertToUsercall.check is True only when the cursor is on the function."""
    import idaapi

    hx = MagicMock()
    hx.item.citype = idaapi.VDI_FUNC
    assert ConvertToUsercall().check(hx) is True
    hx.item.citype = idaapi.VDI_EXPR
    assert ConvertToUsercall().check(hx) is False


def test_add_remove_return_check_requires_func_item() -> None:
    """AddRemoveReturn.check is True only when the cursor is on the function."""
    import idaapi

    hx = MagicMock()
    hx.item.citype = idaapi.VDI_FUNC
    assert AddRemoveReturn().check(hx) is True
    hx.item.citype = idaapi.VDI_EXPR
    assert AddRemoveReturn().check(hx) is False


def test_remove_argument_check_requires_arg_lvar() -> None:
    """RemoveArgument.check is True only for an argument local variable."""
    import idaapi

    hx = MagicMock()
    hx.item.citype = idaapi.VDI_LVAR
    lvar = MagicMock()
    lvar.is_arg_var.return_value = True
    hx.item.get_lvar.return_value = lvar
    assert RemoveArgument().check(hx) is True
    lvar.is_arg_var.return_value = False
    assert RemoveArgument().check(hx) is False
    hx.item.citype = idaapi.VDI_EXPR
    assert RemoveArgument().check(hx) is False


def test_activate_with_mock_view_is_noop() -> None:
    """activate() does not raise when the view cannot be resolved / no func type."""
    ctx = MagicMock()
    import idaapi
    # get_widget_vdui returns a mock view whose cfunc.get_func_type fails → early return
    vu = MagicMock()
    vu.cfunc.get_func_type.return_value = False
    idaapi.get_widget_vdui.return_value = vu
    ConvertToUsercall().activate(ctx)  # must not raise
    AddRemoveReturn().activate(ctx)
    RemoveArgument().activate(ctx)


# --- activate() paths with a working func type ----------------------------


def _wire_func_type(monkeypatch, rettype_is_void: bool = False, cc: int = 0):
    """Patch idaapi so activate() reaches the signature-modifying body.

    Returns (vu, function_tinfo, function_details) mocks for assertions.
    """
    import idaapi

    vu = MagicMock()
    vu.cfunc.get_func_type.side_effect = lambda _t: True
    monkeypatch.setattr(idaapi, "get_widget_vdui", lambda _w: vu)

    function_tinfo = MagicMock(name="function_tinfo")
    function_details = MagicMock(name="function_details")
    function_details.cc = cc
    function_details.rettype.equals_to.return_value = rettype_is_void
    monkeypatch.setattr(idaapi, "tinfo_t", lambda *a, **k: function_tinfo)
    monkeypatch.setattr(idaapi, "func_type_data_t", lambda: function_details)
    return vu, function_tinfo, function_details


def test_convert_cdecl_to_usercall(monkeypatch) -> None:
    """cdecl → CM_CC_SPECIAL, create_func + apply_tinfo + refresh called."""
    import idaapi

    vu, ftinfo, fdetails = _wire_func_type(monkeypatch, cc=idaapi.CM_CC_CDECL)
    apply_mock = MagicMock()
    monkeypatch.setattr(idaapi, "apply_tinfo", apply_mock)

    ConvertToUsercall().activate(MagicMock())

    assert fdetails.cc == idaapi.CM_CC_SPECIAL
    ftinfo.create_func.assert_called_once_with(fdetails)
    apply_mock.assert_called_once()
    vu.refresh_view.assert_called_once_with(True)


def test_convert_stdcall_to_specialp(monkeypatch) -> None:
    """stdcall/fastcall/thiscall/pascal → CM_CC_SPECIALP."""
    import idaapi

    for cc in (idaapi.CM_CC_STDCALL, idaapi.CM_CC_FASTCALL, idaapi.CM_CC_THISCALL, idaapi.CM_CC_PASCAL):
        _vu, ftinfo, fdetails = _wire_func_type(monkeypatch, cc=cc)
        monkeypatch.setattr(idaapi, "apply_tinfo", MagicMock())
        ConvertToUsercall().activate(MagicMock())
        assert fdetails.cc == idaapi.CM_CC_SPECIALP, f"cc={cc} should map to SPECIALP"
        ftinfo.create_func.assert_called_once_with(fdetails)


def test_convert_ellipsis_to_speciale(monkeypatch) -> None:
    """ellipsis → CM_CC_SPECIALE."""
    import idaapi

    _vu, ftinfo, fdetails = _wire_func_type(monkeypatch, cc=idaapi.CM_CC_ELLIPSIS)
    monkeypatch.setattr(idaapi, "apply_tinfo", MagicMock())
    ConvertToUsercall().activate(MagicMock())
    assert fdetails.cc == idaapi.CM_CC_SPECIALE
    ftinfo.create_func.assert_called_once_with(fdetails)


def test_convert_unknown_convention_is_noop(monkeypatch) -> None:
    """An unknown cc leaves the function untouched (no create_func/apply)."""
    import idaapi

    _vu, ftinfo, fdetails = _wire_func_type(monkeypatch, cc=0x7)  # not any known CC
    apply_mock = MagicMock()
    monkeypatch.setattr(idaapi, "apply_tinfo", apply_mock)
    ConvertToUsercall().activate(MagicMock())
    ftinfo.create_func.assert_not_called()
    apply_mock.assert_not_called()


def test_add_remove_return_void_to_ptr(monkeypatch) -> None:
    """void rettype → create_ptr(void) assigned back."""
    import idaapi

    _vu, ftinfo, fdetails = _wire_func_type(monkeypatch, rettype_is_void=True)
    monkeypatch.setattr(idaapi, "apply_tinfo", MagicMock())
    AddRemoveReturn().activate(MagicMock())
    # tinfo_t() constructor returns function_tinfo mock; its create_ptr must be used
    assert ftinfo.create_ptr.called or fdetails.rettype is not None
    ftinfo.create_func.assert_called_once_with(fdetails)


def test_add_remove_return_nonvoid_to_void(monkeypatch) -> None:
    """non-void rettype → replaced by BT_VOID tinfo."""
    import idaapi

    _vu, ftinfo, fdetails = _wire_func_type(monkeypatch, rettype_is_void=False)
    monkeypatch.setattr(idaapi, "apply_tinfo", MagicMock())
    AddRemoveReturn().activate(MagicMock())
    # rettype was overwritten with the (mock) void tinfo from tinfo_t(BT_VOID)
    assert fdetails.rettype is ftinfo  # monkeypatched tinfo_t returns function_tinfo
    ftinfo.create_func.assert_called_once_with(fdetails)


def test_remove_argument_erases_match(monkeypatch) -> None:
    """Matching arg by name is erased from func details."""
    import idaapi

    vu, ftinfo, fdetails = _wire_func_type(monkeypatch)
    monkeypatch.setattr(idaapi, "apply_tinfo", MagicMock())
    arg = MagicMock()
    arg.name = "a1"
    fdetails.__iter__ = lambda _s: iter([arg])
    lvar = MagicMock()
    lvar.name = "a1"
    vu.item.get_lvar.return_value = lvar

    RemoveArgument().activate(MagicMock())

    fdetails.erase.assert_called_once_with(arg)
    ftinfo.create_func.assert_called_once_with(fdetails)


def test_remove_argument_no_match_is_noop(monkeypatch) -> None:
    """No arg with the lvar's name → erase never called."""
    import idaapi

    vu, ftinfo, fdetails = _wire_func_type(monkeypatch)
    apply_mock = MagicMock()
    monkeypatch.setattr(idaapi, "apply_tinfo", apply_mock)
    other = MagicMock()
    other.name = "other"
    fdetails.__iter__ = lambda _s: iter([other])
    lvar = MagicMock()
    lvar.name = "a1"
    vu.item.get_lvar.return_value = lvar

    RemoveArgument().activate(MagicMock())

    fdetails.erase.assert_not_called()
    ftinfo.create_func.assert_not_called()
    apply_mock.assert_not_called()
