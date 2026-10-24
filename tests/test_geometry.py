"""Geometry regressions: full geometry, deterministic growth, and rendered pixels."""

from collections.abc import Callable
from math import cos, pi, sin
from pathlib import Path
import random
import sys
import xml.etree.ElementTree as ET

import cairo
import pytest
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box

from graph_ics import GrowthSettings, Edge, Graph, Node, export_graph
from graph_ics.colors import rgb_normalized


@pytest.mark.parametrize('angle', [0, pi/4, pi/2, pi, 3*pi/2, 7*pi/4])
def test_endpoint_clipping_and_mixed_radii(angle: float) -> None:
    first = Node(0, 0, outer_radius=3, inner_radius=1)
    last = Node(30*cos(angle), 30*sin(angle), outer_radius=5, inner_radius=2)
    edge = Edge(first, last, thickness=4, edge_node_distance=2)
    assert edge.start_point.distance(first.center) == pytest.approx(5)
    assert edge.end_point.distance(last.center) == pytest.approx(7)
    assert edge.length == pytest.approx(18)
    assert edge.footprint.area == pytest.approx(72)


@pytest.mark.parametrize('factory', [lambda: Node(inner_radius=2, outer_radius=2), lambda: Node(inner_radius=-1), lambda: Node(buffer=-1),
                                    lambda: Node(x=float('nan')), lambda: Node(opacity=2), lambda: Edge(Node(), Node()),
                                    lambda: Edge(Node(), Node(5, 0)), lambda: Edge(Node(), Node(20, 0), thickness=0),
                                    lambda: Edge(Node(), Node(20, 0), edge_node_distance=-1), lambda: Graph(edge_length_min=0),
                                    lambda: Graph(edge_length_min=3, edge_length_max=2), lambda: Graph(target_nodes=-1),
                                    lambda: Graph(target_nodes=True), lambda: Graph(outline_polygon=Polygon()), lambda: Graph(seed=True)])
def test_invalid_geometry_options(factory: Callable[[], object]) -> None:
    with pytest.raises(ValueError): factory()


def test_full_disk_boundary_and_obstacle_checks() -> None:
    graph = Graph(outline_polygon=box(0, 0, 30, 30), illegal_areas=box(12, 12, 18, 18))
    assert graph.in_bounds(Point(1, 10))
    assert not graph.in_bounds(Node(1, 10))
    assert graph.in_bounds(Node(2, 10))  # Exact boundary contact is permitted.
    assert not graph.in_illegal_areas(Point(11, 15))
    assert graph.in_illegal_areas(Node(11, 15))
    assert graph.in_illegal_areas(Node(10, 15))  # Obstacle contact is forbidden.


def test_concavity_holes_and_thick_edge_boundaries() -> None:
    outline = Polygon([(0, 0), (30, 0), (30, 30), (20, 30), (20, 10), (10, 10), (10, 30), (0, 30)])
    graph = Graph(outline_polygon=outline)
    edge = Edge(Node(5, 20), Node(25, 20))
    assert graph.in_bounds(edge.start_node) and graph.in_bounds(edge.end_node)
    assert not graph.in_bounds(edge)
    region = Polygon(box(0, 0, 40, 40).exterior.coords, holes=[box(15, 15, 25, 25).exterior.coords])
    assert not Graph(outline_polygon=region).in_bounds(Edge(Node(5, 20), Node(35, 20)))
    thick = Edge(Node(5, 2), Node(25, 2), thickness=6)
    assert Graph().in_bounds(thick.line_string)
    assert not Graph().in_bounds(thick)


def test_stroke_clearance_and_shared_endpoint_branches() -> None:
    horizontal = Edge(Node(0, 0), Node(30, 0), thickness=4)
    parallel = Edge(Node(0, 3), Node(30, 3), thickness=4)
    assert horizontal.line_string.distance(parallel.line_string) > 0
    assert horizontal.overlap(parallel)
    assert horizontal.overlap(Node(15, 3.5, outer_radius=1, inner_radius=0.5, buffer=1))
    parent = Node(0, 0)
    first = Edge(parent, Node(30, 0), thickness=2)
    assert not first.overlap(Edge(parent, Node(0, 30), thickness=2))
    assert first.overlap(Edge(parent, Node(30, 1), thickness=2))
    assert not first.overlap(parent)


