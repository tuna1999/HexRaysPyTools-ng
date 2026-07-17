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

    # ------------------------------------------------------------------
    # tinfo helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _get_ordinal(tinfo: idaapi.tinfo_t) -> int:
        """Resolve the ordinal of a tinfo, unwrapping pointer/array/typeref.

        Ported from the original `core/structure_graph.py:65-83`. The
        pointer/array unwrap is required because struct members commonly
        reference other types through `Foo*` or `Foo[N]`; without unwrapping,
        `_calculate_edges` would record no edges for any pointer/array member.
        """
        while tinfo is not None and (tinfo.is_ptr() or tinfo.is_array()):
            tinfo = tinfo.remove_ptr_or_array() if hasattr(tinfo, "remove_ptr_or_array") else None
        if tinfo is None:
            return 0
        if tinfo.is_udt() or tinfo.is_enum():
            return int(tinfo.get_ordinal())
        if tinfo.is_typeref():
            return int(tinfo.get_ordinal())
        return 0

    # ------------------------------------------------------------------
    # node + edge construction
    # ------------------------------------------------------------------
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
        """Compute edges from each UDT's members.

        FIX 1 (reviewer): the previous loop body called
        ``int(tinfo.get_ordinal())`` — the *parent UDT's* ordinal — for every
        member, so every recorded edge would either be a self-loop
        (immediately skipped by the ``!= ordinal`` guard) or be skipped
        entirely because the parent's ordinal equals ``ordinal``. The net
        effect was ``self.edges`` always empty for non-self-referential UDTs.

        Correct behavior (per the original) is to resolve the *member's*
        type's ordinal via ``_get_ordinal(member.type)``.
        """
        for ordinal in self.local_types:
            tinfo = idaapi.tinfo_t()
            tinfo.get_numbered_type(idaapi.get_idati(), int(ordinal))
            if tinfo and tinfo.is_udt():
                udt = idaapi.udt_type_data_t()
                tinfo.get_udt_details(udt)
                for member in udt:
                    member_ord = self._get_ordinal(member.type)
                    if member_ord and member_ord != ordinal:
                        self.edges.append((ordinal, member_ord))
        self._build_adjacency()

    def _build_adjacency(self) -> None:
        """Build adjacency lists (downward/upward) from self.edges.

        FIX 2 (reviewer): the DFS traversal methods need adjacency lists
        keyed by source/destination. The previous code left
        ``downward_edges`` / ``upward_edges`` empty, so the DFS would never
        recurse — even after this fix's traversal methods are added.
        """
        self.downward_edges = {}
        self.upward_edges = {}
        for src, dst in self.edges:
            self.downward_edges.setdefault(src, []).append(dst)
            self.upward_edges.setdefault(dst, []).append(src)

    # ------------------------------------------------------------------
    # DFS traversal (reachable subgraph from selected ordinals)
    # ------------------------------------------------------------------
    def generate_final_edges_down(self, ordinal: int) -> None:
        """DFS downward from `ordinal`, appending (ordinal, child) edges."""
        if ordinal in self.visited_downward:
            return
        self.visited_downward.add(ordinal)
        for child in self.downward_edges.get(ordinal, []):
            self.final_edges.append((ordinal, child))
            self.generate_final_edges_down(child)

    def generate_final_edges_up(self, ordinal: int) -> None:
        """DFS upward from `ordinal`, appending (parent, ordinal) edges."""
        if ordinal in self.visited_upward:
            return
        self.visited_upward.add(ordinal)
        for parent in self.upward_edges.get(ordinal, []):
            self.final_edges.append((parent, ordinal))
            self.generate_final_edges_up(parent)

    def get_nodes(self) -> set[int]:
        """Drive DFS from each selected ordinal and return the visited set.

        FIX 3 (reviewer): the previous ``get_nodes`` was a flat list
        comprehension over ``self.final_edges``, which was always empty
        because nothing populated it. The original drives both DFS passes
        from each selected ordinal, then derives the node set from the
        union of the final-edge endpoints.
        """
        self.final_edges = []
        self.visited_downward = set()
        self.visited_upward = set()
        nodes: set[int] = set()
        for ordinal in self.ordinal_list:
            if ordinal in self.local_types:
                nodes.add(ordinal)
                self.generate_final_edges_down(ordinal)
                self.generate_final_edges_up(ordinal)
        # Union of all visited nodes; this also captures orphans (a selected
        # ordinal with no edges is added above, its neighbors are added by DFS).
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
