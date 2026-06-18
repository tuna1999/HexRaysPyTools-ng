"""Test tinfo_utils."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.types.tinfo_utils import get_nice_pointed_object, get_ordinal


def test_get_ordinal_for_udt() -> None:
    """get_ordinal returns the ordinal for a UDT."""
    tinfo = __import__("idaapi").tinfo_t.return_value
    tinfo.is_udt.return_value = True
    tinfo.get_ordinal.return_value = 42
    assert get_ordinal(tinfo) == 42


def test_get_ordinal_for_non_udt() -> None:
    """get_ordinal returns 0 for non-UDT types."""
    tinfo = __import__("idaapi").tinfo_t.return_value
    tinfo.is_udt.return_value = False
    tinfo.is_enum.return_value = False
    tinfo.is_typeref.return_value = False
    assert get_ordinal(tinfo) == 0


def test_get_nice_pointed_object_strips_p() -> None:
    """get_nice_pointed_object returns the non-P-prefixed type if it exists."""
    idaapi = __import__("idaapi")
    inner = MagicMock()
    inner.dstr.return_value = "PFoo"
    tinfo = MagicMock()
    tinfo.get_pointed_object.return_value = inner
    idaapi.get_short_name.return_value = "PFoo"
    # Make get_named_type succeed for "Foo"
    tinfo2 = MagicMock()
    tinfo2.get_named_type.return_value = True
    idaapi.tinfo_t.return_value = tinfo2
    result = get_nice_pointed_object(tinfo)
    # Should be the named tinfo, not the inner
    assert result is not None
