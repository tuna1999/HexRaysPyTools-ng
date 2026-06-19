"""Test the recursive (cross-function) object visitors.

These cover the Python-level state management: the `_visited` dedup set,
the `_new_for_visit` work queue, `prepare_new_scan` reset, and the
`_is_func_crippled` thunk heuristic. The live ctree dispatch (visit_expr /
leave_expr / `_check_call` / `_recursive_process`) is verified in real IDA.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import idaapi  # type: ignore[import-not-found]  # via mock_ida

from hexrays_pytools.domain.scanner.scanned_object import (
    SO_CALL_ARGUMENT,
    ScanObject,
)
from hexrays_pytools.domain.scanner.visitor_base import (
    ObjectDownwardsVisitor,
    ObjectUpwardsVisitor,
    RecursiveObjectDownwardsVisitor,
    RecursiveObjectUpwardsVisitor,
    RecursiveObjectVisitor,
)

# --- RecursiveObjectVisitor base ---------------------------------------------


def _make_recursive(cls: type) -> RecursiveObjectVisitor:
    """Build a minimal recursive visitor with a mock cfunc + seed object."""
    cfunc = MagicMock()
    obj = ScanObject()
    obj.ea = 0x401000
    obj.name = "seed"
    return cls(cfunc, obj)


def test_recursive_init_visited_is_empty() -> None:
    """A fresh recursive visitor starts with an empty _visited set."""
    v = _make_recursive(RecursiveObjectDownwardsVisitor)
    assert v._visited == set()


def test_recursive_init_new_for_visit_is_empty() -> None:
    """A fresh recursive visitor starts with an empty work queue."""
    v = _make_recursive(RecursiveObjectDownwardsVisitor)
    assert v._new_for_visit == set()


def test_recursive_init_accepts_existing_visited() -> None:
    """Passing visited= seeds the _visited set (multi-function scans share it)."""
    cfunc = MagicMock()
    obj = ScanObject()
    obj.ea = 0x401000
    seed: set[tuple[int, int]] = {(0x402000, 0)}
    v = RecursiveObjectDownwardsVisitor(cfunc, obj, visited=seed)
    assert (0x402000, 0) in v._visited


def test_recursive_add_visit_returns_true_for_new_target() -> None:
    """_add_visit records a new (func, arg) and returns True."""
    v = _make_recursive(RecursiveObjectDownwardsVisitor)
    assert v._add_visit(0x401000, 1) is True
    assert (0x401000, 1) in v._visited
    assert (0x401000, 1) in v._new_for_visit


def test_recursive_add_visit_returns_false_for_duplicate() -> None:
    """_add_visit dedupes: a second visit to the same (func, arg) is a no-op."""
    v = _make_recursive(RecursiveObjectDownwardsVisitor)
    assert v._add_visit(0x401000, 1) is True
    assert v._add_visit(0x401000, 1) is False  # already visited
    # Queue must not gain a duplicate
    assert len(v._new_for_visit) == 1


def test_recursive_prepare_new_scan_resets_state() -> None:
    """prepare_new_scan re-points the visitor at a fresh cfunc + seed."""
    v = _make_recursive(RecursiveObjectDownwardsVisitor)
    new_cfunc = MagicMock()
    new_cfunc.entry_ea = 0x402000
    new_cfunc.body.cblock.size.return_value = 5  # not crippled
    new_obj = ScanObject()
    new_obj.ea = 0x402010
    new_obj.name = "callee_seed"

    v.prepare_new_scan(new_cfunc, arg_idx=2, obj=new_obj)

    assert v._cfunc is new_cfunc
    assert v._arg_idx == 2
    assert v._objects == [new_obj]
    assert v._init_obj is new_obj
    assert v._skip is False


def test_recursive_is_func_crippled_single_return() -> None:
    """A function body of one `return` statement is crippled (passthrough)."""
    v = _make_recursive(RecursiveObjectDownwardsVisitor)
    stmt = MagicMock()
    stmt.op = idaapi.cit_return
    block = MagicMock()
    block.size.return_value = 1
    block.at.return_value = stmt
    v._cfunc.body.cblock = block
    assert v._is_func_crippled() is True


def test_recursive_is_func_crippled_single_call() -> None:
    """A function body of one bare call is crippled (thunk)."""
    v = _make_recursive(RecursiveObjectDownwardsVisitor)
    call_expr = MagicMock()
    call_expr.op = idaapi.cot_call
    stmt = MagicMock()
    stmt.op = idaapi.cit_expr
    stmt.cexpr = call_expr
    block = MagicMock()
    block.size.return_value = 1
    block.at.return_value = stmt
    v._cfunc.body.cblock = block
    assert v._is_func_crippled() is True


def test_recursive_is_func_crippled_false_for_multi_statement() -> None:
    """A multi-statement function body is not crippled."""
    v = _make_recursive(RecursiveObjectDownwardsVisitor)
    block = MagicMock()
    block.size.return_value = 3  # >1 statement
    v._cfunc.body.cblock = block
    assert v._is_func_crippled() is False


# --- RecursiveObjectDownwardsVisitor -----------------------------------------


def test_recursive_downwards_inherits_object_downwards() -> None:
    """RecursiveObjectDownwardsVisitor IS-A ObjectDownwardsVisitor."""
    v = _make_recursive(RecursiveObjectDownwardsVisitor)
    assert isinstance(v, ObjectDownwardsVisitor)
    assert isinstance(v, RecursiveObjectVisitor)


def test_recursive_downwards_has_cv_post_flag() -> None:
    """RecursiveObjectDownwardsVisitor sets CV_POST (inherited from Downwards)."""
    v = _make_recursive(RecursiveObjectDownwardsVisitor)
    assert v.cv_flags & int(idaapi.CV_POST)


def test_recursive_downwards_check_call_is_overridden() -> None:
    """RecursiveObjectDownwardsVisitor implements _check_call (not the base NotImplementedError)."""
    v = _make_recursive(RecursiveObjectDownwardsVisitor)
    # The base raises NotImplementedError; the concrete must not.
    # _check_call reads parent_expr() + parents — stub the parent chain so it
    # returns early without raising.
    v.parent_expr = MagicMock(return_value=None)  # no parent → early return
    v._check_call(MagicMock())  # should not raise NotImplementedError


# --- RecursiveObjectUpwardsVisitor -------------------------------------------


def test_recursive_upwards_inherits_object_upwards() -> None:
    """RecursiveObjectUpwardsVisitor IS-A ObjectUpwardsVisitor."""
    v = _make_recursive(RecursiveObjectUpwardsVisitor)
    assert isinstance(v, ObjectUpwardsVisitor)
    assert isinstance(v, RecursiveObjectVisitor)


def test_recursive_upwards_prepare_sets_call_obj_for_call_arg() -> None:
    """When the seed is a SO_CALL_ARGUMENT, prepare_new_scan sets _call_obj."""
    cfunc = MagicMock()
    cfunc.entry_ea = 0x401000
    cfunc.body.cblock.size.return_value = 3  # not crippled
    obj = ScanObject()
    obj.id = SO_CALL_ARGUMENT
    obj.ea = 0x401000
    obj.name = "call_arg"
    v = RecursiveObjectUpwardsVisitor(cfunc, obj)
    v.prepare_new_scan(cfunc, arg_idx=0, obj=obj)
    assert v._call_obj is obj


def test_recursive_upwards_prepare_leaves_call_obj_none_for_non_call_arg() -> None:
    """When the seed is NOT a call arg, prepare_new_scan leaves _call_obj None."""
    cfunc = MagicMock()
    cfunc.entry_ea = 0x401000
    cfunc.body.cblock.size.return_value = 3
    obj = ScanObject()
    obj.id = 1  # SO_LOCAL_VARIABLE
    obj.ea = 0x401000
    obj.name = "lvar"
    v = RecursiveObjectUpwardsVisitor(cfunc, obj)
    v.prepare_new_scan(cfunc, arg_idx=0, obj=obj)
    assert v._call_obj is None
