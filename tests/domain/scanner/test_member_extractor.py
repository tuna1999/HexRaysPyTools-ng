"""Test SearchVisitor."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.scanner.member_extractor import (
    NewShallowSearchVisitor,
    SearchVisitor,
)
from hexrays_pytools.domain.scanner.scanned_object import SO_LOCAL_VARIABLE


def test_search_visitor_init() -> None:
    """SearchVisitor(cfunc) initializes with the cfunc."""
    cfunc = MagicMock()
    v = SearchVisitor(cfunc)
    assert v._cfunc is cfunc


def test_search_visitor_manipulate_matches_target() -> None:
    """_manipulate processes cexprs that match the obj's is_target."""
    cfunc = MagicMock()
    v = SearchVisitor(cfunc)
    obj = MagicMock()
    obj.is_target.return_value = True
    cexpr = MagicMock()
    cexpr.op = SO_LOCAL_VARIABLE
    cexpr.ea = 0x1000
    v._manipulate(cexpr, obj)  # should not raise


def test_shallow_visitor_subclasses_search() -> None:
    """NewShallowSearchVisitor is a subclass of SearchVisitor."""
    assert issubclass(NewShallowSearchVisitor, SearchVisitor)
