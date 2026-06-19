"""Test swap_if."""
from hexrays_pytools.domain.ctree.swap_if import swap_if_then_else


def test_swap_if_none_returns_false() -> None:
    assert swap_if_then_else(None) is False
