"""Test the object visitor base classes (domain/scanner/visitor_base.py).

These tests exercise the ctree-parentee-t API using MagicMock. Real ctree
objects are not testable under mock_ida (no real visitor dispatch), so
the actual traversal code is verified in real IDA via idat headless.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from hexrays_pytools.domain.scanner.scanned_object import (
    SO_CALL_ARGUMENT,
    SO_LOCAL_VARIABLE,
    SO_RETURNED_OBJECT,
    ScanObject,
    VariableObject,
)
from hexrays_pytools.domain.scanner.visitor_base import (
    ObjectDownwardsVisitor,
    ObjectUpwardsVisitor,
    ObjectVisitor,
)

# --- ObjectVisitor base -------------------------------------------------------


def _make_visitor() -> ObjectVisitor:
    """Build a minimal ObjectVisitor with a mock cfunc + fake init obj."""
    cfunc = MagicMock()
    obj = ScanObject()
    obj.ea = 0x401000
    obj.id = SO_LOCAL_VARIABLE
    obj.name = "tracked"
    return ObjectVisitor(cfunc, obj, data=None, skip_until_object=False)


def test_visitor_process_calls_apply_to() -> None:
    """process() delegates to apply_to on the cfunc body."""
    v = _make_visitor()
    v.apply_to = MagicMock()  # patch: real ctree_parentee_t has no Python apply_to
    v.process()
    v.apply_to.assert_called_with(v._cfunc.body, None)


def test_visitor_initial_objects_contains_init_obj() -> None:
    """A new visitor's _objects list contains the init obj exactly once."""
    v = _make_visitor()
    assert v.objects == [v._init_obj]


def test_visitor_objects_is_readonly_copy() -> None:
    """``v.objects`` is a snapshot — mutating it doesn't affect _objects."""
    v = _make_visitor()
    snapshot = v.objects
    snapshot.append("garbage")
    assert v.objects == [v._init_obj]


def test_visitor_set_callbacks_overrides_manipulate() -> None:
    """set_callbacks(installs a custom manipulator) and _manipulate delegates to it.

    set_callbacks binds the function as an instance method (via __get__),
    so the callback receives ``self`` as its first argument.
    """
    v = _make_visitor()
    received: list[tuple[int, int]] = []

    def custom(visitor_self: object, cexpr: object, obj: object) -> None:
        assert visitor_self is v  # bound to the visitor instance
        received.append((int(cexpr.op), int(obj.id)))  # type: ignore[arg-type]

    v.set_callbacks(custom)

    cexpr = MagicMock(op=5)
    obj = MagicMock(id=3)
    v._manipulate(cexpr, obj)
    assert received == [(5, 3)]


def test_visitor_default_manipulate_logs_only() -> None:
    """Without a custom callback, _manipulate falls back to a debug log."""
    v = _make_visitor()  # no set_callbacks call
    # Should not raise even though there's no real logger handler.
    cexpr = MagicMock(op=1)
    obj = MagicMock(id=2)
    v._manipulate(cexpr, obj)


def test_visitor_get_line_returns_first_citem_text() -> None:
    """_get_line walks parents to the first citem (not cexpr)."""
    v = _make_visitor()

    citem = MagicMock()
    citem.is_expr.return_value = False
    citem.print1.return_value = "v1 = malloc(8);"
    citem.ea = 0x401000
    idaapi = MagicMock()  # noqa: F841 — used via import side effect
    import hexrays_pytools.domain.scanner.visitor_base as vb
    vb.idaapi.tag_remove = MagicMock(return_value="v1 = malloc(8);")

    cexpr = MagicMock()
    cexpr.is_expr.return_value = True
    cexpr.ea = 0x401000

    v.parents = [cexpr, citem]
    line = v._get_line()
    assert line == "v1 = malloc(8);"


def test_visitor_get_line_returns_empty_when_no_citem() -> None:
    """_get_line returns "" when the parent stack is all cexprs."""
    v = _make_visitor()
    cexpr = MagicMock()
    cexpr.is_expr.return_value = True
    cexpr.ea = 0x401000
    v.parents = [cexpr, cexpr, cexpr]
    assert v._get_line() == ""


