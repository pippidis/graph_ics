"""Incremental growth behavior, atomic events, and bounded termination."""

import pytest
from shapely.geometry import box

from graph_ics import Graph, GrowthGenerator, GrowthSettings, GrowthStatus, NewestTip, Node, RandomFrontier


def signature(graph: Graph) -> tuple[object, ...]:
    return (tuple((n.id, n.center.x, n.center.y) for n in graph.nodes), tuple((e.start_node.id, e.end_node.id) for e in graph.edges))


@pytest.mark.parametrize('batch', [1, 3, 17, 1000])
@pytest.mark.parametrize('newest', [False, True])
def test_step_sizes_and_events_match_batch(batch: int, newest: bool) -> None:
    expected = Graph.historical(target_nodes=60, seed=7)
    expected.growth(policy=NewestTip() if newest else RandomFrontier())
    expected.build()
    graph = Graph.historical(target_nodes=60, seed=7)
    generator = graph.growth(policy=NewestTip() if newest else RandomFrontier())
    accepted = 0
    completions = 0
    while not generator.done:
        before = len(graph.nodes)
        result = generator.step(batch)
        assert 0 <= result.attempts <= batch
        assert len(graph.nodes) == before + len(result.additions) - len(result.removed_node_ids)
        for event in result.additions:
            accepted += 1
            assert event.node in graph.nodes or event.node.id in result.removed_node_ids
            if event.edge is not None:
                assert event.edge.end_node is event.node
                assert graph.nx_graph.has_edge(event.edge.start_node.id, event.node.id)
        completions += result.completion is not None
    assert signature(graph) == signature(expected)
    assert accepted == 60 and completions == 1
    assert generator.attempts == expected.growth().attempts
    assert generator.step().completion is None
    graph.build(force=True)
    assert signature(graph) == signature(expected)
    with pytest.raises(RuntimeError): generator.step()


def test_failed_seeding_and_global_budget() -> None:
    tiny = Graph(outline_polygon=box(0, 0, 1, 1), target_nodes=100, seed=0)
    generator = tiny.growth(settings=GrowthSettings(seed_attempts=7))
    assert generator.step(3).attempts == 3
    assert generator.step(100).attempts == 4
    assert generator.status == GrowthStatus.FRONTIER_EXHAUSTED
    assert not tiny.nodes
    graph = Graph.historical()
    generator = graph.growth(settings=GrowthSettings(total_attempts=2))
    result = generator.step(100)
    assert result.total_attempts == 2
    assert result.status == GrowthStatus.ATTEMPT_BUDGET_EXHAUSTED
    assert generator.step().attempts == 0


def test_retirement_and_cancel_preserve_valid_partial_graph() -> None:
    graph = Graph(outline_polygon=box(0, 0, 5, 5), input_nodes=[Node(2.5, 2.5)], target_nodes=10, seed=0)
    generator = graph.growth(settings=GrowthSettings(failures_per_parent=4))
    result = generator.step(20)
    assert result.attempts == 4 and result.active_parents == 0
    assert result.status == GrowthStatus.FRONTIER_EXHAUSTED
    graph = Graph.historical()
    generator = graph.growth()
    generator.step(20)
    connected = {node.id for node in graph.nodes if graph.nx_graph.degree(node.id)}
    edges = signature(graph)[1]
    assert generator.cancel().status == GrowthStatus.CANCELLED
    assert generator.step().attempts == 0
    graph.build()
    assert {node.id for node in graph.nodes} == connected and signature(graph)[1] == edges
    for edge in graph.edges:
        assert graph.in_bounds(edge)
        assert not any(edge.overlap(node) for node in graph.nodes)


def test_ownership_and_zero_work_cases() -> None:
    graph = Graph(target_nodes=0)
    generator = GrowthGenerator(graph)
    assert graph.growth() is generator
    with pytest.raises(ValueError): GrowthGenerator(graph)
    with pytest.raises(ValueError): graph.growth(settings=GrowthSettings())
    with pytest.raises(ValueError): generator.step(0)
    assert generator.step().status == GrowthStatus.TARGET_REACHED
    graph = Graph(target_seed_nodes=0)
    assert graph.growth().step().status == GrowthStatus.FRONTIER_EXHAUSTED
    graph = Graph()
    assert graph.growth(settings=GrowthSettings(total_attempts=0)).step().attempts == 0


@pytest.mark.parametrize('settings', [{'failures_per_parent': 0}, {'seed_attempts': -1}, {'total_attempts': -1}])
def test_invalid_settings(settings: dict[str, int]) -> None:
    with pytest.raises(ValueError): GrowthSettings(failures_per_parent=settings.get('failures_per_parent', 30), seed_attempts=settings.get('seed_attempts', 100), total_attempts=settings.get('total_attempts'))
