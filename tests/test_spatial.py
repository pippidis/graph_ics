"""Spatial broad-phase completeness and exact equivalence to exhaustive checks."""

from random import Random

import pytest
from shapely.geometry import Polygon, box

from graph_ics import Edge, Graph, GrowthSettings, Node
from graph_ics.spatial import Bounds, SpatialHash, intersects


@pytest.mark.parametrize('cell_size', [0.1, 5, 50])
def test_random_envelopes_and_overflow(cell_size: float) -> None:
    rng = Random(21)
    index = SpatialHash(cell_size, max_cells=30)
    bounds: list[Bounds] = [(-1000, -1, 1000, 1), (-5, -5, 5, 5), (0, 0, 0, 0)]
    for _ in range(100):
        x, y = rng.uniform(-100, 100), rng.uniform(-100, 100)
        bounds.append((x, y, x+rng.uniform(0, 200), y+rng.uniform(0, 200)))
    for key, envelope in enumerate(bounds): index.insert(key, envelope)
    for query in bounds:
        assert index.query(query) == tuple(i for i, envelope in enumerate(bounds) if intersects(query, envelope))
    with pytest.raises(ValueError): index.insert(0, (0, 0, 1, 1))
    with pytest.raises(ValueError): index.query((1, 0, 0, 1))
    # Extremely small cells must take the bounded-memory fallback.
    tiny = SpatialHash(1e-300)
    tiny.insert(0, (0, 0, 1e100, 1e100))
    assert tiny.query((0, 0, 1, 1)) == (0,)


@pytest.mark.parametrize('seed', [0, 7, 21])
@pytest.mark.parametrize('cell_size', [1, 20, 100])
def test_complete_build_matches_brute(seed: int, cell_size: float) -> None:
    region = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)], holes=[[(40, 40), (60, 40), (60, 60), (40, 60)]])
    indexed = Graph(target_nodes=150, target_seed_nodes=3, seed=seed, outline_polygon=region, cell_size=cell_size)
    brute = Graph(target_nodes=150, target_seed_nodes=3, seed=seed, outline_polygon=region, spatial_backend='brute')
    for graph in (indexed, brute):
        graph.growth(settings=GrowthSettings(failures_per_parent=5, total_attempts=3000))
        graph.build()
    assert [(n.id, n.center.wkt) for n in indexed.nodes] == [(n.id, n.center.wkt) for n in brute.nodes]
    assert [(e.start_node.id, e.end_node.id) for e in indexed.edges] == [(e.start_node.id, e.end_node.id) for e in brute.edges]
    assert indexed.growth().attempts == brute.growth().attempts
    assert indexed.growth().status == brute.growth().status
    assert indexed.collision_stats.exact_checks < brute.collision_stats.exact_checks
    before = [(n.id, n.center.wkt) for n in indexed.nodes]
    indexed.build(force=True)
    assert [(n.id, n.center.wkt) for n in indexed.nodes] == before


def test_mixed_radii_spacing_long_edges_and_random_candidates() -> None:
    indexed = Graph(target_nodes=100, outline_polygon=box(-1000, -1000, 1000, 1000), cell_size=2)
    brute = Graph(target_nodes=100, outline_polygon=box(-1000, -1000, 1000, 1000), spatial_backend='brute')
    rng = Random(9)
    for graph in (indexed, brute):
        first = Node(-400, 0, outer_radius=50, inner_radius=20, min_edge_length=100)
        last = Node(400, 0, outer_radius=2)
        graph._accept(first)
        graph._accept(last, Edge(first, last, thickness=20))
    for _ in range(200):
        node = Node(rng.uniform(-600, 600), rng.uniform(-200, 200), outer_radius=rng.uniform(2, 80), min_edge_length=rng.uniform(0, 100))
        assert indexed.can_place_node(node) == brute.can_place_node(node)
        edge = Edge(Node(node.center.x, -500), Node(node.center.x, 500), thickness=rng.uniform(0.1, 40))
        assert indexed.can_place_edge(edge) == brute.can_place_edge(edge)
    assert not indexed.can_place_node(Node(0, 0))


def test_touching_cells_and_diagnostics() -> None:
    index = SpatialHash(10)
    index.insert(0, (-10, -10, 0, 0))
    assert index.query((0, 0, 10, 10)) == (0,)
    region = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)], holes=[[(40, 40), (60, 40), (60, 60), (40, 60)]])
    graph = Graph(outline_polygon=region, illegal_areas=box(10, 10, 20, 20))
    assert not graph.can_place_node(Node(-1, -1))
    assert not graph.can_place_node(Node(50, 50))
    assert not graph.can_place_node(Node(15, 15))
    assert graph.collision_stats.outer_boundary == 1
    assert graph.collision_stats.inner_exclusion == 2
    for size in (0, -1, float('nan')):
        with pytest.raises(ValueError): SpatialHash(size)