def test_new_node_rejects_existing_edge() -> None:
    graph = Graph(target_nodes=3, input_nodes=[Node(10, 10)], seed=4, node_direction_function=lambda _: 0, node_length_function=lambda _: 20)
    graph._build_regular_nodes(nodes_to_build=1)
    edge = graph.edges[0]
    midpoint = edge.line_string.interpolate(0.5, normalized=True)
    assert not graph.can_place_node(Node(midpoint.x, midpoint.y, outer_radius=1, inner_radius=0.5, buffer=0))


def snapshot(graph: Graph) -> tuple[list[tuple[str, float, float]], list[tuple[str, str, float]]]:
    return [(n.id, n.center.x, n.center.y) for n in graph.nodes], [(e.start_node.id, e.end_node.id, e.length) for e in graph.edges]


def test_seeded_build_rebuild_and_global_rng_independence() -> None:
    random.seed(918)
    state = random.getstate()
    first = Graph(target_nodes=30, seed=7)
    first.build()
    assert random.getstate() == state
    original = snapshot(first)
    first.build()
    assert snapshot(first) == original
    first.build(force=True)
    assert snapshot(first) == original
    second = Graph(target_nodes=30, seed=7)
    second.build()
    assert snapshot(second) == original
    assert len(first.nodes) == 30
    assert len({n.id for n in first.nodes}) == 30
    assert set(first.nx_graph.nodes) == {n.id for n in first.nodes}


def test_input_node_copies_counts_and_zero_targets() -> None:
    node = Node(50, 50, outer_radius=5, inner_radius=2)
    original_id = node.id
    graph = Graph(target_nodes=4, target_seed_nodes=2, input_nodes=[node], seed=0)
    graph.growth(settings=GrowthSettings(remove_isolated_nodes=False))
    graph.build()
    assert len(graph.nodes) == 4
    assert node.id == original_id and graph.nodes[0] is not node
    assert graph.nodes[0].outer_radius == 5
    empty = Graph(target_nodes=0, target_seed_nodes=20)
    empty.build()
    assert not empty.nodes
    with pytest.raises(ValueError): Graph(target_nodes=0, input_nodes=[node])
    with pytest.raises(ValueError): Graph(input_nodes=[Node(0, 0)])


def test_full_circle_and_visible_length_sampling() -> None:
    graph = Graph(target_nodes=1, input_nodes=[Node(50, 50)], edge_length_min=7, edge_length_max=9, edge_node_distance=3, seed=2)
    quadrants: set[tuple[bool, bool]] = set()
    for _ in range(100):
        parent, candidate = graph.find_node_candidate()
        quadrants.add((candidate.center.x > 50, candidate.center.y > 50))
        edge = Edge(parent, candidate, edge_node_distance=3)
        assert 7-1e-10 <= edge.length <= 9+1e-10
    assert len(quadrants) == 4


def test_setting_propagation() -> None:
    graph = Graph(target_nodes=12, seed=0, node_inner_radius=1.5, node_outer_radius=3, node_buffer=0.25, edge_thickness=0.7,
                  edge_node_distance=2, node_color='#804020', edge_color='#203040', node_opacity=0.6, edge_opacity=0.4, edge_length_min=4, edge_length_max=6)
    graph.build()
    assert len(graph.nodes) + graph.growth().removed_nodes == 12
    assert all((n.inner_radius, n.outer_radius, n.buffer, n.color, n.opacity) == (1.5, 3, 0.25, '#804020', 0.6) for n in graph.nodes)
    assert all((e.thickness, e.edge_node_distance, e.color, e.opacity) == (0.7, 2, '#203040', 0.4) for e in graph.edges)
    assert all(4-1e-10 <= e.length <= 6+1e-10 for e in graph.edges)


@pytest.mark.parametrize('seed', [0, 1, 2, 3, 4])
def test_generated_geometry_invariants(seed: int) -> None:
    region = Polygon(box(-50, -50, 50, 50).exterior.coords, holes=[box(-8, -8, 8, 8).exterior.coords])
    graph = Graph(target_nodes=45, target_seed_nodes=3, outline_polygon=region, illegal_areas=box(20, 10, 30, 30), seed=seed)
    graph.build()
    assert 3 <= len(graph.nodes) <= 45
    for i, node in enumerate(graph.nodes):
        assert region.covers(node.center) and node.center.distance(region.boundary) >= node.outer_radius
        for other in graph.nodes[:i]: assert node.distance_to(other) > node.buffer_radius+other.buffer_radius
    for i, edge in enumerate(graph.edges):
        assert region.covers(edge.footprint)
        assert edge.footprint.disjoint(box(20, 10, 30, 30))
        for other_edge in graph.edges[:i]: assert edge.footprint.disjoint(other_edge.footprint)
        for node in graph.nodes:
            if node is not edge.start_node and node is not edge.end_node: assert edge.footprint.distance(node.center) > node.buffer_radius


