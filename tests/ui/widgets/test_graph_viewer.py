"""Smoke test: StructureGraphViewer builds."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import MagicMock


def test_graph_viewer_init() -> None:
    from hexrays_pytools.ui.widgets.graph_viewer import StructureGraphViewer
    graph = MagicMock()
    gv = StructureGraphViewer("Test", graph)
    assert gv._graph is graph
