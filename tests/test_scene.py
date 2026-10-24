"""Scene inputs, glyph geometry, colour fields and GIF output contracts."""
from copy import deepcopy
from pathlib import Path
import json
import pytest
import yaml
from shapely.geometry import Point, Polygon
from graph_ics import Text, SceneConfig, ColorRamp, ConstantField, EventRecorder, Playback, ReplayRenderer, export_graph, validate_graph
from graph_ics.scene_gallery import scene_examples
from graph_ics.cli import main


def test_scene_json_yaml_equivalence_and_no_mutation(tmp_path: Path) -> None:
    data = dict(version=1,nodes=35,width=180,height=120,style=dict(node_outer_radius=3,node_inner_radius=1),growth=dict(coverage=dict(tile_size=30)),
                color_map=dict(field=dict(kind='gradient'),colors=['#000000','#ffffff']))
    original=deepcopy(data)
    scenes=[]
    for suffix,text in [('json',json.dumps(data)),('yaml',yaml.safe_dump(data))]:
        path=tmp_path/f'scene.{suffix}'
        path.write_text(text)
        scene=SceneConfig.load(path)
        scene.graph.build()
        validate_graph(scene.graph)
        scenes.append(scene)
    SceneConfig.from_mapping(data)
    assert data==original
    assert [(n.center.x,n.center.y,n.color) for n in scenes[0].graph.nodes]==[(n.center.x,n.center.y,n.color) for n in scenes[1].graph.nodes]
    assert len({n.color for n in scenes[0].graph.nodes})>1


@pytest.mark.parametrize('data',[{'unknown':3},{'version':2},{'width':float('nan')},{'style':{'node_outer_radius':-1}},{'fields':{'radius':{'kind':'invalid'}}},{'boundary_style':{'width':0}}])
def test_invalid_scene_rejected(data: dict[str, object]) -> None:
    with pytest.raises(ValueError): SceneConfig.from_mapping(data)


def test_safe_yaml_and_relative_boundary(tmp_path: Path) -> None:
    path=tmp_path/'scene.yaml'
    path.write_text('!!python/object/apply:os.system [echo unsafe]')
    with pytest.raises(ValueError): SceneConfig.load(path)
    boundary=dict(type='Polygon',coordinates=[[[0,0],[120,0],[120,100],[0,100],[0,0]]])
    (tmp_path/'outline.json').write_text(json.dumps(boundary))
    path.write_text('boundary: outline.json\nnodes: 20\n')
    assert SceneConfig.load(path).graph.outline_polygon.bounds==(0,0,120,100)


def test_glyph_holes_and_tight_exclusion() -> None:
    measured=Text('O',0,200,size=200,bold=True,padding=0,exclusion_mode='glyph').measure()
    glyph=measured.glyph_region
    polygons=[glyph] if isinstance(glyph,Polygon) else list(glyph.geoms)
    holes=[Polygon(ring) for polygon in polygons for ring in polygon.interiors]
    assert holes
    centre=max(holes,key=lambda hole:hole.area).representative_point()
    assert not glyph.covers(centre) and not measured.exclusion.covers(centre)
    assert measured.exclusion.area < Text('O',0,200,size=200,padding=0,bold=True).measure().exclusion.area
    data=scene_examples()['graph-lettering'][1]
    data['nodes']=100
    scene=SceneConfig.from_mapping(data)
    scene.graph.build()
    assert len(scene.graph.nodes)>50 and not scene.graph.texts
    validate_graph(scene.graph)
    assert all(scene.graph.outline_polygon.covers(n.center) for n in scene.graph.nodes)


def test_colour_ramp_endpoints() -> None:
    assert ColorRamp(ConstantField(0),('#000000','#ffffff')).sample(0,0)=='#000000'
    assert ColorRamp(ConstantField(0.5),('#000000','#ffffff')).sample(0,0)=='#808080'
    assert ColorRamp(ConstantField(2),('#000000','#ffffff')).sample(0,0)=='#ffffff'


def test_border_colour_replay_and_gif(tmp_path: Path) -> None:
    import cairo
    from PIL import Image, GifImagePlugin
    scene=SceneConfig.from_mapping(dict(nodes=25,width=140,height=100,boundary_style=dict(visible=True,color='#aa2233',width=4),color_map=dict(field=dict(kind='gradient'))))
    graph=scene.graph
    with EventRecorder(graph) as recorder: graph.build()
    playback=Playback(recorder.snapshot(),seconds_per_event=0.01)
    renderer=ReplayRenderer(playback,background='#ffffff')
    export_graph(graph,tmp_path/'static.png',frame='region',background='#ffffff')
    static=cairo.ImageSurface.create_from_png(str(tmp_path/'static.png'))
    assert bytes(renderer.render(playback.duration).get_data())==bytes(static.get_data())
    position=playback.position
    path=renderer.export_gif(tmp_path/'growth.gif',fps=20)
    assert playback.position==position
    with Image.open(path) as image:
        assert isinstance(image,GifImagePlugin.GifImageFile)
        assert image.n_frames>2 and image.info['loop']==0
        image.seek(0)
        first=image.convert('RGB').tobytes()
        image.seek(image.n_frames-1)
        assert image.convert('RGB').tobytes()!=first
    with pytest.raises(FileExistsError): renderer.export_gif(path)
    with pytest.raises(ValueError): renderer.export_gif(tmp_path/'oversized.gif',max_pixels=1)
    assert not (tmp_path/'oversized.gif').exists()