def test_extent_includes_radii_and_stroke_without_origin_bias() -> None:
    graph = Graph(target_nodes=1, input_nodes=[Node(30, 40, outer_radius=5, inner_radius=2)], outline_polygon=box(10, 10, 100, 100))
    assert graph.get_extent() == (25, 35, 35, 45)
    assert graph.get_size(buffer=2) == (14, 14)
    with pytest.warns(DeprecationWarning): assert graph.get_exstent() == (25, 35, 35, 45)
    assert Graph(target_nodes=0).get_extent() == (0, 0, 0, 0)


def pixel(surface: cairo.ImageSurface, x: int, y: int) -> tuple[int, int, int, int]:
    surface.flush()
    offset = y*surface.get_stride()+4*x
    value = int.from_bytes(surface.get_data()[offset:offset+4], sys.byteorder)
    return (value >> 16) & 255, (value >> 8) & 255, value & 255, (value >> 24) & 255


def test_rendered_ring_radii_and_normalized_channels() -> None:
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 50, 50)
    context = cairo.Context(surface)
    # A pre-existing path must not introduce a line into the ring.
    context.move_to(0, 0)
    Node(25, 25, outer_radius=10, inner_radius=6, color='#804020', opacity=1).draw(context)
    assert pixel(surface, 25, 25)[3] == 0
    assert pixel(surface, 29, 25)[3] == 0
    assert pixel(surface, 36, 25)[3] == 0
    red, green, blue, alpha = pixel(surface, 33, 25)
    assert (red, green, blue, alpha) == (128, 64, 32, 255)
    assert rgb_normalized('#804020') == (128/255, 64/255, 32/255)


def test_export_margins_transparency_and_svg(tmp_path: Path) -> None:
    graph = Graph(target_nodes=1, input_nodes=[Node(30, 40, outer_radius=5, inner_radius=2)])
    assert export_graph(graph, tmp_path/'sample.png', margin=3, scale=2) == (32, 32)
    png = cairo.ImageSurface.create_from_png(str(tmp_path/'sample.png'))
    assert pixel(png, 0, 0)[3] == 0
    export_graph(graph, tmp_path/'sample.svg', margin=3, scale=2, background='#ffffff')
    root = ET.parse(tmp_path/'sample.svg').getroot()
    assert root.attrib['viewBox'] == '0 0 32 32'
    with pytest.raises(ValueError): export_graph(graph, tmp_path/'bad.pdf')
    with pytest.raises(ValueError): export_graph(Graph(target_nodes=0), tmp_path/'empty.png')


def test_multipart_region_and_bounded_failure() -> None:
    region = MultiPolygon([box(0, 0, 20, 20), box(40, 0, 60, 20)])
    graph = Graph(outline_polygon=region, target_nodes=20, target_seed_nodes=4, seed=0)
    graph.build()
    assert all(graph.in_bounds(node) for node in graph.nodes)
    assert not graph.in_bounds(LineString([(10, 10), (50, 10)]))
    tiny = Graph(outline_polygon=box(0, 0, 1, 1), target_nodes=1000, seed=0)
    tiny.build()
    assert not tiny.nodes and tiny.built


def test_historical_preset_and_border_export(tmp_path: Path) -> None:
    graph = Graph.historical(target_nodes=12, seed=7)
    graph.build()
    assert len(graph.nodes) + graph.growth().removed_nodes == 12
    assert all(node.outer_radius == 4 and node.inner_radius == 2 for node in graph.nodes)
    assert all(10-1e-10 <= edge.length <= 20+1e-10 for edge in graph.edges)
    # Sharp corners and interior contours must render within a padded region frame.
    region = Polygon([(0, 0), (100, 0), (1, 60)], holes=[[(5, 5), (15, 5), (5, 15)]])
    border = Graph(target_nodes=0, outline_polygon=region, draw_border=True)
    assert export_graph(border, tmp_path/'border.png', frame='region', margin=1, scale=4) == (410, 250)
    surface = cairo.ImageSurface.create_from_png(str(tmp_path/'border.png'))
    assert all(pixel(surface, x, 0)[3] == 0 for x in range(surface.get_width()))
    assert all(pixel(surface, 0, y)[3] == 0 for y in range(surface.get_height()))
    assert any(pixel(surface, x, 5)[3] for x in range(surface.get_width()))
