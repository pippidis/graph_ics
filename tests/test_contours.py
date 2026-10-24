"""Contour semantics, readable adaptive geometry, and honest terminal constraints."""

from pathlib import Path
from typing import Literal

import pytest
from shapely.geometry import MultiPolygon, Point, Polygon, box

from graph_ics import ContourSettings, DistanceField, Graph, GrowthSettings, GrowthStatus, LocalWidth, Node, Readability, RegionSpec, export_graph
from tests.geometry_assertions import validate


def test_region_semantics_and_rejection() -> None:
    shape = box(10, 10, 30, 30)
    assert RegionSpec(shape, padding=2).resolve().bounds == (12, 12, 28, 28)
    outside = RegionSpec(shape, 'outside', canvas=box(0, 0, 40, 40)).resolve()
    assert outside.covers(Point(5, 5)) and not outside.covers(Point(20, 20))
    band = RegionSpec(shape, 'band', band_width=4).resolve()
    assert band.covers(Point(10, 20)) and not band.covers(Point(20, 20))
    with pytest.raises(ValueError): RegionSpec(shape, 'outside').resolve()
    with pytest.raises(ValueError): RegionSpec(Polygon([(0, 0), (10, 10), (10, 0), (0, 10)])).resolve()
    with pytest.raises(ValueError): RegionSpec(shape, padding=100).resolve()
    with pytest.raises(ValueError): Graph(outline_polygon=shape, region=RegionSpec(shape))


def test_distance_width_and_readability() -> None:
    distance = DistanceField(box(0, 0, 100, 20))
    assert distance.sample(50, 10) == 10
    assert distance.sample(50, -10) == -10
    assert distance.sample(0, 10) == 0
    width = LocalWidth(box(0, 0, 100, 20), 2, 1000)
    assert width.sample(50, 1) > 10  # Near a wall is not necessarily a narrow feature.
    assert width.sample(50, 10) == pytest.approx(18, abs=2)
    assert Readability(output_scale=2).radius_minimum(0.5) == 0.5
    with pytest.raises(ValueError): Readability(output_scale=0)
    with pytest.raises(ValueError): ContourSettings(maximum_neighbor_ratio=0.5)


@pytest.mark.parametrize('mode', ['contain', 'follow', 'terminate'])
def test_modes_step_equivalence_and_full_footprints(mode: Literal['contain', 'follow', 'terminate']) -> None:
    shape = Polygon([(0, 0), (150, 0), (150, 100), (95, 100), (95, 40), (55, 40), (55, 100), (0, 100)])
    settings = ContourSettings(mode=mode, anchor_spacing=12, width_resolution=5)
    first = Graph(target_nodes=90, target_seed_nodes=6, seed=7, region=RegionSpec(shape), contours=settings, node_outer_radius=4, node_inner_radius=2, edge_length_min=8, edge_length_max=14)
    second = Graph(target_nodes=90, target_seed_nodes=6, seed=7, region=RegionSpec(shape), contours=settings, node_outer_radius=4, node_inner_radius=2, edge_length_min=8, edge_length_max=14, spatial_backend='brute')
    for graph in (first, second): graph.growth(settings=GrowthSettings(failures_per_parent=6, total_attempts=1500))
    first.build()
    while not second.growth().done: second.growth().step(1)
    assert [(n.center.wkt, n.outer_radius) for n in first.nodes] == [(n.center.wkt, n.outer_radius) for n in second.nodes]
    validate(first)
    assert all(max(e.start_node.outer_radius, e.end_node.outer_radius)/min(e.start_node.outer_radius, e.end_node.outer_radius) <= settings.maximum_neighbor_ratio*(1+1e-8) for e in first.edges)
    assert all(n.outer_radius-n.inner_radius >= 0.5-1e-8 and n.inner_radius*2 >= 1-1e-8 for n in first.nodes)
    report = first.contour_report()
    assert 0 <= report.boundary_coverage <= 1
    assert len(report.terminal_distances) == report.terminal_count
    if mode == 'follow': assert report.boundary_nodes > 0
    before = [(n.center.wkt, n.outer_radius) for n in first.nodes]
    first.build(force=True)
    assert [(n.center.wkt, n.outer_radius) for n in first.nodes] == before


