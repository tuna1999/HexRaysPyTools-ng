"""Test negative_offsets stubs."""
from hexrays_pytools.domain.ctree.negative_offsets import (
    reset_containing_structure,
    select_containing_structure,
)


def test_select_stub() -> None:
    assert select_containing_structure(None) is False


def test_reset_stub() -> None:
    assert reset_containing_structure(None) is False
