"""Test virtual_table action wrapper (CreateVtableAction).

Note: the registered action is `CreateVtable` in struct_creation.py (per the
ActionRegistry). This `CreateVtableAction` is a naming-parity alias retained
per the design spec's `actions/virtual_table.py` mapping; it is not in the
27-action registry.
"""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.action import Action
from hexrays_pytools.domain.actions.virtual_table import CreateVtableAction


def test_create_vtable_action_is_action() -> None:
    assert issubclass(CreateVtableAction, Action)
    assert CreateVtableAction.description == "Create Virtual Table"
    assert CreateVtableAction.hotkey == "V"


def test_create_vtable_action_instantiable_and_activates() -> None:
    a = CreateVtableAction()
    assert a.name == "HexRaysPyTools:CreateVtableAction"
    a.activate(MagicMock())


def test_create_vtable_action_accepts_session() -> None:
    session = MagicMock()
    a = CreateVtableAction(session=session)
    assert a._session is session
