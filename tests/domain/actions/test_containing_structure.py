"""Test SelectContainingStructure/ResetContainingStructure actions."""
from hexrays_pytools.domain.actions.containing_structure import (
    ResetContainingStructure,
    SelectContainingStructure,
)


def test_select_containing_init() -> None:
    a = SelectContainingStructure()
    assert a.description == "Select Containing Structure"


def test_reset_containing_init() -> None:
    a = ResetContainingStructure()
    assert a.description == "Reset Containing Structure"


def test_both_can_instantiate() -> None:
    SelectContainingStructure()
    ResetContainingStructure()
