"""Test udt_builder."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.types.udt_builder import create_padding_udt_member


def test_create_padding_member_name() -> None:
    """Padding member name follows gap_<offset_in_hex> convention."""
    idaapi = __import__("idaapi")
    member = MagicMock()
    idaapi.udt_member_t.return_value = member
    idaapi.tinfo_t.return_value = MagicMock()

    create_padding_udt_member(0x10, 4)
    assert member.name == "gap_10"


def test_create_padding_member_offset() -> None:
    """Padding member offset matches input."""
    idaapi = __import__("idaapi")
    member = MagicMock()
    idaapi.udt_member_t.return_value = member
    idaapi.tinfo_t.return_value = MagicMock()

    create_padding_udt_member(0x20, 8)
    assert member.offset == 0x20


def test_create_padding_member_size() -> None:
    """Padding member size matches input."""
    idaapi = __import__("idaapi")
    member = MagicMock()
    idaapi.udt_member_t.return_value = member
    idaapi.tinfo_t.return_value = MagicMock()

    create_padding_udt_member(0x0, 16)
    assert member.size == 16
