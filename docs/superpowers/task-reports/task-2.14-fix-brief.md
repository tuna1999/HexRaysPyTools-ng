# Task 2.14 Fix Brief: Restore DFS logic + fix `_calculate_edges`

## Context

The Task 2.14 implementation passed tests but has 2 CRITICAL bugs that the reviewer caught:

1. **`_calculate_edges` bug**: calls `tinfo.get_ordinal()` on the parent UDT's tinfo instead of each member's type's ordinal. The loop body never inspects `member.type` — net effect: `self.edges` is always empty for any non-self-referential UDT.

2. **DFS traversal logic missing**: the class needs `generate_final_edges_down(node)` and `generate_final_edges_up(node)` methods (recursive DFS using `visited_downward`/`visited_upward` sets). The current `get_nodes` is just a flat list comprehension over the always-empty `final_edges`.

The original at `refs/HexRaysPyTools/HexRaysPyTools/core/structure_graph.py` (lines 86-95 and 163-188) has the correct logic. Read this file first.

## Fixes Required

### Fix 1: `_calculate_edges` — use `member.type` per member

Change from:
```python
for member in udt:
    member_ord = int(tinfo.get_ordinal())  # WRONG: always the parent's ordinal
```

To:
```python
for member in udt:
    member_ord = self._get_ordinal(member.type)  # each member's type's ordinal
```

Need to add a static helper `_get_ordinal(tinfo)` that recursively unwraps pointer/array/typeref (the original `core/structure_graph.py:65-83`):

```python
@staticmethod
def _get_ordinal(tinfo) -> int:
    """Resolve the ordinal of a tinfo, unwrapping pointer/array/typeref."""
    while tinfo is not None and (tinfo.is_ptr() or tinfo.is_array()):
        tinfo = tinfo.remove_ptr_or_array() if hasattr(tinfo, "remove_ptr_or_array") else None
    if tinfo is None:
        return 0
    if tinfo.is_udt() or tinfo.is_enum():
        return int(tinfo.get_ordinal())
    if tinfo.is_typeref():
        return int(tinfo.get_ordinal())
    return 0
```

### Fix 2: Add DFS traversal methods

Add the actual DFS methods that use `visited_downward`/`visited_upward` sets:

```python
def generate_final_edges_down(self, ordinal: int) -> None:
    """DFS downward from `ordinal` adding edges to final_edges."""
    if ordinal in self.visited_downward:
        return
    self.visited_downward.add(ordinal)
    for child in self.downward_edges.get(ordinal, []):
        self.final_edges.append((ordinal, child))
        self.generate_final_edges_down(child)

def generate_final_edges_up(self, ordinal: int) -> None:
    """DFS upward from `ordinal` adding edges to final_edges."""
    if ordinal in self.visited_upward:
        return
    self.visited_upward.add(ordinal)
    for parent in self.upward_edges.get(ordinal, []):
        self.final_edges.append((parent, ordinal))
        self.generate_final_edges_up(parent)
```

Add helper to populate `downward_edges`/`upward_edges` from `self.edges`:

```python
def _build_adjacency(self) -> None:
    """Build adjacency lists from edges."""
    self.downward_edges = {}
    self.upward_edges = {}
    for src, dst in self.edges:
        self.downward_edges.setdefault(src, []).append(dst)
        self.upward_edges.setdefault(dst, []).append(src)
```

Call `_build_adjacency()` at end of `_calculate_edges`.

### Fix 3: Update `get_nodes` to drive DFS

The original's `get_nodes` triggers both DFS passes from each selected ordinal. Update:

```python
def get_nodes(self) -> set[int]:
    """Drive DFS from each selected ordinal and return the visited node set."""
    self.final_edges = []
    self.visited_downward = set()
    self.visited_upward = set()
    nodes: set[int] = set()
    for ordinal in self.ordinal_list:
        if ordinal in self.local_types:
            nodes.add(ordinal)
            self.generate_final_edges_down(ordinal)
            self.generate_final_edges_up(ordinal)
    return nodes
```

### Fix 4: Add meaningful tests

Add at least 2 tests that exercise the graph logic (with mock):

```python
def test_calculate_edges_extracts_member_type_ordinals() -> None:
    """Each member's type ordinal (not the parent's) is added as an edge."""
    idaapi = __import__("idaapi")
    g = StructureGraph()
    g.local_types = {1: LocalType(name="A"), 2: LocalType(name="B")}
    # Mock udt with a member whose type has ordinal 2
    member = MagicMock()
    member.type.is_ptr.return_value = False
    member.type.is_array.return_value = False
    member.type.is_udt.return_value = True
    member.type.get_ordinal.return_value = 2
    udt = MagicMock()
    udt.__iter__.return_value = iter([member])
    idaapi.udt_type_data_t.return_value = udt
    # Simulate _calculate_edges being called for ordinal 1
    tinfo = MagicMock()
    tinfo.is_udt.return_value = True
    tinfo.get_udt_details.return_value = True
    tinfo.get_ordinal.return_value = 1
    g._calculate_edges_for_tinfo(tinfo, udt)
    assert (1, 2) in g.edges


def test_get_nodes_triggers_dfs() -> None:
    """get_nodes() runs DFS and returns the visited set."""
    g = StructureGraph()
    g.local_types = {1: LocalType(name="A"), 2: LocalType(name="B")}
    g.ordinal_list = [1]
    g.downward_edges = {1: [2]}
    g.upward_edges = {}
    g._build_adjacency = lambda: None  # already built
    nodes = g.get_nodes()
    assert 1 in nodes
    assert 2 in nodes
    assert (1, 2) in g.final_edges
```

## Working directory
D:\re_dev_projects\ida-plugins\HexRaysPyTools

## Verification (after fixes)
```bash
PYTHONPATH=src pytest tests/domain/graph/test_structure_graph.py -v
python -m mypy --strict src/hexrays_pytools/domain/graph/structure_graph.py
python -m ruff check src/hexrays_pytools/domain/graph/ tests/domain/graph/
PYTHONPATH=src pytest  # full suite must still pass
```

## Commit
```bash
git add src/hexrays_pytools/domain/graph/structure_graph.py tests/domain/graph/test_structure_graph.py
git commit -m "fix(graph): restore DFS traversal + fix _calculate_edges to use member.type ordinal

Reviewer caught 2 CRITICAL bugs in Task 2.14:
1. _calculate_edges was using parent's ordinal instead of each member's
2. DFS traversal methods (generate_final_edges_down/up) were entirely missing
   — making the set-based B6 fix dead code

This restores the original behavior from refs/.../core/structure_graph.py.

Co-authored-by: Claude <noreply@anthropic.com>"
```

## Report
D:\re_dev_projects\ida-plugins\HexRaysPyTools\docs\superpowers\task-reports\task-2.14-fix-report.md