def test_visitor_skip_initially_false_when_ea_valid() -> None:
    """_skip starts True only when skip_until_object=True AND start_ea is valid."""
    cfunc = MagicMock()
    obj = ScanObject()
    obj.ea = 0x401000
    obj.id = SO_LOCAL_VARIABLE
    v = ObjectVisitor(cfunc, obj, data=None, skip_until_object=True)
    assert v._skip is True

    v2 = ObjectVisitor(cfunc, obj, data=None, skip_until_object=False)
    assert v2._skip is False


def test_visitor_skip_false_when_start_ea_is_badaddr() -> None:
    """_skip falls back to False when the init obj has no address."""
    cfunc = MagicMock()
    obj = ScanObject()
    obj.ea = 0xFFFFFFFFFFFFFFFF  # BADADDR
    v = ObjectVisitor(cfunc, obj, data=None, skip_until_object=True)
    assert v._skip is False


# --- ObjectDownwardsVisitor ---------------------------------------------------


def test_downwards_inherits_from_object_visitor() -> None:
    """ObjectDownwardsVisitor IS-A ObjectVisitor."""
    cfunc = MagicMock()
    obj = ScanObject()
    obj.ea = 0x401000
    v = ObjectDownwardsVisitor(cfunc, obj)
    assert isinstance(v, ObjectVisitor)


def test_downwards_enables_cv_post_flag() -> None:
    """ObjectDownwardsVisitor sets cv_flags |= CV_POST."""
    cfunc = MagicMock()
    obj = ScanObject()
    obj.ea = 0x401000
    v = ObjectDownwardsVisitor(cfunc, obj)
    assert v.cv_flags & 1  # CV_POST = 1


def test_downwards_visit_expr_on_asg_tracks_rhs() -> None:
    """`a = tracked` should derive a new ScanObject for `a` and add it.

    visit_expr loops over _objects calling is_target(x) then is_target(y).
    For the tracked object: is_target(LHS `a`) → False, is_target(RHS
    `tracked`) → True → derive a new obj for `a` and append it.
    """
    cfunc = MagicMock()

    tracked = VariableObject(MagicMock(name="lv", type=MagicMock(return_value="T")), 0)
    tracked.ea = 0x401000
    # is_target called twice per object: first with LHS, then with RHS.
    tracked.is_target = MagicMock(side_effect=[False, True])

    v = ObjectDownwardsVisitor(cfunc, tracked, skip_until_object=False)

    # Build the `a = tracked` assignment shape.
    cexpr = MagicMock()
    cexpr.op = idaapi_cot_asg()
    cexpr.x = MagicMock()  # LHS `a`
    cexpr.y = MagicMock()  # RHS `tracked`
    cexpr.y.op = idaapi_cot_num()  # not cot_cast → y_cexpr = cexpr.y

    # ScanObject.create(cfunc, LHS) → a new tracked obj for `a`
    lvar_a = MagicMock(name="a", type=MagicMock(return_value="T_a"))
    new_obj = VariableObject(lvar_a, 5)
    new_obj.ea = 0x401010
    import hexrays_pytools.domain.scanner.scanned_object as so
    orig_create = so.ScanObject.create
    so.ScanObject.create = MagicMock(return_value=new_obj)  # type: ignore[assignment]
    try:
        v.visit_expr(cexpr)
    finally:
        so.ScanObject.create = orig_create  # type: ignore[assignment]

    assert new_obj in v.objects
    assert len(v.objects) == 2


def test_downwards_visit_expr_no_match_does_nothing() -> None:
    """Non-asg cexprs are no-ops in visit_expr."""
    cfunc = MagicMock()
    obj = ScanObject()
    obj.ea = 0x401000
    v = ObjectDownwardsVisitor(cfunc, obj, skip_until_object=False)
    cexpr = MagicMock()
    cexpr.op = idaapi_cot_num()  # not cot_asg  # type: ignore[name-defined]
    ret = v.visit_expr(cexpr)
    assert ret == 0
    assert v.objects == [obj]


def test_downwards_skip_mode_passes_until_initial() -> None:
    """When _skip=True, visit_expr is a no-op until the initial object is seen."""
    cfunc = MagicMock()
    obj = ScanObject()
    obj.ea = 0x401000
    v = ObjectDownwardsVisitor(cfunc, obj, skip_until_object=True)
    assert v._skip is True

    # First cexpr: not the initial — should be skipped
    cexpr1 = MagicMock()
    cexpr1.op = 0  # anything
    cexpr1.ea = 0x402000  # not the start_ea
    v.visit_expr(cexpr1)
    assert v._skip is True
    assert v.objects == [obj]


