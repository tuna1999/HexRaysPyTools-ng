"""Test ScanObject hierarchy."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.scanner.scanned_object import (
    SO_LOCAL_VARIABLE,
    ScanObject,
)


def test_scan_object_stores_fields() -> None:
    """ScanObject stores ea, name, tinfo, id."""
    tinfo = MagicMock()
    obj = ScanObject(0x1000, "foo", tinfo, SO_LOCAL_VARIABLE)
    assert obj.ea == 0x1000
    assert obj.name == "foo"
    assert obj.tinfo is tinfo
    assert obj.id == SO_LOCAL_VARIABLE


def test_is_target_matches_op() -> None:
    """is_target returns True when cexpr.op == self.id."""
    obj = ScanObject(0x1000, "foo", MagicMock(), SO_LOCAL_VARIABLE)
    cexpr = MagicMock()
    cexpr.op = SO_LOCAL_VARIABLE
    assert obj.is_target(cexpr) is True


def test_is_target_rejects_other_op() -> None:
    """is_target returns False when cexpr.op != self.id."""
    obj = ScanObject(0x1000, "foo", MagicMock(), SO_LOCAL_VARIABLE)
    cexpr = MagicMock()
    cexpr.op = 999
    assert obj.is_target(cexpr) is False
