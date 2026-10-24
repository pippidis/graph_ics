"""Ownership, interaction legality, reproducibility, and bounded colony growth."""
from math import pi
from typing import Literal
import networkx as nx
import pytest
from shapely.geometry import box
from graph_ics import Colony, ColonySettings, Interaction, Graph, GrowthSettings, CoverageSettings, AngleSettings, Node, Edge, Join, CallableField, SpatialFields
from graph_ics.colonies import rival_clearance, visible_distance
from tests.geometry_assertions import validate


def settings(*, attraction: float = 0, join: bool = False, clearance: float = 0, bridges: int = 1) -> ColonySettings:
    return ColonySettings((Colony('a', ((30, 50),), color='#ef916c'), Colony('b', ((70, 50),), color='#71b9e8')),
                          (Interaction('a', 'b', attraction, join, clearance),), target_bridges=bridges, bridge_attempts=100, bridge_distance=90)


def signature(graph: Graph) -> tuple[object, ...]:
    return (tuple((n.id, n.center.x, n.center.y, n.colony_id) for n in graph.nodes),
            tuple((e.start_node.id, e.end_node.id) for e in graph.edges), graph.parents, graph.component_ids())


@pytest.mark.parametrize('join', [False, True])
def test_bridge_without_attraction_and_replay(join: bool) -> None:
    graph = Graph(target_nodes=2, colonies=settings(join=join), edge_length_max=40)
    initial = graph.component_ids()
    parents = graph.parents.copy()
    run = graph.growth()
    joins: list[Join] = []
    while not run.done: joins.extend(run.step(1).joins)
    assert run.bridges_added == len(joins) == int(join)
    assert run.bridge_attempts <= 100
    assert len(set(graph.component_ids().values())) == int(join)
    if join:
        event = joins[0]
        assert event.first_component == initial[event.edge.start_node.id]
        assert event.second_component == initial[event.edge.end_node.id]
        assert {event.first_colony, event.second_colony} == {'a', 'b'}
        assert graph.parents == parents and {n.colony_id for n in graph.nodes} == {'a', 'b'}
        assert graph.nx_graph[event.edge.start_node.id][event.edge.end_node.id]['bridge']
    else: assert not graph.nodes  # Unconnected seeds are cleaned by default.
    assert run.step().joins == ()
    before = signature(graph)
    graph.build(force=True)
    assert signature(graph) == before


@pytest.mark.parametrize('batch', [1, 17, 1000])
@pytest.mark.parametrize('backend', ['hash', 'brute'])
def test_colony_schedule_replay(batch: int, backend: Literal['hash', 'brute']) -> None:
    config = settings(attraction=0.4, join=True)
    growth = GrowthSettings(failures_per_parent=8, total_attempts=1500, coverage=CoverageSettings(), refill_passes=1, loop_attempts=80)
    def make(kind: Literal['hash', 'brute']) -> Graph:
        return Graph(target_nodes=60, target_extra_edges=3, colonies=config, angles=AngleSettings(30, 60, 0.5), seed=7, edge_length_min=5, edge_length_max=12, spatial_backend=kind)
    expected = make('hash')
    expected.growth(settings=growth)
    expected.build()
    graph = make(backend)
    run = graph.growth(settings=growth)
    nodes = {n.id: n.colony_id for n in graph.nodes}
    edges: set[frozenset[str]] = set()
    while not run.done:
        result = run.step(batch)
        assert result.attempts <= batch
        for addition in result.additions:
            assert addition.colony_id == addition.node.colony_id
            nodes[addition.node.id] = addition.colony_id
            if addition.edge: edges.add(frozenset((addition.edge.start_node.id, addition.edge.end_node.id)))
        for edge in (*result.loop_additions, *(join.edge for join in result.joins)): edges.add(frozenset((edge.start_node.id, edge.end_node.id)))
        for key in result.removed_node_ids: nodes.pop(key)
    assert nodes == {n.id: n.colony_id for n in graph.nodes}
    assert edges == {frozenset((e.start_node.id, e.end_node.id)) for e in graph.edges}
    assert signature(graph) == signature(expected)
    report = run.colony_report(territory_resolution=5)
    assert report == expected.growth().colony_report(territory_resolution=5)
    assert sum(p.nodes for p in report.populations) == len(graph.nodes)
    assert all(p.accepted+p.rejected == p.attempts for p in report.populations)
    assert report.components == nx.number_connected_components(graph.to_networkx())
    assert sum(p.territory_fraction for p in report.populations) == pytest.approx(1)
    validate(graph)
    before = signature(graph)
    graph.build(force=True)
    assert signature(graph) == before


