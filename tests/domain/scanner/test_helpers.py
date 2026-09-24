"""Test scanner helpers (domain/scanner/helpers.py + infra/arch.is_imported_ea).

These cover the pure-Python control flow: the DecompilationFailure guard
in ``decompile_function``, the .plt / set-membership logic in
``is_imported_ea``, and the call-target collection in
``FunctionTouchVisitor``. The live ctree dispatch is verified in real IDA.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import idaapi  # type: ignore[import-not-found]  # via mock_ida

from hexrays_pytools.domain.scanner.helpers import (
    FunctionTouchVisitor,
    decompile_function,
)
from hexrays_pytools.infra.arch.arch import is_imported_ea

# --- decompile_function -------------------------------------------------------


def test_decompile_function_returns_cfunc_on_success() -> None:
    """Happy path: idaapi.decompile returns a cfunc → returned unchanged."""
    cfunc = MagicMock(name="cfunc")
    idaapi.decompile = MagicMock(return_value=cfunc)
    result = decompile_function(0x401000)
    assert result is cfunc
    idaapi.decompile.assert_called_once_with(0x401000)


def test_decompile_function_returns_none_on_decompilation_failure() -> None:
    """DecompilationFailure is caught and None is returned (scan continues)."""
    idaapi.decompile = MagicMock(side_effect=idaapi.DecompilationFailure)
    result = decompile_function(0x402000)
    assert result is None


def test_decompile_function_returns_none_when_decompile_returns_falsy() -> None:
    """When idaapi.decompile returns None/False, the helper returns None."""
    idaapi.decompile = MagicMock(return_value=None)
    result = decompile_function(0x403000)
    assert result is None


# --- is_imported_ea -----------------------------------------------------------


def test_is_imported_ea_true_for_plt_segment() -> None:
    """An address in the .plt segment is always imported."""
    import idc  # type: ignore[import-not-found]
    idc.get_segm_name = MagicMock(return_value=".plt")
    assert is_imported_ea(0x401000, imported_ea=set()) is True


def test_is_imported_ea_false_for_non_plt_not_in_cache() -> None:
    """Non-.plt address not in the import cache is not imported."""
    import idc  # type: ignore[import-not-found]
    idc.get_segm_name = MagicMock(return_value=".text")
    assert is_imported_ea(0x401000, imported_ea=set()) is False


def test_is_imported_ea_true_when_in_cache() -> None:
    """Session import cache stores the same absolute EAs used by ctree callers."""
    import idc  # type: ignore[import-not-found]
    idc.get_segm_name = MagicMock(return_value=".text")
    assert is_imported_ea(0x401000, imported_ea={0x401000}) is True


# --- FunctionTouchVisitor -----------------------------------------------------


def test_function_touch_visitor_visit_expr_collects_call_targets() -> None:
    """visit_expr records addresses only for direct calls."""
    cfunc = MagicMock()
    touched: set[int] = set()
    imported_ea: set[int] = set()
    v = FunctionTouchVisitor(cfunc, touched, imported_ea)

    call_expr = MagicMock()
    call_expr.op = idaapi.cot_call
    call_expr.x.op = idaapi.cot_obj
    call_expr.x.obj_ea = 0x405000
    v.visit_expr(call_expr)
    assert 0x405000 in v.functions

    # Non-call expressions are ignored
    num_expr = MagicMock()
    num_expr.op = idaapi.cot_num
    v.visit_expr(num_expr)
    assert v.functions == {0x405000}


def test_function_touch_visitor_ignores_indirect_calls() -> None:
    v = FunctionTouchVisitor(MagicMock(), set(), set())
    call = SimpleNamespace(op=idaapi.cot_call, x=SimpleNamespace(op=idaapi.cot_var))

    assert v.visit_expr(call) == 0
    assert v.functions == set()


def test_function_touch_visitor_process_marks_function_touched() -> None:
    """process() marks the entry_ea as touched and runs the traversal."""
    cfunc = MagicMock()
    cfunc.entry_ea = 0x401000
    touched: set[int] = set()
    v = FunctionTouchVisitor(cfunc, touched, imported_ea=set())
    v.apply_to = MagicMock()  # patch — no real dispatch under mock

    result = v.process()
    assert result is True
    assert 0x401000 in touched
    v.apply_to.assert_called_once()


def test_function_touch_visitor_process_skips_already_touched() -> None:
    """If the entry_ea was already touched, process() returns False and does nothing."""
    cfunc = MagicMock()
    cfunc.entry_ea = 0x401000
    touched: set[int] = {0x401000}
    v = FunctionTouchVisitor(cfunc, touched, imported_ea=set())
    v.apply_to = MagicMock()

    result = v.process()
    assert result is False
    v.apply_to.assert_not_called()


def test_function_touch_visitor_refresh_failure_does_not_poison_touched_cache() -> None:
    cfunc = MagicMock()
    cfunc.entry_ea = 0x401000
    touched: set[int] = set()
    v = FunctionTouchVisitor(cfunc, touched, imported_ea=set())
    v.apply_to = MagicMock()
    idaapi.decompile = MagicMock(side_effect=idaapi.DecompilationFailure)

    assert v.process() is False
    assert 0x401000 not in touched
