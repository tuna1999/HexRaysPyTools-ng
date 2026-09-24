"""Test SearchVisitor Python-level state + pure helpers.

The visitor's ``_manipulate`` walks the live ctree (not unit-testable with
mocks — same exclusion as ``visitor_base.py``). These tests cover the
``_deref_tinfo``, ``_extract_obj_ea``, ``_parse_call``, and the concrete
subclass inheritance chain.

``_deref_tinfo`` is an instance method that reads the per-session
``Consts`` dataclass (replaces the original module-level ``const.PCHAR_TINFO``
etc. globals). The tests stub ``self._consts`` with a ``MagicMock`` carrying
just the fields the helper touches.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import idaapi  # type: ignore[import-not-found]

from hexrays_pytools.domain.scanner.member_extractor import (
    DeepReturnVisitor,
    NewDeepSearchVisitor,
    NewShallowSearchVisitor,
    SearchVisitor,
)
from hexrays_pytools.domain.scanner.visitor_base import (
    ObjectDownwardsVisitor,
    RecursiveObjectDownwardsVisitor,
)


def _make_visitor(consts: Any | None = None) -> SearchVisitor:
    """Build a SearchVisitor bypassing ``__init__`` (no real cfunc needed)."""
    cfunc = MagicMock()
    obj = MagicMock()
    obj.ea = 0x1000
    v = SearchVisitor.__new__(SearchVisitor)
    v._cfunc = cfunc
    v._init_obj = obj
    v._consts = consts
    v.crippled = False
    return v


def test_search_visitor_deref_tinfo_non_ptr_returns_unchanged() -> None:
    """_deref_tinfo returns the same tinfo when input is not a pointer."""
    visitor = _make_visitor()
    tinfo = MagicMock()
    tinfo.is_ptr.return_value = False
    assert visitor._deref_tinfo(tinfo) is tinfo


def test_search_visitor_deref_tinfo_x_word_ptr_returns_pointed() -> None:
    """_deref_tinfo on a pointer returns the pointed-to tinfo."""
    visitor = _make_visitor()
    tinfo = MagicMock()
    tinfo.is_ptr.return_value = True
    tinfo.get_ptrarr_objsize.return_value = 8  # x_word size
    pointed = MagicMock()
    tinfo.get_pointed_object.return_value = pointed
    result = visitor._deref_tinfo(tinfo)
    assert result is pointed


def test_search_visitor_deref_tinfo_char_ptr_returns_char() -> None:
    """_deref_tinfo on char* (1-byte pointer) returns CHAR tinfo from consts."""
    visitor = _make_visitor(consts=MagicMock())
    tinfo = MagicMock()
    tinfo.is_ptr.return_value = True
    tinfo.get_ptrarr_objsize.return_value = 1
    # equals_to returns True → char* branch
    tinfo.equals_to.return_value = True

    char_tinfo = MagicMock(name="char_typed")
    visitor._consts.pchar_tinfo = MagicMock()
    visitor._consts.const_pchar_tinfo = MagicMock()
    visitor._consts.char_tinfo = char_tinfo

    result = visitor._deref_tinfo(tinfo)
    assert result is char_tinfo


def test_search_visitor_deref_tinfo_one_byte_void_ptr_returns_none() -> None:
    """_deref_tinfo on 1-byte void* returns None (becomes VoidMember)."""
    visitor = _make_visitor(consts=MagicMock())
    tinfo = MagicMock()
    tinfo.is_ptr.return_value = True
    tinfo.get_ptrarr_objsize.return_value = 1
    # equals_to returns False → fall into the None branch
    tinfo.equals_to.return_value = False

    result = visitor._deref_tinfo(tinfo)
    assert result is None


def test_search_visitor_extract_obj_ea_strips_ref() -> None:
    """_extract_obj_ea strips cot_ref, then reads cot_obj.obj_ea."""
    inner = MagicMock()
    inner.op = int(idaapi.cot_obj)
    inner.obj_ea = 0x2000

    outer = MagicMock()
    outer.op = int(idaapi.cot_ref)
    outer.x = inner

    result = SearchVisitor._extract_obj_ea(outer)
    assert result == 0x2000


def test_search_visitor_extract_obj_ea_returns_none_for_non_obj() -> None:
    """_extract_obj_ea returns None when expr is not cot_obj after unwrap."""
    inner = MagicMock()
    inner.op = int(idaapi.cot_asg)  # not cot_obj
    outer = MagicMock()
    outer.op = int(idaapi.cot_ref)
    outer.x = inner
    result = SearchVisitor._extract_obj_ea(outer)
    assert result is None


def test_search_visitor_parse_call_returns_arg_tinfo() -> None:
    """_parse_call calls get_call_argument_info and derefs the tinfo."""
    from hexrays_pytools.domain.scanner import member_extractor

    visitor = _make_visitor(consts=MagicMock())
    call_cexpr = MagicMock()
    arg_cexpr = MagicMock()

    expected_tinfo = MagicMock(name="arg_tinfo")
    deref_tinfo = MagicMock(name="deref")

    with patch.object(
        member_extractor, "get_call_argument_info", return_value=(0, expected_tinfo)
    ) as mock_gcai, patch.object(
        member_extractor.SearchVisitor,
        "_deref_tinfo",
        return_value=deref_tinfo,
    ):
        result = member_extractor.SearchVisitor._parse_call(
            visitor, call_cexpr, arg_cexpr, 0
        )
        assert result is deref_tinfo
        mock_gcai.assert_called_once_with(call_cexpr, arg_cexpr)


def test_search_visitor_parse_call_falls_back_to_char() -> None:
    """_parse_call returns consts.char_tinfo when no tinfo can be derived."""
    from hexrays_pytools.domain.scanner import member_extractor

    char_tinfo = MagicMock(name="CHAR")
    consts = MagicMock()
    consts.char_tinfo = char_tinfo
    visitor = _make_visitor(consts=consts)

    call_cexpr = MagicMock()
    arg_cexpr = MagicMock()

    with patch.object(
        member_extractor, "get_call_argument_info", return_value=(0, None)
    ):
        result = member_extractor.SearchVisitor._parse_call(
            visitor, call_cexpr, arg_cexpr, 0
        )
        assert result is char_tinfo


def test_pointer_arithmetic_assignment_records_offset_without_extra_parent() -> None:
    visitor = _make_visitor(consts=MagicMock())
    visitor._origin = 0
    visitor.parents = []
    tinfo = MagicMock()
    tinfo.get_size.return_value = 4
    tinfo.is_ptr.return_value = False
    visitor._consts.px_word_tinfo = tinfo
    expr = SimpleNamespace(op=idaapi.cot_add)
    assignment = SimpleNamespace(x=object(), y=expr)

    with patch(
        "hexrays_pytools.domain.scanner.member_extractor.ScannedObject.create",
        return_value=MagicMock(),
    ):
        member = visitor._extract_member(expr, MagicMock(), 4, [assignment], ["asg"])

    assert member.offset == 4


def test_cast_wrapped_whole_object_call_does_not_invent_integer_field() -> None:
    visitor = _make_visitor()
    visitor.parents = []
    visitor._origin = 0
    variable = SimpleNamespace(op=idaapi.cot_var)
    cast = SimpleNamespace(op=idaapi.cot_cast, type=MagicMock())
    call = SimpleNamespace(op=idaapi.cot_call)
    guessed_int = MagicMock()
    guessed_int.is_integral.return_value = True
    guessed_int.get_size.return_value = 4
    with (
        patch.object(visitor, "_parse_call", return_value=guessed_int),
        patch(
            "hexrays_pytools.domain.scanner.member_extractor.ScannedObject.create",
            return_value=MagicMock(),
        ),
    ):
        member = visitor._extract_member(variable, MagicMock(), 0, [cast, call], ["cast", "call"])

    assert member is None


def test_shallow_search_visitor_is_object_downwards() -> None:
    """NewShallowSearchVisitor is a subclass of ObjectDownwardsVisitor."""
    assert issubclass(NewShallowSearchVisitor, ObjectDownwardsVisitor)
    assert issubclass(NewShallowSearchVisitor, SearchVisitor)


def test_deep_search_visitor_is_recursive_object_downwards() -> None:
    """NewDeepSearchVisitor is a subclass of RecursiveObjectDownwardsVisitor."""
    assert issubclass(NewDeepSearchVisitor, RecursiveObjectDownwardsVisitor)
    assert issubclass(NewDeepSearchVisitor, SearchVisitor)


def test_deep_return_visitor_is_subclass_of_deep_search() -> None:
    """DeepReturnVisitor is a subclass of NewDeepSearchVisitor."""
    assert issubclass(DeepReturnVisitor, NewDeepSearchVisitor)


def test_search_visitor_init_stores_origin_and_workspace() -> None:
    """SearchVisitor.__init__ stores origin + workspace + consts."""
    cfunc = MagicMock()
    obj = MagicMock()
    obj.ea = 0x1000
    workspace = MagicMock()
    consts = MagicMock()

    visitor = SearchVisitor(
        cfunc, origin=0x8, obj=obj, workspace=workspace, consts=consts
    )
    assert visitor._cfunc is cfunc
    assert visitor._init_obj is obj
    assert visitor._origin == 0x8
    assert visitor._workspace is workspace
    assert visitor._consts is consts


def test_get_member_preserves_scanned_object_for_finalize() -> None:
    """Candidates keep their ScannedObject so final types can be applied back."""
    from hexrays_pytools.domain.scanner import member_extractor

    consts = MagicMock()
    consts.void_tinfo = None
    consts.const_void_tinfo = None
    consts.const_pchar_tinfo = None
    consts.const_pvoid_tinfo = None
    visitor = _make_visitor(consts=consts)
    visitor._origin = 0x10
    visitor.parents = []
    tinfo = MagicMock()
    tinfo.dstr.return_value = "int"
    tinfo.get_size.return_value = 4
    scan_obj = MagicMock()
    scan_obj.name = "obj"

    with patch.object(member_extractor, "find_asm_address", return_value=0x401000), patch.object(
        member_extractor.ScannedObject,
        "create",
        return_value=scan_obj,
    ):
        member = visitor._get_member(4, MagicMock(), MagicMock(), tinfo=tinfo)

    assert scan_obj in member.scanned_variables
    assert member.origin == 0x10
    assert member.offset == 0x14


def test_emit_scan_hit_reports_source_and_member_offset(caplog) -> None:
    """Every scan hit is logged at DEBUG with code location and struct offset."""
    from hexrays_pytools.domain.scanner import member_extractor

    visitor = _make_visitor()
    visitor._cfunc.entry_ea = 0x401000
    visitor.parents = []
    cexpr = MagicMock()
    obj = MagicMock()
    obj.name = "this"
    member = MagicMock()
    member.offset = 0x18
    member.name = "qword_18"
    member.tinfo = "void *"

    with patch.object(member_extractor, "find_asm_address", return_value=0x401234), patch.object(
        idaapi, "get_name", return_value="Foo_method"
    ), caplog.at_level("DEBUG"):
        visitor._emit_scan_hit(cexpr, obj, member)

    assert (
        "[HexRaysPyTools][Scan Hit] Foo_method@0x401000 source=0x401234 "
        "object=this offset=0x18 member=qword_18 type=void *"
    ) in caplog.text