def test_competition_clearance_and_unequal_weights() -> None:
    config = ColonySettings((Colony('a', ((20, 50),), weight=4), Colony('b', ((80, 50),))), (Interaction('a', 'b', clearance=8),))
    graph = Graph(target_nodes=80, colonies=config, seed=9, edge_length_min=4, edge_length_max=10)
    run = graph.growth(settings=GrowthSettings(total_attempts=1000, failures_per_parent=8))
    graph.build()
    for i, first in enumerate(graph._objects):
        for second in graph._objects[i+1:]:
            gap = rival_clearance(config, first, second)
            if gap: assert visible_distance(first, second)+1e-9 >= gap
    assert all(edge.start_node.colony_id == edge.end_node.colony_id for edge in graph.edges)
    assert run.colony_report(territory_resolution=5).clearance_rejections > 0
    validate(graph)


def test_weighted_opportunity_is_not_population_weighted() -> None:
    config = ColonySettings((Colony('a', ((20, 50),), weight=4), Colony('b', ((80, 50),))))
    graph = Graph(target_nodes=10, colonies=config, seed=3)
    run = graph.growth()
    # Duplicate frontier entries deliberately: colony weights must not scale with frontier size.
    run._frontier = [graph.nodes[0]]*10+[graph.nodes[1]]
    a = sum(run._frontier[run._select_parent()].colony_id == 'a' for _ in range(2000))
    assert 1500 < a < 1700


def test_direction_and_clearance_shapes() -> None:
    attract = settings(attraction=1)
    graph = Graph(target_nodes=2, colonies=attract)
    assert attract.bias(graph, graph.nodes[0], pi/2) == pytest.approx(0)
    avoid = settings(attraction=-1)
    assert abs(avoid.bias(graph, graph.nodes[0], pi/2)) == pytest.approx(pi)
    center = Node(0, 0, outer_radius=3)
    other = Node(10, 0, outer_radius=2)
    assert visible_distance(center, other) == 5
    edge = Edge(Node(-10, 10), Node(10, 10), thickness=2)
    assert visible_distance(center, edge) == pytest.approx(6)
    assert visible_distance(edge, center) == pytest.approx(6)
    assert visible_distance(edge, edge) == 0


def test_impossible_bridges_obstacles_degree_and_budget() -> None:
    for growth, obstacles in [(GrowthSettings(total_attempts=0), None), (GrowthSettings(), box(45, 0, 55, 100))]:
        graph = Graph(target_nodes=2, colonies=settings(join=True), edge_length_max=40, illegal_areas=obstacles)
        run = graph.growth(settings=growth)
        graph.build()
        assert run.bridges_added == 0 and run.bridge_attempts <= 100
        assert run.colony_report(territory_resolution=2).bridge_shortfall == 1
    graph = Graph(target_nodes=2, colonies=settings(join=True), edge_length_max=40)
    run = graph.growth()
    assert not run.cancel().joins and not graph.nodes and run.bridge_attempts == 0


