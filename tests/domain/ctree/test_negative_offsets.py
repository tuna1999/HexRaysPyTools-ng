"""Test negative_offsets stubs."""
from hexrays_pytools.domain.ctree.negative_offsets import (
    can_select_containing,
    reset_containing_structure,
    select_containing_structure,
)


def test_select_stub() -> None:
    """No hx_view -> False regardless of the session store contents."""
    assert select_containing_structure(None, {}) is False
    assert select_containing_structure(None, {0x401000: {}}) is False


def test_reset_stub() -> None:
    assert reset_containing_structure(None) is False


def test_can_select_containing_no_candidates() -> None:
    """Empty store / unknown entry_ea -> not selectable."""
    assert can_select_containing(None, {}) is False