def test_scene_cli_and_geometry_overrides(tmp_path: Path) -> None:
    from graph_ics import build_example
    assert build_example('lines',style_overrides={'edge_thickness':3}).edge_thickness==3
    assert build_example('uk_colors',nodes=20,style_overrides={'edge_thickness':2}).edge_thickness==2
    path=tmp_path/'input.json'
    path.write_text(json.dumps(dict(nodes=20,width=150,height=100)))
    assert main(['render','--config',str(path),'--output',str(tmp_path/'scene.svg')])==0
    assert main(['render','--config',str(path),'--palette','arctic','--output',str(tmp_path/'ignored.svg')])==2
    assert main(['render','--config',str(path),'--node-outer-radius','9','--output',str(tmp_path/'bad.svg')])==2
    assert main(['render','--nodes','10','--node-inner-radius','1','--node-outer-radius','3','--edge-thickness','2','--output',str(tmp_path/'override.png')])==0


def test_spain_extent_and_population_alignment() -> None:
    from graph_ics.uk import population_region,population_field,population_data,dimensions
    data=population_data('spain')
    width,height=dimensions('spain')
    def point(lon: float,lat: float) -> Point: return Point((lon+9.6)*width/14.1,(44.1-lat)*height/8.6)
    region=population_region('spain')
    assert region.covers(point(-3.7,40.42))
    assert not region.covers(point(-15.43,28.12))
    assert not region.covers(point(-9.14,38.72))
    madrid=point(-3.7,40.42)
    rural=point(-3,40.9)
    raster=population_field('spain')
    assert raster.sample(madrid.x,madrid.y)>raster.sample(rural.x,rural.y)
    assert data['metadata']['year']==2020

def test_area_fill_is_bounded_and_visits_disconnected_regions() -> None:
    from graph_ics import GraphStyle, GrowthSettings, CoverageSettings, GrowthStatus
    from shapely.geometry import MultiPolygon, box
    outline=MultiPolygon([box(0,0,100,100),box(300,0,400,100)])
    settings=GrowthSettings(fill_area=True,total_attempts=5000,coverage=CoverageSettings(tile_size=25,reseed_attempts=300,reseed_interval=10))
    graphs=[]
    for batch in (1,100):
        graph=GraphStyle.named('porcelain').create_graph(target_nodes=120,target_seed_nodes=2,outline_polygon=outline,seed=17)
        run=graph.growth(settings=settings)
        while not run.done: run.step(batch)
        assert run.attempts<=5000 and len(graph.nodes)<=120
        assert run.status in (GrowthStatus.NODE_LIMIT_REACHED,GrowthStatus.ATTEMPT_BUDGET_EXHAUSTED,GrowthStatus.FILL_SEARCH_EXHAUSTED)
        assert all(sum(part.covers(node.center) for node in graph.nodes)>5 for part in outline.geoms)
        report=run.coverage_report()
        assert 0 < report.occupied_tile_area_fraction <= 1
        validate_graph(graph)
        graphs.append(graph)
    assert [(n.center.x,n.center.y) for n in graphs[0].nodes]==[(n.center.x,n.center.y) for n in graphs[1].nodes]


def test_fill_node_cap_is_not_reported_as_completed_area() -> None:
    scene=SceneConfig.from_mapping(dict(nodes=10,width=600,height=400,growth=dict(fill_area=True,total_attempts=10000)))
    scene.graph.build()
    assert scene.graph.growth().status.value=='node_limit_reached'
    assert scene.graph.growth().coverage_report().occupied_tile_area_fraction < 0.1

def test_logo_crops_network_at_all_edges_and_exports_sizes(tmp_path: Path) -> None:
    from graph_ics import make_logo
    from PIL import Image
    assert make_logo(tmp_path/'logo.png',width=300,height=125)==(300,125)
    make_logo(tmp_path/'same.png',width=300,height=125)
    assert (tmp_path/'logo.png').read_bytes()==(tmp_path/'same.png').read_bytes()
    assert make_logo(tmp_path/'logo.svg',width=300,height=125,scale=2)==(600,250)
    assert '<svg' in (tmp_path/'logo.svg').read_text()
    with Image.open(tmp_path/'logo.png') as image:
        rgb=image.convert('RGB')
        edges=[[(x,0) for x in range(300)],[(x,124) for x in range(300)],[(0,y) for y in range(125)],[(299,y) for y in range(125)]]
        assert all(any(rgb.getpixel(point)!=(255,255,255) for point in edge) for edge in edges)
    with pytest.raises(ValueError): make_logo(tmp_path/'invalid.png',zoom=0)


def test_unknown_boundary_type_is_a_validation_error() -> None:
    with pytest.raises(ValueError, match="Invalid boundary geometry"):
        SceneConfig.from_mapping({"boundary": {"type": "Banana", "coordinates": []}})
