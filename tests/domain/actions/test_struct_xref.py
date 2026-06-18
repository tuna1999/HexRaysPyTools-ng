"""Test struct_xref action (FindFieldXrefs)."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.action import HexRaysXrefAction
from hexrays_pytools.domain.actions.struct_xref import FindFieldXrefs


def test_find_field_xrefs_is_xref_action() -> None:
    assert issubclass(FindFieldXrefs, HexRaysXrefAction)
    assert FindFieldXrefs.description == "Field Xrefs"
    assert FindFieldXrefs.hotkey == "Ctrl+X"


def test_find_field_xrefs_instantiable_and_activates() -> None:
    a = FindFieldXrefs()
    assert a.name == "HexRaysPyTools:FindFieldXrefs"
    assert a.check(MagicMock()) is True
    a.activate(MagicMock())


def test_find_field_xrefs_accepts_session() -> None:
    session = MagicMock()
    a = FindFieldXrefs(session=session)
    assert a._session is session
