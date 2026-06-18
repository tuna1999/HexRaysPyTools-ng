"""Test StructureGraphViewer (with offscreen Qt)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import MagicMock

from hexrays_pytools.ui.widgets.graph_viewer import StructureGraphViewer


def test_graph_viewer_init() -> None:
    graph = MagicMock()
    gv = StructureGraphViewer("Test", graph)
    assert gv._graph is graph


def test_graph_viewer_on_get_text_returns_name() -> None:
    """OnGetText returns the node's name attribute."""
    graph = MagicMock()
    gv = StructureGraphViewer("Test", graph)
    node = MagicMock()
    node.name = "MyType"
    gv.__class__.__getitem__ = lambda self, k: node  # type: ignore[assignment]
    assert gv.OnGetText(0) == "MyType"


def test_graph_viewer_on_get_text_handles_no_name() -> None:
    """OnGetText falls back to str(node) if no name attribute."""
    graph = MagicMock()
    gv = StructureGraphViewer("Test", graph)
    node = "just_a_string"
    gv.__class__.__getitem__ = lambda self, k: node  # type: ignore[assignment]
    assert gv.OnGetText(0) == "just_a_string"


def test_graph_viewer_on_hint_returns_tooltip() -> None:
    """OnHint returns the node's tooltip if present."""
    graph = MagicMock()
    gv = StructureGraphViewer("Test", graph)
    node = MagicMock()
    node.tooltip.return_value = "MyClass::vtable"
    gv.__class__.__getitem__ = lambda self, k: node  # type: ignore[assignment]
    assert gv.OnHint(0) == "MyClass::vtable"


def test_graph_viewer_on_hint_handles_no_tooltip() -> None:
    """OnHint returns empty string if no tooltip."""
    graph = MagicMock()
    gv = StructureGraphViewer("Test", graph)
    node = MagicMock(spec=[])  # no attributes
    gv.__class__.__getitem__ = lambda self, k: node  # type: ignore[assignment]
    assert gv.OnHint(0) == ""


def test_graph_viewer_on_dbl_click_changes_selection() -> None:
    """OnDblClick calls graph.change_selected with a set containing the node."""
    graph = MagicMock()
    gv = StructureGraphViewer("Test", graph)
    node = MagicMock()
    node.name = "Foo"
    gv.__class__.__getitem__ = lambda self, k: node  # type: ignore[assignment]
    gv.OnDblClick(0)
    graph.change_selected.assert_called_once()
    passed_set = graph.change_selected.call_args[0][0]
    assert node in passed_set  # the set passed contains the node itself


def test_graph_viewer_on_dbl_click_handles_no_graph_change_selected() -> None:
    """OnDblClick doesn't crash if graph has no change_selected method."""
    graph = object()  # no change_selected attribute
    gv = StructureGraphViewer("Test", graph)
    node = MagicMock()
    node.name = "Foo"
    gv.__class__.__getitem__ = lambda self, k: node  # type: ignore[assignment]
    # Should not raise
    gv.OnDblClick(0)


def test_graph_viewer_on_refresh_builds_nodes_and_edges() -> None:
    """OnRefresh adds nodes/edges from the graph."""
    graph = MagicMock()
    graph.get_nodes.return_value = {1, 2}
    graph.get_edges.return_value = [(1, 2)]
    gv = StructureGraphViewer("Test", graph)
    gv.Clear = MagicMock()  # type: ignore[assignment]
    gv.AddNode = MagicMock(return_value=42)  # type: ignore[assignment]
    gv.AddEdge = MagicMock()  # type: ignore[assignment]
    gv.OnRefresh()
    graph.get_nodes.assert_called_once()
    graph.get_edges.assert_called_once()
    assert gv.AddNode.call_count == 2
    assert gv.AddEdge.call_count == 1
