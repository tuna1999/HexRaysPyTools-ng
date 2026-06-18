"""Structure Graph viewer widget — graph of type dependencies."""
from __future__ import annotations

from typing import Any

import idaapi  # type: ignore[import-not-found]


class StructureGraphViewer(idaapi.GraphViewer):  # type: ignore[misc]
    """Graph viewer for structure_graph.StructureGraph."""

    def __init__(self, title: str, graph: Any) -> None:
        super().__init__(title)
        self._graph = graph

    def OnRefresh(self) -> None:  # noqa: N802, N806
        self.Clear()
        nodes = self._graph.get_nodes() if hasattr(self._graph, "get_nodes") else set()
        node_to_id: dict[Any, int] = {}
        for node in nodes:
            nid = self.AddNode(node)
            node_to_id[node] = nid
        for src, dst in self._graph.get_edges() if hasattr(self._graph, "get_edges") else []:
            if src in node_to_id and dst in node_to_id:
                self.AddEdge(node_to_id[src], node_to_id[dst])

    def OnGetText(self, node_id: int) -> str:  # noqa: N802, N806
        node = self[node_id]
        if hasattr(node, "name"):
            return str(node.name)
        return str(node)

    def OnHint(self, node_id: int) -> str:  # noqa: N802, N806
        node = self[node_id]
        if hasattr(node, "tooltip"):
            return str(node.tooltip())
        return ""

    def OnDblClick(self, node_id: int) -> None:  # noqa: N802, N806
        node = self[node_id]
        if hasattr(self._graph, "change_selected") and hasattr(node, "name"):
            self._graph.change_selected({node})
            self.Refresh()
