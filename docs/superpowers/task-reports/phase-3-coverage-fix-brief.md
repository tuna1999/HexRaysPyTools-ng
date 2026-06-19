# Phase 3 coverage fix: add tests for graph_viewer methods

## Context

Phase 3 widgets have 74.71% coverage (below 80% gate). The UI methods
(OnCreate, _init_ui) genuinely need a Qt event loop. But the graph_viewer's
OnRefresh, OnGetText, OnHint, OnDblClick methods are plain methods
that can be tested with mock graph data.

## Files

Modify: `tests/ui/widgets/test_graph_viewer.py`

## Test file content

```python
"""Test StructureGraphViewer (with offscreen Qt)."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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
    gv.__setitem__ = lambda k, v: None  # base class normally sets via id; mock
    # Patch __getitem__ to return our node
    gv.__class__.__getitem__ = lambda self, k: node
    assert gv.OnGetText(0) == "MyType"


def test_graph_viewer_on_get_text_handles_no_name() -> None:
    """OnGetText falls back to str(node) if no name attribute."""
    graph = MagicMock()
    gv = StructureGraphViewer("Test", graph)
    node = "just_a_string"
    gv.__class__.__getitem__ = lambda self, k: node
    assert gv.OnGetText(0) == "just_a_string"


def test_graph_viewer_on_hint_returns_tooltip() -> None:
    """OnHint returns the node's tooltip if present."""
    graph = MagicMock()
    gv = StructureGraphViewer("Test", graph)
    node = MagicMock()
    node.tooltip.return_value = "MyClass::vtable"
    gv.__class__.__getitem__ = lambda self, k: node
    assert gv.OnHint(0) == "MyClass::vtable"


def test_graph_viewer_on_hint_handles_no_tooltip() -> None:
    """OnHint returns empty string if no tooltip."""
    graph = MagicMock()
    gv = StructureGraphViewer("Test", graph)
    node = MagicMock(spec=[])  # no attributes
    gv.__class__.__getitem__ = lambda self, k: node
    assert gv.OnHint(0) == ""


def test_graph_viewer_on_dbl_click_changes_selection() -> None:
    """OnDblClick calls graph.change_selected with the node's name."""
    graph = MagicMock()
    gv = StructureGraphViewer("Test", graph)
    node = MagicMock()
    node.name = "Foo"
    gv.__class__.__getitem__ = lambda self, k: node
    gv.OnDblClick(0)
    graph.change_selected.assert_called_once()
    call_args = graph.change_selected.call_args
    assert "Foo" in call_args[0][0]  # the set passed contains "Foo"


def test_graph_viewer_on_dbl_click_handles_no_graph_change_selected() -> None:
    """OnDblClick doesn't crash if graph has no change_selected method."""
    graph = object()  # no change_selected attribute
    gv = StructureGraphViewer("Test", graph)
    node = MagicMock()
    node.name = "Foo"
    gv.__class__.__getitem__ = lambda self, k: node
    # Should not raise
    gv.OnDblClick(0)


def test_graph_viewer_on_refresh_builds_nodes_and_edges() -> None:
    """OnRefresh adds nodes/edges from the graph."""
    graph = MagicMock()
    graph.get_nodes.return_value = {1, 2}
    graph.get_edges.return_value = [(1, 2)]
    gv = StructureGraphViewer("Test", graph)
    gv.Clear = MagicMock()
    gv.AddNode = MagicMock(return_value=42)
    gv.AddEdge = MagicMock()
    gv.OnRefresh()
    graph.get_nodes.assert_called_once()
    graph.get_edges.assert_called_once()
    assert gv.AddNode.call_count == 2
    assert gv.AddEdge.call_count == 1
```

Add `from unittest.mock import MagicMock` to imports.

## Verification

```bash
PYTHONPATH=src pytest tests/ui/widgets/test_graph_viewer.py -v
python -m mypy --strict src/hexrays_pytools/ui/widgets/graph_viewer.py
python -m ruff check src/hexrays_pytools/ui/widgets/graph_viewer.py tests/ui/widgets/test_graph_viewer.py
PYTHONPATH=src pytest  # check full suite + coverage
```

## Commit

```bash
git add tests/ui/widgets/test_graph_viewer.py
git commit -m "test(ui): add coverage for graph_viewer methods (boost Phase 3 to gate)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\phase-3-coverage-fix-report.md`