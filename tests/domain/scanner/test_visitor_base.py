"""Test ObjectVisitor."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.scanner.visitor_base import ObjectVisitor


def test_visitor_process_calls_apply_to() -> None:
    """process() calls apply_to on the cfunc body."""
    cfunc = MagicMock()
    cfunc.body = "fake_body"
    v = ObjectVisitor(cfunc)
    v.apply_to = MagicMock()  # patch: real ctree_parentee_t has no Python apply_to
    v.process()
    v.apply_to.assert_called_with("fake_body", None)


def test_visitor_objects_initially_empty() -> None:
    """A new visitor has no objects."""
    cfunc = MagicMock()
    v = ObjectVisitor(cfunc)
    assert v.objects == []


def test_visitor_subclass_must_implement_manipulate() -> None:
    """ObjectVisitor._manipulate raises NotImplementedError."""
    cfunc = MagicMock()
    v = ObjectVisitor(cfunc)
    try:
        v._manipulate("expr", "obj")
        raise AssertionError("should have raised")
    except NotImplementedError:
        pass