def test_downwards_leave_expr_skipped_in_skip_mode() -> None:
    """leave_expr is also a no-op in skip mode."""
    cfunc = MagicMock()
    obj = ScanObject()
    obj.ea = 0x401000
    v = ObjectDownwardsVisitor(cfunc, obj, skip_until_object=True)
    received: list[object] = []

    def cb(cexpr: object, o: object) -> None:
        received.append(o)

    v.set_callbacks(cb)
    v.leave_expr(MagicMock())
    assert received == []


def test_downwards_leave_expr_does_not_manipulate_returned() -> None:
    """SO_RETURNED_OBJECT matches in leave_expr but does NOT fire _manipulate."""
    cfunc = MagicMock()
    obj = ScanObject()
    obj.ea = 0x401000
    obj.id = SO_RETURNED_OBJECT
    v = ObjectDownwardsVisitor(cfunc, obj, skip_until_object=False)
    received: list[object] = []

    def cb(cexpr: object, o: object) -> None:
        received.append(o)

    v.set_callbacks(cb)
    v._skip = False  # make sure leave_expr doesn't bail on _skip

    cexpr = MagicMock()
    cexpr.op = idaapi_cot_call()  # type: ignore[name-defined]
    obj.is_target = MagicMock(return_value=True)  # the returned object DOES match
    v.leave_expr(cexpr)
    assert received == []  # but _manipulate is NOT called


def test_downwards_is_object_overwritten_simple() -> None:
    """Non-call RHS + ≥2 tracked objs → overwrite = True (value is gone).

    The original implementation short-circuits when ``len(_objects) < 2``,
    so this test needs two tracked objects to reach the real logic.
    """
    cfunc = MagicMock()
    obj1 = ScanObject()
    obj1.ea = 0x401000
    obj2 = ScanObject()
    obj2.ea = 0x401000
    v = ObjectDownwardsVisitor(cfunc, obj1, skip_until_object=False)
    v._objects.append(obj2)
    x = MagicMock()
    rhs = MagicMock()
    rhs.op = idaapi_cot_num()  # not a cast, not a call
    assert v._is_object_overwritten(x, obj1, rhs) is True


def test_downwards_is_object_overwritten_call_to_tracked() -> None:
    """`obj = other_tracked(...)` → NOT overwritten (rhs is a tracked call)."""
    cfunc = MagicMock()
    obj1 = ScanObject()
    obj1.ea = 0x401000
    obj2 = ScanObject()
    obj2.ea = 0x401000
    v = ObjectDownwardsVisitor(cfunc, obj1, skip_until_object=False)
    v._objects.append(obj2)
    x = MagicMock()
    call = MagicMock()
    call.op = idaapi_cot_call()  # type: ignore[name-defined]
    arg0 = MagicMock()
    call.a = [arg0]
    obj2.is_target = MagicMock(return_value=True)
    rhs = MagicMock()
    rhs.op = 99  # not a cast, use as-is
    rhs.x = call  # but _is_object_overwritten uses rhs directly if not cast
    # hmm, the function takes y_cexpr and checks if cast. Let's just pass call as y directly.
    assert v._is_object_overwritten(x, obj1, call) is False


# --- ObjectUpwardsVisitor -----------------------------------------------------


def test_upwards_inherits_from_object_visitor() -> None:
    """ObjectUpwardsVisitor IS-A ObjectVisitor."""
    cfunc = MagicMock()
    obj = ScanObject()
    obj.ea = 0x401000
    v = ObjectUpwardsVisitor(cfunc, obj)
    assert isinstance(v, ObjectVisitor)


def test_upwards_initial_stage_is_prepare() -> None:
    """Fresh visitor starts in STAGE_PREPARE."""
    cfunc = MagicMock()
    obj = ScanObject()
    obj.ea = 0x401000
    v = ObjectUpwardsVisitor(cfunc, obj)
    assert v._stage == ObjectUpwardsVisitor.STAGE_PREPARE


