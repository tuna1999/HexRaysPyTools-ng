# Task 2.14 Brief: domain/graph/structure_graph.py

## Context

Replaces `core/structure_graph.py` (191 LOC). The original used `list` for `visited_downward`/`visited_upward` (O(n²) bug B6). The rewrite uses `set`. Also fixes `logger.warn` → `logger.warning` (B5).

## Files

1. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\graph\__init__.py` (empty)
2. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\src\hexrays_pytools\domain\graph\structure_graph.py`
3. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\graph\__init__.py` (empty)
4. `D:\re_dev_projects\ida-plugins\HexRaysPyTools\tests\domain\graph\test_structure_graph.py`

## Content (verbatim)

### `src/hexrays_pytools/domain/graph/structure_graph.py`

```python
"""Local-type dependency graph for the Structure Graph viewer.

Replaces `core/structure_graph.py`. The original used `list` for visited
sets during DFS (O(n²) membership check). This rewrite uses `set` for
O(1) membership. Also fixes `logger.warn` → `logger.warning`.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any

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
        for ordinal, lt in self.local_types.items():
            tinfo = idaapi.tinfo_t()
            tinfo.get_numbered_type(idaapi.get_idati(), int(ordinal))
            if tinfo and tinfo.is_udt():
                udt = idaapi.udt_type_data_t()
                tinfo.get_udt_details(udt)
                for member in udt:
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
```

### `tests/domain/graph/test_structure_graph.py`

```python
"""Test StructureGraph."""
from hexrays_pytools.domain.graph.structure_graph import StructureGraph, LocalType


def test_local_type_default_fields() -> None:
    """LocalType has empty defaults for collections."""
    lt = LocalType(name="Foo")
    assert lt.members_ordinals == []
    assert lt.is_selected is False


def test_structure_graph_init_empty() -> None:
    """StructureGraph with no ordinals has empty collections."""
    g = StructureGraph()
    assert g.local_types == {}
    assert g.edges == []
    assert g.final_edges == []


def test_visited_sets_are_sets() -> None:
    """visited_downward and visited_upward are sets (not lists)."""
    g = StructureGraph()
    assert isinstance(g.visited_downward, set)
    assert isinstance(g.visited_upward, set)


def test_get_nodes_empty_graph() -> None:
    """get_nodes returns empty set when final_edges is empty."""
    g = StructureGraph()
    assert g.get_nodes() == set()


def test_get_edges_empty_graph() -> None:
    """get_edges returns empty list when final_edges is empty."""
    g = StructureGraph()
    assert g.get_edges() == []


def test_change_selected_updates_ordinal_list() -> None:
    """change_selected filters ordinal_list to the selected set."""
    g = StructureGraph()
    g.local_types[1] = LocalType(name="A")
    g.local_types[2] = LocalType(name="B")
    g.local_types[3] = LocalType(name="C")
    g.change_selected({1, 3})
    assert g.ordinal_list == [1, 3]
    assert g.local_types[1].is_selected is True
    assert g.local_types[2].is_selected is False
    assert g.local_types[3].is_selected is True
```

## Verification

```bash
cd D:\re_dev_projects\ida-plugins\HexRaysPyTools
PYTHONPATH=src pytest tests/domain/graph/test_structure_graph.py -v
python -m mypy --strict src/hexrays_pytools/domain/graph/structure_graph.py
python -m ruff check src/hexrays_pytools/domain/graph/ tests/domain/graph/
```

## Commit

```bash
git add src/hexrays_pytools/domain/graph/ tests/domain/graph/
git commit -m "feat(graph): add StructureGraph (set-based DFS, fixes B6 O(n²) bug)"
```

## Report

`D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-2.14-report.md`