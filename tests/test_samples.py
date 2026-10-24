"""Supported recipes, palette contracts, command-line output, and scalable validation."""
from pathlib import Path
import json
import subprocess
import sys
import pytest
from graph_ics import GraphStyle, build_example, describe_example, example_names, validate_graph, Graph, Node, Edge, NODE_SHAPES, EDGE_STYLES
from graph_ics.cli import main
from graph_ics.gallery import generate_gallery
from tests.geometry_assertions import validate


@pytest.mark.parametrize('name', example_names())
def test_every_recipe(name: str) -> None:
    graph = build_example(name, nodes=40)
    graph.build()
    report = validate_graph(graph)
    validate(graph)
    assert report.objects == len(graph.nodes)+len(graph.edges)
    from graph_ics.samples import explain_option
    assert all(explain_option(option) for option in describe_example(name).options)
    assert describe_example(name).explanation and describe_example(name).options and describe_example(name).limitation


@pytest.mark.parametrize('palette', GraphStyle.palette_names())
def test_palette_geometry_and_colors(palette: str) -> None:
    graph = build_example('sprawl', palette=palette, nodes=30)
    graph.build()
    baseline = build_example('sprawl', palette='historical', nodes=30)
    baseline.build()
    assert [(n.center.x, n.center.y) for n in graph.nodes] == [(n.center.x, n.center.y) for n in baseline.nodes]
    assert all(n.color == GraphStyle.named(palette).node_color for n in graph.nodes)
    validate_graph(graph)


def test_cli_describe_render_record_frames(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(['describe', 'density']) == 0
    assert json.loads(capsys.readouterr().out)['name'] == 'density'
    image, log = tmp_path/'output.svg', tmp_path/'growth.jsonl'
    args = ['render', '--example', 'sprawl', '--nodes', '8', '--output', str(image), '--record', str(log)]
    assert main(args) == 0 and image.exists() and log.exists()
    previous = image.read_bytes()
    assert main(args) == 2 and image.read_bytes() == previous
    assert main([*args, '--force']) == 0
    assert main(['frames', '--log', str(log), '--output', str(tmp_path/'frames'), '--fps', '4', '--seconds-per-event', '0.1']) == 0
    assert list((tmp_path/'frames').glob('frame_*.png'))
    assert main(['frames', '--example', 'sprawl', '--nodes', '4', '--output', str(tmp_path/'new_frames'), '--fps', '2']) == 0
    assert main(['render', '--nodes', '-1', '--output', str(tmp_path/'bad.png')]) == 2
    assert main(['render', '--output', str(tmp_path/'bad.txt')]) == 2
    assert main(['render', '--output', str(tmp_path/'same.png'), '--record', str(tmp_path/'same.png')]) == 2


def test_module_cli_and_explained_gallery(tmp_path: Path) -> None:
    result = subprocess.run([sys.executable, '-m', 'graph_ics', 'list'], check=True, capture_output=True, text=True)
    assert 'arctic' in result.stdout and 'archipelago' in result.stdout
    index = generate_gallery(tmp_path/'gallery', quick=True)
    manifest = json.loads((index.parent/'manifest.json').read_text())
    assert len(manifest['cases']) == 6
    assert all(record['options'] and record['command'] and record['limitation'] for record in manifest['cases'])
    assert all(record['accepted_attempts']+record['rejected_attempts'] == record['attempts'] for record in manifest['cases'])
    assert len([p for p in (index.parent/'figures').glob('*.svg') if not p.name.startswith(('control-', 'scene-'))]) == 6
    assert (index.parent/'guide/controls.html').exists()
    html = index.read_text(encoding='utf-8')
    assert 'Art grown from connections.' in html and 'https://pippidis.no' in html
    examples = (index.parent/'gallery/index.html').read_text(encoding='utf-8')
    assert 'Options, limits, and command' in examples and '--all-palettes' in examples
    assert 'WorldPop' in (index.parent/'guide/maps.html').read_text(encoding='utf-8')
    assert (index.parent/'about/index.html').exists()
    from scripts.check_site import check_site
    assert check_site(index.parent) == []


def test_validation_rejects_invalid_geometry_and_names() -> None:
    graph = Graph(target_nodes=2)
    graph._accept(Node(20, 20))
    graph._accept(Node(21, 20))
    with pytest.raises(ValueError, match='overlaps'): validate_graph(graph)
    with pytest.raises(ValueError): GraphStyle.named('missing')
    with pytest.raises(ValueError): build_example('missing')
    with pytest.raises(ValueError): build_example('cooperate', nodes=1)
    assert len(set(GraphStyle.named(name).background for name in GraphStyle.palette_names())) == 10


@pytest.mark.parametrize('shape', NODE_SHAPES)
@pytest.mark.parametrize('style', EDGE_STYLES)
def test_shapes_lines_replay_and_reserved_geometry(shape: str, style: str, tmp_path: Path) -> None:
    import cairo
    from graph_ics import NODE_SHAPES, EDGE_STYLES, EventRecorder, EventLog, Playback, ReplayRenderer, export_graph
    from graph_ics.rendering import draw_node, draw_edge
    selected_shape = next(value for value in NODE_SHAPES if value == shape)
    selected_style = next(value for value in EDGE_STYLES if value == style)
    graph = build_example('lines', nodes=15, node_shape=selected_shape, edge_style=selected_style)
    with EventRecorder(graph, path=tmp_path/'events.jsonl') as recorder: graph.build()
    validate_graph(graph)
    assert all(node.shape == shape for node in graph.nodes)
    assert all(edge.style == style for edge in graph.edges)
    log = EventLog.load(tmp_path/'events.jsonl')
    assert log.events == recorder.snapshot().events
    playback = Playback(log)
    renderer = ReplayRenderer(playback)
    final = renderer.render(playback.duration)
    export_graph(graph, tmp_path/'static.png', frame='region')
    static = cairo.ImageSurface.create_from_png(str(tmp_path/'static.png'))
    assert bytes(final.get_data()) == bytes(static.get_data())
    # Inspect actual alpha pixels against the protected disk/rectangle. The small
    # tolerance accounts for a pixel's area and raster antialiasing at 8x scale.
    from math import ceil
    from shapely.geometry import Point
    objects: list[Node | Edge] = [graph.nodes[0], graph.edges[0]]
    for obj in objects:
        bounds = obj.bounds if isinstance(obj, Node) else obj.footprint.bounds
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, ceil((bounds[2]-bounds[0]+4)*8), ceil((bounds[3]-bounds[1]+4)*8))
        context = cairo.Context(surface)
        context.scale(8,8)
        context.translate(2-bounds[0],2-bounds[1])
        if isinstance(obj, Node): draw_node(obj, context)
        else: draw_edge(obj, context)
        surface.flush()
        pixels = bytes(surface.get_data())
        for y in range(surface.get_height()):
            for x in range(surface.get_width()):
                if not pixels[y*surface.get_stride()+x*4+3]: continue
                point = Point((x+0.5)/8-2+bounds[0], (y+0.5)/8-2+bounds[1])
                if isinstance(obj, Node): assert point.distance(obj.center) <= obj.outer_radius+0.2
                else: assert obj.footprint.distance(point) <= 0.2


