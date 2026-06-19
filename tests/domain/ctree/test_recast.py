"""Test recast engine.

The ctree-walking core (``extract_recast_info_left/right``, ``apply_recast``)
operates on live Hex-Rays ctree objects and cannot be exercised with mocks —
it is verified by loading the plugin in a real IDA. These tests cover the
pure parts: the recast-descriptor namedtuples and the label builder.
"""
from unittest.mock import MagicMock

from hexrays_pytools.domain.ctree.recast import (
    RecastArgument,
    RecastGlobalVariable,
    RecastLocalVariable,
    RecastReturn,
    RecastStructure,
    apply_recast,
    extract_recast_info_left,
    extract_recast_info_right,
    recast_label,
)


def test_extract_left_returns_none_for_non_expr_item() -> None:
    """extract_recast_info_left bails when the cursor item is not an expression."""
    import idaapi

    cfunc = MagicMock()
    item = MagicMock()
    item.citype = idaapi.VDI_LVAR  # not VDI_EXPR
    assert extract_recast_info_left(cfunc, item) is None


def test_extract_right_returns_none_for_non_expr_item() -> None:
    """extract_recast_info_right bails when the cursor item is not an expression."""
    import idaapi

    cfunc = MagicMock()
    item = MagicMock()
    item.citype = idaapi.VDI_LVAR  # not VDI_EXPR
    assert extract_recast_info_right(cfunc, item) is None


def test_recast_label_local_variable() -> None:
    """recast_label formats a local-variable recast."""
    tinfo = MagicMock()
    tinfo.dstr.return_value = "FOO *"
    lvar = MagicMock()
    lvar.name = "v1"
    ri = RecastLocalVariable(recast_tinfo=tinfo, local_variable=lvar)
    assert recast_label(ri) == 'Recast Variable "v1" to FOO *'


def test_recast_label_argument() -> None:
    """recast_label formats an argument recast."""
    ri = RecastArgument(
        recast_tinfo=MagicMock(), arg_idx=0, func_ea=0x1000, func_tinfo=MagicMock()
    )
    assert recast_label(ri) == "Recast Argument"


def test_recast_label_structure() -> None:
    """recast_label formats a struct-field recast."""
    ri = RecastStructure(
        recast_tinfo=MagicMock(), structure_name="MyStruct", field_offset=8
    )
    assert recast_label(ri) == "Recast Field of MyStruct structure"


def test_recast_label_return_has_type_placeholder() -> None:
    """B9 fix: the Return label includes the type name (original dropped it)."""
    tinfo = MagicMock()
    tinfo.dstr.return_value = "BAR *"
    ri = RecastReturn(recast_tinfo=tinfo, func_ea=0x2000)
    assert recast_label(ri) == "Recast Return to BAR *"


def test_recast_label_global_variable() -> None:
    """recast_label formats a global-variable recast."""
    import idaapi

    idaapi.get_name.return_value = "g_thing"
    tinfo = MagicMock()
    tinfo.dstr.return_value = "int"
    ri = RecastGlobalVariable(recast_tinfo=tinfo, global_variable_ea=0x4000)
    assert recast_label(ri) == 'Recast Global Variable "g_thing" to int'


def test_apply_recast_unknown_descriptor_returns_false() -> None:
    """apply_recast returns False for an unknown descriptor type."""
    hx_view = MagicMock()
    assert apply_recast(hx_view, "not a recast descriptor") is False
    hx_view.refresh_view.assert_not_called()


def test_decompile_function_returns_none_on_failure() -> None:
    """decompile_function returns None on DecompilationFailure."""
    import idaapi

    # MagicMock can't be raised; use a real exception via the mock's attribute.
    idaapi.decompile.side_effect = Exception("DecompilationFailure")
    from hexrays_pytools.domain.ctree.recast import decompile_function

    assert decompile_function(0x1000) is None


def test_decompile_function_returns_none_when_decompile_returns_falsy() -> None:
    """decompile_function returns None when idaapi.decompile returns None."""
    import idaapi

    idaapi.decompile.return_value = None
    from hexrays_pytools.domain.ctree.recast import decompile_function

    assert decompile_function(0x1000) is None


def test_decompile_function_returns_cfunc_on_success() -> None:
    """decompile_function returns the cfunc on success."""
    import idaapi

    cfunc = MagicMock()
    idaapi.decompile.return_value = cfunc
    from hexrays_pytools.domain.ctree.recast import decompile_function

    assert decompile_function(0x1000) is cfunc


def test_is_code_ea_strips_thumb_bit() -> None:
    """_is_code_ea masks the ARM THUMB bit before checking."""
    import idaapi

    idaapi.is_code.return_value = True
    from hexrays_pytools.domain.ctree.recast import _is_code_ea

    _is_code_ea(0x1001)
    idaapi.get_full_flags.assert_called_with(0x1000)


def test_apply_recast_local_variable_sets_lvar_type() -> None:
    """apply_recast calls set_lvar_type for a local-variable descriptor."""
    hx_view = MagicMock()
    tinfo = MagicMock()
    lvar = MagicMock()
    apply_recast(hx_view, RecastLocalVariable(recast_tinfo=tinfo, local_variable=lvar))
    hx_view.set_lvar_type.assert_called_once_with(lvar, tinfo)
    hx_view.refresh_view.assert_called_once_with(True)


def test_apply_recast_global_variable_applies_tinfo() -> None:
    """apply_recast calls apply_tinfo for a global-variable descriptor."""
    import idaapi

    hx_view = MagicMock()
    tinfo = MagicMock()
    apply_recast(hx_view, RecastGlobalVariable(recast_tinfo=tinfo, global_variable_ea=0x4000))
    idaapi.apply_tinfo.assert_called_once()
    hx_view.refresh_view.assert_called_once_with(True)


def test_apply_recast_argument_converts_array_to_ptr() -> None:
    """apply_recast converts array args to pointers before setting."""
    hx_view = MagicMock()
    recast = MagicMock()
    recast.is_array.return_value = True
    func_tinfo = MagicMock()
    apply_recast(
        hx_view,
        RecastArgument(
            recast_tinfo=recast, arg_idx=1, func_ea=0x1000, func_tinfo=func_tinfo
        ),
    )
    recast.convert_array_to_ptr.assert_called_once()
    hx_view.refresh_view.assert_called_once_with(True)


def test_apply_recast_return_bails_when_decompile_fails() -> None:
    """apply_recast returns False for a Return recast when decompile fails."""
    import idaapi

    idaapi.decompile.side_effect = Exception("DecompilationFailure")
    hx_view = MagicMock()
    tinfo = MagicMock()
    result = apply_recast(hx_view, RecastReturn(recast_tinfo=tinfo, func_ea=0x2000))
    assert result is False
    hx_view.refresh_view.assert_not_called()


def test_apply_recast_structure_bails_on_unknown_type() -> None:
    """apply_recast returns False for a Structure recast when the type has no ordinal."""
    import idaapi

    idaapi.get_type_ordinal.return_value = 0
    hx_view = MagicMock()
    result = apply_recast(
        hx_view, RecastStructure(recast_tinfo=MagicMock(), structure_name="Nope", field_offset=0)
    )
    assert result is False
    hx_view.refresh_view.assert_not_called()
