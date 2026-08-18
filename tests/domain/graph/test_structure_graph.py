"""Test StructureGraph."""
from unittest.mock import MagicMock

from hexrays_pytools.domain.graph.structure_graph import LocalType, StructureGraph


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


def test_calculate_edges_extracts_member_type_ordinals() -> None:
    """Each member's type ordinal (not the parent's) is added as an edge.

    Regression for reviewer CRITICAL bug #1: previously the loop body called
    ``int(tinfo.get_ordinal())`` on the *parent* UDT's tinfo, so it always
    recorded either a self-loop or nothing. The fix resolves
    ``_get_ordinal(member.type)`` per member.
    """
    idaapi = __import__("idaapi")
    g = StructureGraph()
    g.local_types = {1: LocalType(name="A"), 2: LocalType(name="B")}

    # Member whose type resolves to ordinal 2 (a UDT).
    member = MagicMock()
    member.type.is_ptr.return_value = False
    member.type.is_array.return_value = False
    member.type.is_udt.return_value = True
    member.type.is_enum.return_value = False
    member.type.is_typeref.return_value = False
    member.type.get_ordinal.return_value = 2

    udt = MagicMock()
    udt.__iter__.return_value = iter([member])
    idaapi.udt_type_data_t.return_value = udt

    # Parent tinfo: ordinal 1, is_udt -> True.
    tinfo = MagicMock()
    tinfo.is_udt.return_value = True
    tinfo.get_udt_details.return_value = True
    tinfo.get_ordinal.return_value = 1  # would be the OLD bug value
    idaapi.tinfo_t.return_value = tinfo

    g._calculate_edges()
    assert (1, 2) in g.edges
    # Self-loop guard: never add (ordinal, ordinal).
    assert (1, 1) not in g.edges
    # Adjacency built: child 2 reachable downward from 1.
    assert g.downward_edges.get(1) == [2]
    assert g.upward_edges.get(2) == [1]


def test_get_ordinal_unwraps_pointer_in_place() -> None:
    """remove_ptr_or_array returns bool in IDA 9; never replace tinfo with it."""
    tinfo = MagicMock()
    tinfo.is_ptr.side_effect = [True, False]
    tinfo.is_array.return_value = False
    tinfo.remove_ptr_or_array.return_value = True
    tinfo.is_udt.return_value = True
    tinfo.is_enum.return_value = False
    tinfo.is_typeref.return_value = False
    tinfo.get_ordinal.return_value = 7

    assert StructureGraph._get_ordinal(tinfo) == 7
    tinfo.remove_ptr_or_array.assert_called_once_with()


def test_get_nodes_triggers_dfs() -> None:
    """get_nodes() runs DFS and returns the union of visited nodes.

    Regression for reviewer CRITICAL bug #2: the previous get_nodes was a
    flat comprehension over an always-empty ``final_edges``, so it returned
    ``set()`` regardless of the underlying graph.
    """
    g = StructureGraph()
    g.local_types = {1: LocalType(name="A"), 2: LocalType(name="B")}
    g.ordinal_list = [1]
    g.downward_edges = {1: [2]}
    g.upward_edges = {2: [1]}
    nodes = g.get_nodes()
    assert 1 in nodes
    assert 2 in nodes
    assert (1, 2) in g.final_edges


def test_generate_final_edges_down_visits_each_node_once() -> None:
    """DFS terminates on cycles and does not revisit nodes.

    Diamond 1 -> 2 -> 3 and 1 -> 3. With set-based visited, node 3 is
    visited exactly once (the original used list-based membership which
    would also terminate, but O(n) per check — this is the B6 fix).
    """
    g = StructureGraph()
    g.downward_edges = {1: [2, 3], 2: [3], 3: []}
    g.upward_edges = {1: [], 2: [1], 3: [1, 2]}
    g.visited_downward = set()
    g.final_edges = []
    g.generate_final_edges_down(1)
    # 3 visited exactly once despite two incoming edges.
    assert g.visited_downward == {1, 2, 3}
    # Both edges (1,2) and (1,3) emitted; (2,3) emitted once.
    assert (1, 2) in g.final_edges
    assert (1, 3) in g.final_edges
    assert (2, 3) in g.final_edges
    assert g.final_edges.count((2, 3)) == 1
