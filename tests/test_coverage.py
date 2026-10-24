"""Population quotas, bounded reseeding, and safe incremental loop events."""

from dataclasses import replace

import networkx as nx
import pytest
from shapely.geometry import MultiPolygon, Polygon, box

from graph_ics import ConstantField, CoverageSettings, Graph, GrowthSettings, SpatialFields
from tests.geometry_assertions import validate


def signature(graph: Graph) -> tuple[object, ...]:
    return (tuple((n.id, n.center.wkt) for n in graph.nodes), tuple((e.start_node.id, e.end_node.id) for e in graph.edges))


def test_clipped_density_integral_and_empty_area() -> None:
    shape = Polygon(box(0, 0, 100, 100).exterior.coords, holes=[box(40, 40, 60, 60).exterior.coords])
    graph = Graph(outline_polygon=shape, illegal_areas=box(0, 0, 10, 100), fields=SpatialFields(density=ConstantField(0.01)), target_nodes=10)
    run = graph.growth(settings=GrowthSettings(coverage=CoverageSettings(tile_size=17)))
    report = run.coverage_report()
    assert report.expected_nodes == pytest.approx(86)
    graph.build()
    assert run.coverage_report().actual_nodes == len(graph.nodes)
    assert run.coverage_report().residual_underfill > 70
    covered = Graph(illegal_areas=box(0, 0, 100, 100))
    run = covered.growth(settings=GrowthSettings(seed_attempts=2, coverage=CoverageSettings()))
    covered.build()
    assert run.coverage_report().usable_tiles == 0 and not covered.nodes


def test_reseeding_disconnected_masks_is_bounded() -> None:
    region = MultiPolygon([box(0, 0, 25, 25), box(100, 0, 125, 25)])
    settings = GrowthSettings(failures_per_parent=3, total_attempts=800, coverage=CoverageSettings(tile_size=10, reseed_attempts=40))
    graph = Graph(outline_polygon=region, target_nodes=1000, seed=7)
    graph.growth(settings=settings)
    graph.build()
    assert any(n.center.x < 25 for n in graph.nodes) and any(n.center.x > 100 for n in graph.nodes)
    assert graph.growth().reseed_attempts <= 40 and graph.growth().attempts <= 800
    assert graph.growth().coverage_report().residual_underfill > 0
    validate(graph)
    single = Graph(outline_polygon=region, target_nodes=1000, seed=7)
    single.growth(settings=replace(settings, coverage=CoverageSettings(allow_components=False)))
    single.build()
    assert nx.number_connected_components(single.to_networkx()) == 1
    assert single.growth().reseeds == 0


@pytest.mark.parametrize('batch', [1, 13, 1000])
def test_loops_coverage_events_and_rebuild(batch: int) -> None:
    settings = GrowthSettings(failures_per_parent=5, max_degree=4, loop_attempts=800, loop_distance=30, coverage=CoverageSettings(tile_size=20, reseed_attempts=30))
    first = Graph(target_nodes=80, target_seed_nodes=3, target_extra_edges=10, seed=7)
    second = Graph(target_nodes=80, target_seed_nodes=3, target_extra_edges=10, seed=7, spatial_backend='brute')
    first.growth(settings=settings)
    first.build()
    run = second.growth(settings=settings)
    events = 0
    while not run.done:
        result = run.step(batch)
        assert result.attempts <= batch
        events += len(result.loop_additions)
        for edge in result.loop_additions: assert second.nx_graph.has_edge(edge.start_node.id, edge.end_node.id)
    assert signature(first) == signature(second)
    assert events == run.loops_added > 0
    assert run.step().loop_additions == ()
    assert run.loop_attempts <= settings.loop_attempts
    assert all(degree <= 4 for _, degree in second.to_networkx().degree())
    edges = [frozenset((edge.start_node.id, edge.end_node.id)) for edge in second.edges]
    assert len(edges) == len(set(edges)) and all(len(pair) == 2 for pair in edges)
    assert len(nx.cycle_basis(second.to_networkx())) == run.loops_added
    validate(second)
    lineage = second.parents.copy()
    before = signature(second)
    second.build(force=True)
    assert signature(second) == before and second.parents == lineage
    exported = second.to_networkx()
    exported.clear()
    assert second.nx_graph.number_of_nodes() == len(second.nodes) == 79


def test_loop_budget_cancellation_and_no_bridging() -> None:
    graph = Graph(target_nodes=30, target_seed_nodes=3, target_extra_edges=1000, seed=0)
    run = graph.growth(settings=GrowthSettings(loop_attempts=3))
    while not run._loop_phase and not run.done: run.step(1)
    before = nx.number_connected_components(graph.to_networkx())
    graph.build()
    assert run.loop_attempts == 3 and run.loop_stop == 'loop_attempt_budget_exhausted'
    assert nx.number_connected_components(graph.to_networkx()) == before
    graph = Graph(target_nodes=10, target_extra_edges=10, seed=0)
    run = graph.growth(settings=GrowthSettings(total_attempts=1))
    graph.build()
    assert run.attempts == 1 and run.loops_added == 0
    graph = Graph(target_nodes=20, target_extra_edges=100, seed=0)
    run = graph.growth()
    while not run._loop_phase and not run.done: run.step(1)
    state = signature(graph)
    run.cancel()
    assert run.step().attempts == 0 and signature(graph) == state


def test_invalid_coverage_options() -> None:
    with pytest.raises(ValueError): CoverageSettings(tile_size=0)
    with pytest.raises(ValueError): CoverageSettings(reseed_attempts=-1)
    with pytest.raises(ValueError): GrowthSettings(loop_distance=float('inf'))
    with pytest.raises(ValueError): GrowthSettings(max_degree=0)
    with pytest.raises(ValueError): Graph().growth(settings=GrowthSettings(coverage=CoverageSettings(narrow_weight=2)))


def test_weighted_quotas_and_loop_length_limit() -> None:
    graph = Graph(target_nodes=100)
    tracker = graph.growth(settings=GrowthSettings(coverage=CoverageSettings(tile_size=20, boundary_band=15, boundary_weight=3))).coverage
    assert tracker is not None
    assert sum(t.expected for t in tracker.tiles) == pytest.approx(100)
    assert tracker.lookup[0, 0].expected > tracker.lookup[2, 2].expected
    graph = Graph(target_nodes=40, target_extra_edges=10, extra_edge_elongation_factor=0.01, seed=7)
    run = graph.growth(settings=GrowthSettings(loop_attempts=50))
    graph.build()
    assert all(edge.length <= graph.edge_length_max*0.01 for edge in graph.edges if graph.nx_graph[edge.start_node.id][edge.end_node.id].get('loop'))
    assert run.loop_attempts <= 50
