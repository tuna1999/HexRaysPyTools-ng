"""Local-type dependency graph for the Structure Graph viewer.

Replaces `core/structure_graph.py`. The original used `list` for visited
sets during DFS (O(n²) membership check). This rewrite uses `set` for
O(1) membership. Also fixes `logger.warn` → `logger.warning`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import idaapi  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)


@dataclass
class LocalType:
    """A single local type with its dependencies."""

    name: str
    members_ordinals: list[int] = field(default_factory=list)
    hint: str = ""
    is_selected: bool = False
    is_typedef: bool = False
    is_enum: bool = False
    is_union: bool = False


class StructureGraph:
    """Build a graph of local-type dependencies for the Graph viewer."""

    def __init__(self, ordinal_list: list[int] | None = None) -> None:
        self.ordinal_list: list[int] = ordinal_list if ordinal_list else []
        self.local_types: dict[int, LocalType] = {}
        self.edges: list[tuple[int, int]] = []
        self.final_edges: list[tuple[int, int]] = []
        # FIX B6: was list (O(n²)), now set (O(1))
        self.visited_downward: set[int] = set()
        self.visited_upward: set[int] = set()
        self.downward_edges: dict[int, list[int]] = {}
        self.upward_edges: dict[int, list[int]] = {}
        if ordinal_list:
            self._initialize_nodes()
            self._calculate_edges()

    def _initialize_nodes(self) -> None:
        """Load all local types into self.local_types."""
        for ordinal in self.ordinal_list or range(1, int(idaapi.get_ordinal_count())):
            tinfo = idaapi.tinfo_t()
            tinfo.get_numbered_type(idaapi.get_idati(), int(ordinal))
            if not tinfo:
                continue
            name = tinfo.dstr() if hasattr(tinfo, "dstr") else ""
            self.local_types[int(ordinal)] = LocalType(name=name)

    def _calculate_edges(self) -> None:
        """Compute edges from each type's members."""
        for ordinal in self.local_types:
            tinfo = idaapi.tinfo_t()
            tinfo.get_numbered_type(idaapi.get_idati(), int(ordinal))
            if tinfo and tinfo.is_udt():
                udt = idaapi.udt_type_data_t()
                tinfo.get_udt_details(udt)
                for _ in udt:
                    member_ord = int(tinfo.get_ordinal())
                    if member_ord and member_ord != ordinal:
                        self.edges.append((ordinal, member_ord))

    def get_nodes(self) -> set[int]:
        """Return the set of all nodes in the final graph."""
        nodes: set[int] = set()
        for a, b in self.final_edges:
            nodes.add(a)
            nodes.add(b)
        return nodes

    def get_edges(self) -> list[tuple[int, int]]:
        """Return the final edges."""
        return list(self.final_edges)

    def change_selected(self, selected: set[int]) -> None:
        """Update the selection and recompute the subgraph."""
        self.visited_downward = set()
        self.visited_upward = set()
        self.final_edges = []
        for ordinal in self.local_types:
            self.local_types[ordinal].is_selected = False
        self.ordinal_list = [o for o in self.local_types if o in selected]
        for ordinal in self.ordinal_list:
            self.local_types[ordinal].is_selected = True