def test_upwards_visit_expr_in_parsing_is_noop() -> None:
    """visit_expr returns 0 immediately during STAGE_PARSING."""
    cfunc = MagicMock()
    obj = ScanObject()
    obj.ea = 0x401000
    v = ObjectUpwardsVisitor(cfunc, obj)
    v._stage = ObjectUpwardsVisitor.STAGE_PARSING
    assert v.visit_expr(MagicMock()) == 0


def test_upwards_visit_expr_adds_assignment_to_tree() -> None:
    """During STAGE_PREPARE, `a = b` adds `a → b` to the assignment tree."""
    cfunc = MagicMock()
    obj = ScanObject()
    obj.ea = 0x401000
    v = ObjectUpwardsVisitor(cfunc, obj, skip_after_object=False)

    # Patch ScanObject.create to return deterministic objects
    obj_left = ScanObject()
    obj_left.id = 1
    obj_right = ScanObject()
    obj_right.id = 2
    import hexrays_pytools.domain.scanner.scanned_object as so
    so.ScanObject.create = MagicMock(side_effect=[obj_left, obj_right])  # type: ignore[assignment]

    cexpr = MagicMock()
    cexpr.op = idaapi_cot_asg()  # type: ignore[name-defined]
    cexpr.x = MagicMock()
    cexpr.y = MagicMock()
    cexpr.y.op = 1  # not cast, use cexpr.y directly
    cexpr.ea = 0x401000

    v.visit_expr(cexpr)
    assert obj_left in v._tree
    assert obj_right in v._tree[obj_left]


def test_upwards_process_runs_two_stages() -> None:
    """process() runs PREPARE then PARSING (observable via the final _stage)."""
    cfunc = MagicMock()
    obj = ScanObject()
    obj.ea = 0x401000
    v = ObjectUpwardsVisitor(cfunc, obj)

    v.apply_to = MagicMock()  # patch — no real traversal under mock
    v.process()

    # apply_to should have been called twice (once per stage)
    assert v.apply_to.call_count == 2
    assert v._stage == ObjectUpwardsVisitor.STAGE_PARSING


def test_upwards_prepare_computes_transitive_closure() -> None:
    """_prepare walks the tree to compute the closure of objects feeding the seed."""
    cfunc = MagicMock()
    obj = ScanObject()
    obj.ea = 0x401000
    obj.id = 99
    v = ObjectUpwardsVisitor(cfunc, obj)

    # Build a tiny tree: a → b → c
    a, b, c = ScanObject(), ScanObject(), ScanObject()
    a.id, b.id, c.id = 1, 2, 3
    v._objects = [a]
    v._tree = {a: {b}, b: {c}}

    v._prepare()
    # After prepare, the closure of a should include {a, b, c}
    assert set(v._objects) == {a, b, c}
    assert v._tree == {}  # tree is cleared after the closure is computed


def test_upwards_call_arg_obj_uses_create_scan_obj() -> None:
    """When the seed is a CallArgObject, calls to it are unwrapped via create_scan_obj."""
    cfunc = MagicMock()
    obj = ScanObject()
    obj.ea = 0x401000
    obj.id = SO_CALL_ARGUMENT  # = 5
    v = ObjectUpwardsVisitor(cfunc, obj)

    # _call_obj is the seed itself when it's a SO_CALL_ARGUMENT
    assert v._call_obj is obj

    # Mock the call_obj's create_scan_obj to return a new obj
    derived = ScanObject()
    derived.id = 1
    obj.create_scan_obj = MagicMock(return_value=derived)  # type: ignore[attr-defined]

    cexpr = MagicMock()
    cexpr.op = idaapi_cot_call()  # type: ignore[name-defined]
    obj.is_target = MagicMock(return_value=True)

    v.visit_expr(cexpr)
    assert derived in v._objects
    obj.create_scan_obj.assert_called_once()  # type: ignore[attr-defined]


# --- Test helpers (real idaapi constants via mock_ida) -----------------------

import idaapi  # type: ignore[import-not-found]  # via mock_ida  # noqa: E402


def idaapi_cot_asg() -> int:
    return int(idaapi.cot_asg)


def idaapi_cot_num() -> int:
    return int(idaapi.cot_num)


def idaapi_cot_call() -> int:
    return int(idaapi.cot_call)
