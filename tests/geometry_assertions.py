"""Exhaustive collision assertions independent of the indexed final validator."""
from graph_ics import Graph


def validate(graph: Graph) -> None:
    """Check complete generated scenes, including later nodes versus earlier edges."""
    for i, node in enumerate(graph.nodes):
        assert graph.in_bounds(node) and not graph.in_illegal_areas(node)
        assert all(not node.overlap(other) for other in graph.nodes[:i])
    for i, edge in enumerate(graph.edges):
        assert graph.in_bounds(edge) and not graph.in_illegal_areas(edge)
        assert all(not edge.overlap(other) for other in graph.edges[:i])
        assert all(not edge.overlap(node) for node in graph.nodes)

