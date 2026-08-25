"""Test rename engine.

The ctree-walking extract/apply functions operate on live Hex-Rays ctree
objects and cannot be exercised with mocks — verified by use in a real IDA.
These tests cover the pure helpers: default-name detection and the
rename-worthiness check.
"""
from hexrays_pytools.domain.ctree.rename import (
    _can_be_part_of_assert,
    _is_default_name,
    _should_be_renamed,
    extract_rename_other_info,
    rename_other,
)


def test_is_default_name_matches_v_and_a_prefixes() -> None:
    """_is_default_name flags IDA auto-names like v1, a2."""
    assert _is_default_name("v1") is True
    assert _is_default_name("a23") is True
    assert _is_default_name("v") is False
    assert _is_default_name("vA") is False


def test_is_default_name_matches_field_and_word_prefixes() -> None:
    """_is_default_name flags field_, qword, dword, off_, word prefixes."""
    assert _is_default_name("field_4") is True
    assert _is_default_name("qword_10") is True
    assert _is_default_name("dword_8") is True
    assert _is_default_name("off_20") is True
    assert _is_default_name("word_2") is True


def test_is_default_name_rejects_real_names() -> None:
    """_is_default_name returns False for user-given names."""
    assert _is_default_name("count") is False
    assert _is_default_name("buffer") is False
    assert _is_default_name("this") is False


def test_should_be_renamed_skips_default_new_names() -> None:
    """Renaming into a default name is never worthwhile."""
    assert _should_be_renamed("count", "v1") is False
    assert _should_be_renamed("count", "field_4") is False


def test_should_be_renamed_skips_unchanged_names() -> None:
    """Renaming to the same (possibly underscore-prefixed) name is a no-op."""
    assert _should_be_renamed("count", "count") is False
    assert _should_be_renamed("_count", "count") is False


def test_should_be_renamed_allows_meaningful_rename() -> None:
    """Different, non-default names should be renamed."""
    assert _should_be_renamed("v1", "count") is True
    assert _should_be_renamed("v1", "_count") is True


def test_extract_rename_other_returns_none_for_non_expr_item() -> None:
    """extract_rename_other_info bails when the cursor item is not an expression."""
    from unittest.mock import MagicMock

    import idaapi
    cfunc = MagicMock()
    item = MagicMock()
    item.citype = idaapi.VDI_LVAR  # not VDI_EXPR
    assert extract_rename_other_info(cfunc, item) is None


def test_rename_other_stops_after_bounded_failures() -> None:
    from unittest.mock import MagicMock

    hx_view = MagicMock()
    hx_view.rename_lvar.return_value = False
    info = MagicMock()
    info.name = "count"

    rename_other(hx_view, info)

    assert hx_view.rename_lvar.call_count == 64


def test_assert_name_check_handles_utf8_string_literal(monkeypatch) -> None:
    from unittest.mock import MagicMock

    import idaapi
    import idc

    from hexrays_pytools.infra.arch import arch as arch_module

    expr = MagicMock()
    expr.op = idaapi.cot_obj
    expr.obj_ea = 0x500000
    item = MagicMock()
    item.citype = idaapi.VDI_EXPR
    item.it.to_specific_type = expr
    parent = MagicMock()
    parent.op = idaapi.cot_call
    parent.x.op = idaapi.cot_obj
    cfunc = MagicMock()
    cfunc.body.find_parent_of.return_value.to_specific_type = parent

    monkeypatch.setattr(arch_module, "is_code_ea", lambda _ea: False)
    monkeypatch.setattr(idc, "get_str_type", lambda _ea: idc.STRTYPE_C)
    monkeypatch.setattr(idc, "get_strlit_contents", lambda _ea: b"t\xc3\xaan_hop_le")
    monkeypatch.setattr(idaapi, "is_valid_typename", lambda value: isinstance(value, str))

    assert _can_be_part_of_assert(cfunc, item) is True
