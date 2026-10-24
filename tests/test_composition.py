"""Text placement, padded exclusions, renderer bounds, and optional dependencies."""
from math import ceil
from pathlib import Path
import cairo
import pytest
from shapely.geometry import box
from graph_ics import Graph, GraphStyle, Text, Node, GrowthSettings, CoverageSettings, export_graph
from tests.geometry_assertions import validate


def ink_bounds(surface: cairo.ImageSurface) -> tuple[int, int, int, int]:
    surface.flush()
    data = bytes(surface.get_data())
    points = [(x, y) for y in range(surface.get_height()) for x in range(surface.get_width()) if data[y*surface.get_stride()+4*x+3]]
    assert points
    return min(x for x, y in points), min(y for x, y in points), max(x for x, y in points), max(y for x, y in points)


@pytest.mark.parametrize('align', ['left', 'center', 'right'])
def test_alignment_baseline_and_descenders(align: str) -> None:
    from typing import cast, Literal
    text = Text('jAgyp', 100, 80, size=40, italic=True, align=cast(Literal['left', 'center', 'right'], align), padding=7)
    measured = text.measure()
    assert measured.bounds[1] < text.y < measured.bounds[3]
    assert measured.baseline_x == pytest.approx(100-measured.advance*{'left': 0, 'center': 0.5, 'right': 1}[align])
    a, b, c, d = measured.bounds
    assert measured.exclusion.bounds == pytest.approx((a-7, b-7, c+7, d+7))


@pytest.mark.parametrize('scale', [1, 2, 3.5])
def test_text_only_export_matches_measured_ink(tmp_path: Path, scale: float) -> None:
    graph = Graph(target_nodes=0, texts=(Text('jAgyp', -40, -20, size=45, italic=True, padding=10),))
    graph.build()
    bounds = graph.texts[0].bounds
    assert graph.get_extent() == bounds
    destination = tmp_path/'text.png'
    width, height = export_graph(graph, destination, margin=3, scale=scale)
    assert (width, height) == (ceil((bounds[2]-bounds[0]+6)*scale), ceil((bounds[3]-bounds[1]+6)*scale))
    x0, y0, x1, y1 = ink_bounds(cairo.ImageSurface.create_from_png(str(destination)))
    assert abs(x0-3*scale) <= 1 and abs(y0-3*scale) <= 1
    assert x1 < width-1 and y1 < height-1
    svg = tmp_path/'text.svg'
    assert export_graph(graph, svg, margin=3, scale=scale) == (width, height)
    assert '<path' in svg.read_text() and '<text' not in svg.read_text()


def test_padded_exclusion_and_rebuild() -> None:
    graph = GraphStyle.historical().create_graph(target_nodes=120, texts=(Text('Graph ICS', 300, 190, size=60, align='center', padding=12),))
    graph.build()
    validate(graph)
    exclusion = graph.texts[0].exclusion
    assert all(exclusion.distance(node.center) > node.outer_radius for node in graph.nodes)
    assert all(not exclusion.intersects(edge.footprint) for edge in graph.edges)
    before = [(n.id, n.center.x, n.center.y) for n in graph.nodes]
    graph.build(force=True)
    assert [(n.id, n.center.x, n.center.y) for n in graph.nodes] == before
    with pytest.raises(ValueError): Graph(input_nodes=[Node(50, 45)], texts=(Text('MMMM', 40, 50, padding=15),))


def test_draw_text_flag_shift_and_region_extent(tmp_path: Path) -> None:
    graph = Graph(target_nodes=0, texts=(Text('A', 150, 150, size=25),))
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 200)
    context = cairo.Context(surface)
    graph.draw(context, draw_text=False)
    assert not any(bytes(surface.get_data()))
    graph.draw(context, x_shift=-100, y_shift=-100)
    x0, y0, x1, y1 = ink_bounds(surface)
    assert 49 <= x0 < x1 < 80 and 20 < y0 < y1 <= 50
    width, height = export_graph(graph, tmp_path/'region.png', frame='region', margin=0)
    assert width >= ceil(graph.texts[0].bounds[2]) and height >= ceil(graph.texts[0].bounds[3])


def test_in_memory_measurement_and_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert Text('Fallback', 0, 0, font='Font That Does Not Exist 721934').measure().advance > 0
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('content', ['', ' ', 'line\nbreak', 'tab\there', 'null\0here'])
def test_invalid_content(content: str) -> None:
    with pytest.raises(ValueError): Text(content, 0, 0)


def test_invalid_styles_and_geometry() -> None:
    with pytest.raises(ValueError): Text('A', 0, 0, size=0)
    with pytest.raises(ValueError): Text('A', 0, 0, padding=-1)
    with pytest.raises(ValueError): Text('A', float('nan'), 0)
    with pytest.raises(ValueError): GraphStyle(edge_length_min=50, edge_length_max=10)
    with pytest.raises(ValueError): GraphStyle(node_outer_radius=1)
    style = GraphStyle.light()
    graph = style.create_graph(target_nodes=0, outline_polygon=box(0, 0, 20, 20))
    assert graph.node_color == style.node_color and graph.edge_color == style.edge_color


@pytest.mark.parametrize('size', [18, 36, 72])
@pytest.mark.parametrize('padding_em', [0, 0.05, 0.3])
def test_relative_clearance_at_multiple_text_sizes(size: float, padding_em: float) -> None:
    text = Text('Type', 150, 90, size=size, align='center', padding=0, padding_em=padding_em)
    assert text.effective_padding == pytest.approx(size*padding_em)
    graph = Graph(target_nodes=180, seed=7, outline_polygon=box(0, 0, 300, 180), texts=(text,), edge_length_min=3, edge_length_max=8)
    graph.growth(settings=GrowthSettings(coverage=CoverageSettings(tile_size=25), total_attempts=5000))
    graph.build()
    ink = box(*graph.texts[0].bounds)
    assert graph.nodes and graph.edges
    assert all(ink.distance(node.center)-node.outer_radius >= text.effective_padding-1e-8 for node in graph.nodes)
    assert all(ink.distance(edge.footprint) >= text.effective_padding-1e-8 for edge in graph.edges)
    validate(graph)


def test_absolute_and_relative_padding_combine() -> None:
    text = Text('A', 0, 0, size=40, padding=2, padding_em=0.1)
    assert text.effective_padding == 6
    with pytest.raises(ValueError): Text('A', 0, 0, padding_em=-1)