def test_strict_unmet_and_successful_boundary_ending() -> None:
    graph = Graph(target_nodes=1, input_nodes=[Node(50, 50)], contours=ContourSettings(mode='terminate', strict_terminals=True))
    assert graph.growth().step().status == GrowthStatus.CONSTRAINT_UNMET
    assert not graph.nodes and not graph.contour_report().strict_satisfied
    graph = Graph(target_nodes=2, input_nodes=[Node(90, 50, outer_radius=2, inner_radius=1)], contours=ContourSettings(mode='terminate', guidance=1),
                  seed=0, edge_length_min=20, edge_length_max=20)
    graph.build()
    assert len(graph.nodes) == 2 and graph.boundary_terminal(graph.nodes[-1])
    validate(graph)
    # A finite minimum blocks a feature rather than silently shrinking to zero.
    tiny = Graph(target_nodes=5, region=RegionSpec(box(0, 0, 1, 1)), contours=ContourSettings())
    tiny.growth(settings=GrowthSettings(seed_attempts=5))
    tiny.build()
    assert not tiny.nodes and tiny.width_failures > 0
    assert tiny.contour_report().unreadable_boundary_samples > 0


def test_export_scale_and_multipart_anchors(tmp_path: Path) -> None:
    graph = Graph(target_nodes=10, target_seed_nodes=5, seed=7, region=RegionSpec(MultiPolygon([box(0, 0, 30, 30), box(50, 0, 80, 30)])),
                  contours=ContourSettings(mode='follow', boundary_fraction=1, readability=Readability(output_scale=2)))
    graph.build()
    assert graph.contour_guide is not None
    assert len({anchor.component for anchor in graph.contour_guide.anchors}) == 2
    with pytest.raises(ValueError): export_graph(graph, tmp_path/'small.png', scale=1)
    export_graph(graph, tmp_path/'readable.png', scale=2)
    validate(graph)


def test_readability_rejection_and_boundary_budget() -> None:
    from graph_ics import Edge
    graph = Graph(contours=ContourSettings())
    assert not graph.can_place_edge(Edge(Node(20, 20), Node(40, 20), thickness=0.1))
    assert graph.readable_failures == 1
    with pytest.raises(ValueError): LocalWidth(box(0, 0, 20, 20), 0, 100)
    with pytest.raises(ValueError): DistanceField(box(0, 0, 20, 20)).sample(float('nan'), 0)
    graph = Graph(target_nodes=80, target_seed_nodes=1, seed=7, contours=ContourSettings(mode='follow', boundary_fraction=1, max_anchors=40))
    graph.growth(settings=GrowthSettings(failures_per_parent=3, total_attempts=500))
    graph.build()
    assert graph.growth().attempts <= 500
    assert graph.contour_guide is not None and graph._anchor_cursor <= len(graph.contour_guide.anchors)*2
    validate(graph)


def test_fields_combine_with_contour_constraints() -> None:
    from graph_ics import CallableField, SpatialFields
    shape = Polygon(box(0, 0, 200, 80).exterior.coords, holes=[box(80, 20, 120, 60).exterior.coords])
    fields = SpatialFields(radius=CallableField(lambda x, y: 0.5+x/200), density=CallableField(lambda x, y: 1/(10+x/10)**2))
    graph = Graph(target_nodes=80, target_seed_nodes=5, seed=21, region=RegionSpec(shape), fields=fields, contours=ContourSettings(width_resolution=4))
    graph.build()
    assert len(graph.nodes) > 10
    validate(graph)
    assert all(a.distance_to(b) > max(a.preferred_spacing, b.preferred_spacing) for i, a in enumerate(graph.nodes) for b in graph.nodes[:i])
    assert not graph.can_place_node(Node(20, 20, buffer=0, min_edge_length=0))
