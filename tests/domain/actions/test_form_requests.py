"""Test form_requests actions (ShowGraph, ShowClasses, ShowStructureBuilder)."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.actions.action import Action, HexRaysPopupAction
from hexrays_pytools.domain.actions.form_requests import (
    ShowClasses,
    ShowGraph,
    ShowStructureBuilder,
)


def test_show_graph_is_action() -> None:
    assert issubclass(ShowGraph, Action)


def test_show_graph_description_and_hotkey() -> None:
    assert ShowGraph.description == "Show graph"
    assert ShowGraph.hotkey == "G"


def test_show_graph_instantiable_and_activates() -> None:
    a = ShowGraph()
    assert a.name == "HexRaysPyTools:ShowGraph"
    a.activate(MagicMock())  # should not raise


def test_show_graph_accepts_session() -> None:
    session = MagicMock()
    a = ShowGraph(session=session)
    assert a._session is session


def test_show_classes_is_action() -> None:
    assert issubclass(ShowClasses, Action)
    assert ShowClasses.description == "Classes"
    assert ShowClasses.hotkey == "Alt+F1"


def test_show_classes_instantiable_and_activates() -> None:
    a = ShowClasses()
    assert a.name == "HexRaysPyTools:ShowClasses"
    a.activate(MagicMock())


def test_show_structure_builder_is_popup_action() -> None:
    assert issubclass(ShowStructureBuilder, HexRaysPopupAction)
    assert ShowStructureBuilder.description == "Show Structure Builder"
    assert ShowStructureBuilder.hotkey == "Alt+F8"


def test_show_structure_builder_check_returns_true() -> None:
    a = ShowStructureBuilder()
    assert a.check(MagicMock()) is True
    a.activate(MagicMock())  # should not raise
