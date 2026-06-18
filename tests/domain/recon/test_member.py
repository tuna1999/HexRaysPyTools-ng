"""Test AbstractMember / Member / VoidMember."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.recon.member import AbstractMember, Member, VoidMember


def test_abstract_member_default_fields() -> None:
    """AbstractMember has sensible defaults."""
    m = AbstractMember(offset=0x10)
    assert m.tinfo is None
    assert m.name == ""
    assert m.enabled is True
    assert m.size == 0


def test_abstract_member_size_from_tinfo() -> None:
    """size property reads from tinfo.get_size()."""
    m = AbstractMember(offset=0)
    tinfo = MagicMock()
    tinfo.get_size.return_value = 4
    m.tinfo = tinfo
    assert m.size == 4


def test_member_eq_merges_scanned_variables() -> None:
    """Two AbstractMembers with same offset+size are equal and merge scanned_variables."""
    a = AbstractMember(offset=0x10)
    a.scanned_variables = {1, 2}
    b = AbstractMember(offset=0x10)
    b.scanned_variables = {3}
    assert a == b
    assert a.scanned_variables == {1, 2, 3}


def test_member_lt_compares_offset() -> None:
    """AbstractMember orders by offset."""
    a = AbstractMember(offset=0x10)
    b = AbstractMember(offset=0x20)
    assert a < b


def test_void_member_wildcard_type_match() -> None:
    """VoidMember.type_equals_to always returns True."""
    v = VoidMember(offset=0)
    assert v.type_equals_to("anything") is True


def test_member_class_is_subclass() -> None:
    """Member is a subclass of AbstractMember."""
    m = Member(offset=0, name="x")
    assert isinstance(m, AbstractMember)
    assert m.name == "x"