def test_uk_population_georeferencing_and_offline_sample() -> None:
    from graph_ics.uk import population_data, population_field, population_region, WIDTH, HEIGHT
    from shapely.geometry import Point
    data = population_data()
    assert data['metadata']['year'] == 2020
    assert data['metadata']['units'] == 'persons per square kilometre'
    field, region = population_field(), population_region()
    def xy(lon: float, lat: float) -> tuple[float, float]: return (lon+8.7)*WIDTH/10.8, (61.1-lat)*HEIGHT/11.3
    assert region.covers(Point(*xy(-0.12,51.5)))  # London
    assert region.covers(Point(*xy(-5.93,54.6)))  # Belfast
    assert not region.covers(Point(*xy(-6.26,53.35)))  # Dublin is not in the UK.
    assert field.sample(*xy(-0.12,51.5)) > field.sample(*xy(-4.8,57.3))*10
    assert len(data['pixels']) == 560 and len(data['pixels'][0]) == 360


def test_cli_controls_help_and_invalid_style_overrides(tmp_path: Path) -> None:
    from graph_ics.cli import parser
    from graph_ics.option_gallery import CLI_OPTIONS
    import argparse
    root = parser()
    subparsers = next(action for action in root._actions if isinstance(action, argparse._SubParsersAction))
    documented = {token for row in CLI_OPTIONS for token in row[0].split(' / ')}
    for command in subparsers.choices.values():
        for action in command._actions:
            if action.option_strings:
                assert action.help and any(option in documented for option in action.option_strings)
    assert main(['render','--minimum-angle','-1','--output',str(tmp_path/'invalid.png')]) == 2
    assert not (tmp_path/'invalid.png').exists()
    assert main(['render','--example','lines','--nodes','12','--node-shape','square','--edge-style','dotted','--minimum-angle','45','--preferred-angle','80','--angle-penalty','0.8','--output',str(tmp_path/'styled.svg')]) == 0


@pytest.mark.parametrize('shape', NODE_SHAPES)
def test_polygon_and_double_line_readability(shape: str) -> None:
    from dataclasses import replace
    from graph_ics import ContourSettings, Readability
    from graph_ics.node import shape_inradius_ratio
    selected = next(value for value in NODE_SHAPES if value == shape)
    style = replace(GraphStyle.named('porcelain'), node_shape=selected, edge_style='double')
    graph = style.create_graph(target_nodes=30, contours=ContourSettings(readability=Readability(stroke=1, hole_diameter=2)))
    graph.build()
    assert graph.edges
    for node in graph.nodes:
        factor = shape_inradius_ratio(node.shape)
        assert (node.outer_radius-node.inner_radius)*factor >= 1-1e-8
        assert 2*node.inner_radius*factor >= 2-1e-8
    assert all(edge.thickness/3 >= 1-1e-8 for edge in graph.edges)
    validate_graph(graph)


def test_replay_reads_logs_without_shape_fields(tmp_path: Path) -> None:
    from graph_ics import EventRecorder, EventLog
    graph = build_example('sprawl',nodes=8)
    path = tmp_path/'old.jsonl'
    with EventRecorder(graph,path=path): graph.build()
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    for row in rows:
        if row.get('node'): row['node'].pop('shape',None)
        if row.get('edge'): row['edge'].pop('style',None)
    path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    state = EventLog.load(path).validate()
    assert all(node.shape == 'circle' for node in state.nodes.values())
    assert all(edge.style == 'solid' for edge in state.edges)
