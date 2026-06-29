"""Test 6 rename action wrappers."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import idaapi  # type: ignore[import-not-found]

from hexrays_pytools.domain.actions.action import HexRaysPopupAction
from hexrays_pytools.domain.actions.rename_action import (
    PropagateName,
    RenameInside,
    RenameMemberFromFunctionName,
    RenameOther,
    RenameOutside,
    RenameUsingAssert,
    _is_default_name,
)


def test_rename_actions_subclass_hexrays_popup_action() -> None:
    for cls in (RenameOther, RenameInside, RenameOutside,
                RenameMemberFromFunctionName, RenameUsingAssert, PropagateName):
        assert issubclass(cls, HexRaysPopupAction)


def test_rename_other_metadata() -> None:
    a = RenameOther()
    assert a.name == "HexRaysPyTools:RenameOther"
    assert a.description == "Take other name"
    assert a.hotkey == "Ctrl+N"


def test_rename_inside_metadata() -> None:
    a = RenameInside()
    assert a.name == "HexRaysPyTools:RenameInside"
    assert a.description == "Rename inside argument"
    assert a.hotkey == "Shift+Alt+N"


def test_rename_outside_metadata() -> None:
    a = RenameOutside()
    assert a.name == "HexRaysPyTools:RenameOutside"
    assert a.description == "Take argument name"
    assert a.hotkey == "Ctrl+Shift+N"


def test_rename_member_from_function_name_metadata() -> None:
    a = RenameMemberFromFunctionName()
    assert a.name == "HexRaysPyTools:RenameMemberFromFunctionName"
    assert a.description == "Take name from function"
    assert a.hotkey == "Ctrl+Alt+N"


def test_rename_using_assert_metadata() -> None:
    a = RenameUsingAssert()
    assert a.name == "HexRaysPyTools:RenameUsingAssert"
    assert a.description == "Rename as assert argument"
    assert a.hotkey is None


def test_propagate_name_metadata() -> None:
    a = PropagateName()
    assert a.name == "HexRaysPyTools:PropagateName"
    assert a.description == "Propagate name"
    assert a.hotkey == "P"


def test_all_six_accept_session() -> None:
    session = MagicMock()
    for cls in (RenameOther, RenameInside, RenameOutside,
                RenameMemberFromFunctionName, RenameUsingAssert, PropagateName):
        a = cls(session=session)
        assert a._session is session


# --- Phase A.8 PropagateName tests -------------------------------------------


def test_is_default_name_matches_a_v_pattern() -> None:
    """IDA's default name pattern: a1, v3 (single char + digits)."""
    assert _is_default_name("a1") is True
    assert _is_default_name("v3") is True
    assert _is_default_name("a42") is True
    assert _is_default_name("v100") is True


def test_is_default_name_matches_qword_field_off() -> None:
    """Word/field_/off_ prefixes are also defaults."""
    assert _is_default_name("qword_8") is True
    assert _is_default_name("dword_4") is True
    assert _is_default_name("word_2") is True
    assert _is_default_name("field_10") is True
    assert _is_default_name("off_4") is True


def test_is_default_name_rejects_real_names() -> None:
    """Real user-defined names are NOT defaults."""
    assert _is_default_name("my_var") is False
    assert _is_default_name("count") is False
    assert _is_default_name("n_elements") is False


def test_propagate_name_check_rejects_non_vdi_expr() -> None:
    """check() returns False when the ctree item is not a VDI_EXPR."""
    hx_view = MagicMock()
    hx_view.item.citype = int(idaapi.VDI_FUNC)
    assert PropagateName().check(hx_view) is False


def test_propagate_name_check_rejects_default_name() -> None:
    """check() returns False when the obj name is a default name (nothing to propagate)."""
    from hexrays_pytools.domain.actions import rename_action as ra_module

    hx_view = MagicMock()
    hx_view.item.citype = int(idaapi.VDI_EXPR)
    original_create = ra_module.ScanObject.create

    def _make_default_obj(*_args: Any, **_kw: Any) -> Any:
        m = MagicMock()
        m.name = "a1"  # explicit — MagicMock(name="a1") only sets the repr
        return m

    ra_module.ScanObject.create = _make_default_obj  # type: ignore[assignment]
    try:
        assert PropagateName().check(hx_view) is False
    finally:
        ra_module.ScanObject.create = original_create


def test_propagate_name_check_accepts_real_name() -> None:
    """check() returns True when obj has a real name to propagate."""
    from hexrays_pytools.domain.actions import rename_action as ra_module

    hx_view = MagicMock()
    hx_view.item.citype = int(idaapi.VDI_EXPR)
    original_create = ra_module.ScanObject.create

    def _make_real_obj(*_args: Any, **_kw: Any) -> Any:
        m = MagicMock()
        m.name = "count"
        return m

    ra_module.ScanObject.create = _make_real_obj  # type: ignore[assignment]
    try:
        assert PropagateName().check(hx_view) is True
    finally:
        ra_module.ScanObject.create = original_create


def test_propagate_name_activate_no_crash_with_bare_magicmock() -> None:
    """activate() with bare MagicMock must not raise (early-return on no session)."""
    a = PropagateName()
    a.activate(MagicMock())
