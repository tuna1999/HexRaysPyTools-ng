"""Test SearchVisitor (domain/scanner/member_extractor.py).

The current ``member_extractor.py`` is a thin stub — ``SearchVisitor``
inherits from :class:`ObjectVisitor` and overrides ``_manipulate`` with a
debug-log fallback. The real extraction logic (parse pointer/xword
expressions, build struct members) lands in Phase A.5, at which point this
file gets expanded with the real tests.

Until then these tests just lock in the inheritance contract + that the
stub does not crash on a match.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from hexrays_pytools.domain.scanner.member_extractor import (
    NewShallowSearchVisitor,
    SearchVisitor,
)
from hexrays_pytools.domain.scanner.scanned_object import (
    SO_LOCAL_VARIABLE,
    ScanObject,
)


def _make_obj() -> ScanObject:
    """A minimal ScanObject seed for the visitor."""
    obj = ScanObject()
    obj.ea = 0x401000
    obj.id = SO_LOCAL_VARIABLE
    obj.name = "seed"
    return obj


def test_search_visitor_init() -> None:
    """SearchVisitor(cfunc, obj) initializes and tracks the seed object.

    Until Phase A.5 gives SearchVisitor its own ``__init__``, it inherits
    ``ObjectVisitor.__init__`` (4 required positional args).
    """
    cfunc = MagicMock()
    obj = _make_obj()
    v = SearchVisitor(cfunc, obj, data=None, skip_until_object=False)
    assert v._cfunc is cfunc
    assert v._init_obj is obj
    assert obj in v.objects


def test_search_visitor_manipulate_does_not_raise() -> None:
    """_manipulate is safe to call with a matching cexpr (stub logs only)."""
    cfunc = MagicMock()
    obj = _make_obj()
    v = SearchVisitor(cfunc, obj, data=None, skip_until_object=False)
    cexpr = MagicMock()
    cexpr.op = SO_LOCAL_VARIABLE
    cexpr.ea = 0x1000
    # Stub default — should not raise.
    v._manipulate(cexpr, obj)


def test_shallow_visitor_subclasses_search() -> None:
    """NewShallowSearchVisitor is a subclass of SearchVisitor."""
    assert issubclass(NewShallowSearchVisitor, SearchVisitor)
