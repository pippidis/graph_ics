"""Cleanup, bounded refill, and junction quality regression tests."""
from math import cos, sin, radians
from typing import Literal
import pytest
from graph_ics import AngleSettings, CoverageSettings, Edge, Graph, GrowthSettings, GrowthStatus, Node
from graph_ics.quality import incident_angle


def signature(graph: Graph) -> tuple[object, ...]:
    return (tuple((n.id, n.center.x, n.center.y) for n in graph.nodes), tuple((e.start_node.id, e.end_node.id) for e in graph.edges))


@pytest.mark.parametrize('rotation', [0, 45, 90, 180, 270])
@pytest.mark.parametrize('angle', [0, 29, 30, 60, 90, 180])
def test_angles(rotation: float, angle: float) -> None:
    center = Node(0, 0)
    first = Node(10*cos(radians(rotation)), 10*sin(radians(rotation)))
    second = Node(20*cos(radians(rotation+angle)), 20*sin(radians(rotation+angle)), outer_radius=3)
    assert incident_angle(center, first, second) == pytest.approx(angle)
    settings = AngleSettings(minimum=30, preferred=60, penalty=0.8)
    assert settings.acceptance(angle) == pytest.approx(0 if angle < 30 else 1 if angle >= 60 else 1-0.8*(60-angle)/30)


@pytest.mark.parametrize('minimum,preferred,penalty', [(-1, 60, 1), (181, 0, 0), (60, 30, 1), (0, 200, 0), (0, 0, -1), (0, 60, 2), (float('nan'), 60, 1)])
def test_invalid_angles(minimum: float, preferred: float, penalty: float) -> None:
    with pytest.raises(ValueError): AngleSettings(minimum, preferred, penalty)


def test_cleanup_supplied_nodes_and_cancel() -> None:
    graph = Graph(input_nodes=[Node(20, 20), Node(80, 80)], target_nodes=2)
    run = graph.growth(settings=GrowthSettings(coverage=CoverageSettings(), refill_passes=3))
    ids = tuple(n.id for n in graph.nodes)
    result = run.cancel()
    assert result.removed_node_ids == ids and not graph.nodes
    assert result.completion is not None and result.completion.nodes == 0
    assert run.refill_attempts == 0 and not graph.parents and not graph._objects
    assert run.coverage_report().actual_nodes == 0
    assert graph._index.query((0, 0, 100, 100)) == ()
    assert run.cancel().removed_node_ids == ()
    assert run.step().completion is None


def test_cleanup_preserves_components_and_ids() -> None:
    graph = Graph(target_nodes=5, input_nodes=[Node(10, 10), Node(70, 70), Node(90, 10)])
    roots = graph.nodes
    for root in roots[:2]:
        child = Node(root.center.x+10, root.center.y)
        graph._accept(child, Edge(root, child))
    removed = graph._remove_isolated_nodes()
    assert removed == (roots[2].id,)
    assert all(degree == 1 for _, degree in graph.to_networkx().degree())
    child = Node(40, 40)
    graph._accept(child)
    assert child.id == 'node_000005'
    assert len(graph._objects) == 7


@pytest.mark.parametrize('batch', [1, 19, 1000])
@pytest.mark.parametrize('backend', ['hash', 'brute'])
def test_quality_replay_and_bounds(batch: int, backend: Literal['hash', 'brute']) -> None:
    settings = GrowthSettings(coverage=CoverageSettings(tile_size=20, reseed_attempts=30), failures_per_parent=5,
                              refill_passes=2, refill_attempts=100, total_attempts=2000, loop_attempts=100)
    def make(kind: Literal['hash', 'brute']) -> Graph:
        return Graph(target_nodes=65, target_seed_nodes=12, target_extra_edges=4, seed=7, angles=AngleSettings(30, 60, 0.8), spatial_backend=kind)
    expected = make('hash')
    expected.growth(settings=settings)
    expected.build()
    graph = make(backend)
    run = graph.growth(settings=settings)
    replay: set[str] = set()
    completions = 0
    while not run.done:
        result = run.step(batch)
        assert result.attempts <= batch
        replay.update(a.node.id for a in result.additions)
        replay.difference_update(result.removed_node_ids)
        assert replay == {n.id for n in graph.nodes}
        completions += result.completion is not None
    assert completions == 1 and signature(graph) == signature(expected)
    assert run.quality_report() == expected.growth().quality_report()
    assert run.refill_attempts <= 100 and run.refill_passes <= 2 and run.attempts <= 2000
    assert run.removed_nodes > 0 and run.refill_attempts > 0
    assert all(degree > 0 for _, degree in graph.to_networkx().degree())
    report = run.quality_report()
    assert report.minimum_angle is not None and report.minimum_angle >= 30-1e-9
    assert run.coverage_report().actual_nodes == len(graph.nodes)
    before = signature(graph)
    graph.build(force=True)
    assert signature(graph) == before


def test_disabled_penalty_preserves_rng_and_cleanup_opt_out() -> None:
    graphs = [Graph(target_nodes=30, target_seed_nodes=4, seed=3, angles=angles) for angles in (AngleSettings(), AngleSettings(0, 90, 0))]
    for graph in graphs:
        graph.growth(settings=GrowthSettings(remove_isolated_nodes=False))
        graph.build()
    assert signature(graphs[0]) == signature(graphs[1]) and graphs[0]._rng.getstate() == graphs[1]._rng.getstate()
    assert len(graphs[0].nodes) == 30
    single = Graph(target_nodes=1)
    result = single.growth().step()
    assert result.status == GrowthStatus.CLEANED_UNDERFILLED and not single.nodes


def test_both_endpoints_and_deterministic_public_check() -> None:
    graph = Graph(target_nodes=4, input_nodes=[Node(20, 20), Node(60, 20)], angles=AngleSettings(60))
    first, second = graph.nodes
    neighbor = Node(40, 30)
    graph._accept(neighbor, Edge(second, neighbor))
    proposed = Edge(first, second)
    state = graph._rng.getstate()
    assert graph.candidate_angle(proposed) < 60 and not graph.can_place_edge(proposed)
    assert not graph.can_place_edge(Edge(second, first))
    assert graph._rng.getstate() == state
    run = graph.growth()
    assert not run._accepts_edge(proposed) and run.hard_rejections == 1


@pytest.mark.parametrize('passes,attempts', [(-1, 10), (1, -1)])
def test_invalid_refill(passes: int, attempts: int) -> None:
    with pytest.raises(ValueError): GrowthSettings(refill_passes=passes, refill_attempts=attempts)
