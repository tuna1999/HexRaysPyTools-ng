"""Test StructureGraph."""
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
