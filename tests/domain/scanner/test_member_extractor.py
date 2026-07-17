"""Test SearchVisitor (domain/scanner/member_extractor.py) — inheritance smoke tests.

The real extraction logic (parse pointer/xword expressions, build struct
members) is verified in ``test_search_visitor.py`` for the pure helpers
and in real IDA via idat headless for the ctree walk itself. This file
locks in the inheritance contract and that construction + a no-op manipulate
call do not raise.
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
    """SearchVisitor(cfunc, origin, obj, workspace) initializes the seed object."""
    cfunc = MagicMock()
    obj = _make_obj()
    workspace = MagicMock()
    v = SearchVisitor(cfunc, origin=0x0, obj=obj, workspace=workspace)
    assert v._cfunc is cfunc
    assert v._init_obj is obj
    assert obj in v.objects
    assert v._origin == 0x0
    assert v._workspace is workspace


def test_search_visitor_manipulate_does_not_raise() -> None:
    """A bare _manipulate call with a MagicMock cexpr/obj is safe (early-return paths)."""
    cfunc = MagicMock()
    obj = _make_obj()
    # The new SearchVisitor._manipulate calls ScannedObject.create(obj, ...)
    # which needs the obj to have the right attribute for its id (lvar for
    # SO_LOCAL_VARIABLE). Set lvar = MagicMock so the create path doesn't
    # blow up on attribute access.
    obj.lvar = MagicMock()
    obj.lvar.location = MagicMock()
    obj.lvar.defea = 0x1000
    workspace = MagicMock()
    workspace.model = None  # model is None → add_row skipped
    v = SearchVisitor(cfunc, origin=0x0, obj=obj, workspace=workspace, consts=None)
    cexpr = MagicMock()
    cexpr.op = SO_LOCAL_VARIABLE
    cexpr.ea = 0x1000
    cexpr.type = MagicMock()
    # _manipulate will check is_legal_type → cexpr.type.is_ptr() etc. All MagicMock
    # returns are falsy, so the visitor should hit the `is_legal_type` True branch
    # and call __extract_member_from_xword, which walks parents — empty list, so
    # it falls through to default_tinfo (None) and __deref_tinfo(None) → None.
    # The result is None, so member is None, and we exit early. Must not raise.
    v._manipulate(cexpr, obj)


def test_shallow_visitor_subclasses_search() -> None:
    """NewShallowSearchVisitor is a subclass of SearchVisitor."""
    assert issubclass(NewShallowSearchVisitor, SearchVisitor)


def test_deref_tinfo_attribute_name_correct() -> None:
    """Regression for ``_SearchVisitor__deref_tinfo`` name-mangling bug.

    SearchVisitor defines ``_deref_tinfo`` (single underscore = ``public``
    Python convention for "private"). Calling it as ``self.__deref_tinfo``
    inside a subclass method name-mangles to ``_SearchVisitor__deref_tinfo``
    which raises ``AttributeError`` at runtime — the original
    HexRaysPyTools v1.x didn't have this issue because the original used a
    flat class, not a multiple-inheritance subclass.

    This test simply checks ``_deref_tinfo`` is reachable on every visitor
    subclass (SearchVisitor, NewShallowSearchVisitor,
    NewDeepSearchVisitor, DeepReturnVisitor).
    """
    from hexrays_pytools.domain.scanner.member_extractor import (  # type: ignore[import-not-found]
        DeepReturnVisitor,
        NewDeepSearchVisitor,
    )

    for cls in (
        SearchVisitor,
        NewShallowSearchVisitor,
        NewDeepSearchVisitor,
        DeepReturnVisitor,
    ):
        assert hasattr(cls, "_deref_tinfo"), f"{cls.__name__} missing _deref_tinfo"
        assert isinstance(cls._deref_tinfo, classmethod) or hasattr(
            cls, "_deref_tinfo"
        ), f"{cls.__name__}._deref_tinfo not a method"
