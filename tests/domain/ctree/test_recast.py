"""Test recast stubs."""
from hexrays_pytools.domain.ctree.recast import recast_item_left, recast_item_right


def test_recast_left_stub_returns_false() -> None:
    assert recast_item_left(None) is False


def test_recast_right_stub_returns_false() -> None:
    assert recast_item_right(None) is False
