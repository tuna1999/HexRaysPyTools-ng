"""Test rename stubs (6 functions)."""
from hexrays_pytools.domain.ctree.rename import (
    propagate_name,
    rename_inside,
    rename_member_from_function_name,
    rename_other,
    rename_outside,
    rename_using_assert,
)


def test_all_rename_stubs_return_false() -> None:
    assert rename_other(None) is False
    assert rename_inside(None) is False
    assert rename_outside(None) is False
    assert rename_member_from_function_name(None) is False
    assert rename_using_assert(None) is False
    assert propagate_name(None) is False