def test_invalid_configuration_and_seed_clearance() -> None:
    with pytest.raises(ValueError): Colony('a', ())
    with pytest.raises(ValueError): Colony('a', ((0, 0),), weight=0)
    with pytest.raises(ValueError): Interaction('a', 'a')
    with pytest.raises(ValueError): Interaction('a', 'b', attraction=2)
    with pytest.raises(ValueError): Interaction('a', 'b', allow_join=True, clearance=2)
    with pytest.raises(ValueError): ColonySettings((Colony('a', ((0, 0),)), Colony('a', ((5, 5),))))
    with pytest.raises(ValueError): ColonySettings((Colony('a', ((0, 0),)),), (Interaction('a', 'b'),))
    with pytest.raises(ValueError): Graph(target_nodes=1, colonies=settings())
    with pytest.raises(ValueError): Graph(target_nodes=2, colonies=settings(clearance=50))
    with pytest.raises(ValueError): Graph(target_nodes=2, colonies=settings(), input_nodes=[Node(5, 5)])
    with pytest.raises(ValueError): Graph().growth().colony_report()


@pytest.mark.parametrize('backend', ['hash', 'brute'])
def test_clearance_queries_include_distant_strokes(backend: Literal['hash', 'brute']) -> None:
    config = ColonySettings((Colony('a', ((50, 90),)), Colony('b', ((20, 50),))), (Interaction('a', 'b', clearance=8),))
    graph = Graph(target_nodes=5, colonies=config, spatial_backend=backend, cell_size=3)
    a, b = graph.nodes
    endpoint = Node(80, 50, colony_id='b', outer_radius=3)
    existing = Edge(b, endpoint)
    graph._accept(endpoint, existing)
    candidate = Node(50, 55, colony_id='a')
    proposed = Edge(a, candidate)
    assert not proposed.overlap(existing) and visible_distance(proposed, existing) < 8
    assert not graph.can_place_edge(proposed)
    assert not graph.can_place_node(Node(70, 60, colony_id='a', outer_radius=4))


def test_multiple_colonies_components_and_bridge_limits() -> None:
    config = ColonySettings((Colony('a', ((20, 50),)), Colony('b', ((50, 50),)), Colony('c', ((80, 50),))),
                            (Interaction('a', 'b', allow_join=True), Interaction('b', 'c', allow_join=True)), target_bridges=3, bridge_distance=80, bridge_attempts=100)
    graph = Graph(target_nodes=3, colonies=config, edge_length_max=25, seed=2)
    graph.build()
    assert graph.growth().bridges_added == 2
    assert len(set(graph.component_ids().values())) == 1
    assert graph.growth().colony_report(territory_resolution=2).bridge_shortfall == 1
    assert all(parent is None for parent in graph.parents.values())
    limited = Graph(target_nodes=3, colonies=config, edge_length_max=25, seed=2)
    limited.growth(settings=GrowthSettings(max_degree=1))
    limited.build()
    assert limited.growth().bridges_added == 1
    assert all(degree <= 1 for _, degree in limited.to_networkx().degree())
    assert not graph.can_place_edge(Edge(graph.nodes[0], graph.nodes[2]))


def test_variable_sizes_obstacle_and_no_unowned_reseeds() -> None:
    graph = Graph(target_nodes=70, seed=4, colonies=settings(clearance=5, bridges=0), edge_length_min=4, edge_length_max=9,
                  fields=SpatialFields(radius=CallableField(lambda x, y: 0.6+x/100)), illegal_areas=box(45, 25, 55, 75))
    run = graph.growth(settings=GrowthSettings(coverage=CoverageSettings(reseed_attempts=50), failures_per_parent=5, refill_passes=2))
    graph.build()
    assert run.reseed_attempts == 0 and all(n.colony_id in ('a', 'b') for n in graph.nodes)
    assert len({n.outer_radius for n in graph.nodes}) > 1
    validate(graph)
    assert graph.colonies is not None
    for i, first in enumerate(graph._objects):
        for second in graph._objects[i+1:]:
            gap = rival_clearance(graph.colonies, first, second)
            assert not gap or visible_distance(first, second)+1e-9 >= gap
