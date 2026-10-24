"""Reproducible scene-file comparisons for geometry, typography and spatial maps."""
from pathlib import Path
from typing import Any
from html import escape
import json
import re
import yaml
from .scene import SceneConfig
from .rendering import export_graph
from .validation import validate_graph


class SceneDumper(yaml.SafeDumper):
    """Keep numeric vectors on one line, with nested rings and objects indented."""


def _numeric_sequence(dumper: SceneDumper, values: list[Any]) -> yaml.SequenceNode:
    return dumper.represent_sequence('tag:yaml.org,2002:seq', values, flow_style=bool(values) and all(type(value) in (int,float) for value in values))


SceneDumper.add_representer(list, _numeric_sequence)


def scene_json(data: dict[str, Any]) -> str:
    """Indent scene objects while keeping coordinate pairs and numeric rows compact."""
    text=json.dumps(data,indent=2,allow_nan=False)
    return re.sub(r'\[\s*(-?\d[^\[\]"{}]*?)\s*\]', lambda match: '['+' '.join(match[1].split())+']', text)+'\n'


def scene_yaml(data: dict[str, Any]) -> str:
    """Write readable scene YAML without splitting numeric vectors into scalars."""
    return yaml.dump(data,Dumper=SceneDumper,sort_keys=False,width=160)


def scene_examples() -> dict[str, tuple[str, dict[str, Any]]]:
    base: dict[str, Any] = dict(version=1,palette='porcelain',width=600,height=360,nodes=650,seed=7,
                                growth=dict(total_attempts=35000,refill_passes=2,coverage=dict(tile_size=30,reseed_attempts=1200)))
    result: dict[str, tuple[str, dict[str, Any]]] = {}
    def add(name: str, note: str, **values: Any) -> None: result[name] = (note,dict(base,**values))
    for name,style,note in (
        ('fine-rings',dict(node_outer_radius=3,node_inner_radius=2.5),'Radius 3, inner radius 2.5: a 0.5-unit wall.'),
        ('heavy-rings',dict(node_outer_radius=5,node_inner_radius=2),'Radius 5, inner radius 2: a 3-unit wall. Larger nodes consume more space.'),
        ('solid-nodes',dict(node_outer_radius=3,node_inner_radius=0),'Zero inner radius makes a filled node.'),
        ('fine-lines',dict(edge_thickness=0.5),'Connection width 0.5. Zoom in to inspect fine strokes.'),
        ('heavy-lines',dict(edge_thickness=3),'Connection width 3. The whole stroke must fit.'),
        ('short-links',dict(edge_length_min=4,edge_length_max=8),'Visible connection length 4 to 8; shorter steps create a finer texture.'),
        ('long-links',dict(edge_length_min=25,edge_length_max=40),'Visible connection length 25 to 40; long steps leave larger openings.'),
        ('wide-gaps',dict(edge_node_distance=4),'Four world units separate each ring from its connection.'),
        ('wide-buffers',dict(node_buffer=5),'A five-unit buffer keeps unrelated nodes and edges further apart.')
    ): add(name,note,style=style)
    text = dict(content='graph_ics',x=300,y=210,size=95,align='center',bold=True,padding=2,color='#a64152')
    add('text-box','Measured rectangle: useful for clear labels, but excludes spaces between letters.',texts=[dict(text,exclusion_mode='box')])
    add('text-hug','Glyph exclusion: branches can enter spaces between letters and sufficiently large letter holes.',texts=[dict(text,exclusion_mode='glyph')])
    add('graph-lettering','The graph itself forms the letters. No text fill is drawn; counters remain empty.',nodes=3200,seeds=30,
        text_region=dict(content='graph_ics',x=0,y=260,size=300,bold=True,padding=0),
        style=dict(node_outer_radius=2,node_inner_radius=1,node_buffer=0.3,edge_thickness=0.7,edge_node_distance=0.5,edge_length_min=3,edge_length_max=7),
        growth=dict(fill_area=True,total_attempts=180000,seed_attempts=2000,refill_passes=2,coverage=dict(tile_size=20,max_tiles=12000,reseed_attempts=6000,reseed_interval=100,seed_components=True)))
    ramp=dict(field=dict(kind='gradient',axis='x'),colors=['#246b87','#e7b96d','#a64152'])
    add('colour-gradient','A continuous colour field, sampled at node centres and edge midpoints. It does not alter geometry.',color_map=ramp)
    add('colour-raster','A painted scalar raster becomes a colour map through bilinear interpolation.',color_map=dict(field=dict(kind='raster',pixels=[[0,0.4,1],[0.8,0.2,0.7],[1,0.5,0]]),colors=['#274f7c','#a7c6ad','#b34d6a']))
    add('radial-density','An abstract focal point, not population: density rises smoothly toward the centre.',fields=dict(density=dict(kind='radial',min=0.0008,max=0.006,sigma=110)))
    add('painted-density','A coarse painted mask creates bands of dense and open texture. Any scalar measurement can play this role.',fields=dict(density=dict(kind='raster',pixels=[[0.001,0.006,0.001],[0.006,0.001,0.006],[0.001,0.006,0.001]])))
    add('variable-dimensions','Coordinated scale changes radius, wall, gap, line width and length together; colour remains independent.',fields=dict(coordinated_scale=dict(kind='gradient',min=0.55,max=1.5)),color_map=ramp)
    boundary=dict(type='Polygon',coordinates=[[[20,20],[580,20],[580,340],[350,340],[300,240],[250,340],[20,340],[20,20]],[[250,70],[350,70],[350,150],[250,150],[250,70]]])
    for name,visible,width,color in [('boundary-hidden',False,0.5,'#527e9e'),('boundary-fine',True,0.5,'#527e9e'),('boundary-bold',True,4,'#a64152')]:
        add(name,'Same GeoJSON outline and hole. Border visibility, colour and width affect rendering; containment always uses the supplied polygon.',boundary=boundary,boundary_style=dict(visible=visible,width=width,color=color))
    add('area-fill', 'Area fill searches beyond the requested local tile populations; the node count is a safety cap. Compare stop reason and tile coverage, not just count.',nodes=2200,growth=dict(fill_area=True,total_attempts=100000,refill_passes=1,refill_attempts=10000,coverage=dict(tile_size=25,reseed_attempts=3000)))
    return result


def generate_scene_gallery(destination: Path) -> str:
    folder=destination/'scenes'
    folder.mkdir(parents=True,exist_ok=True)
    cards: list[str] = []
    for name,(note,data) in scene_examples().items():
        (folder/(name+'.json')).write_text(scene_json(data),encoding='utf-8')
        (folder/(name+'.yaml')).write_text(scene_yaml(data),encoding='utf-8')
        scene=SceneConfig.from_mapping(data)
        scene.graph.build()
        validate_graph(scene.graph)
        for suffix in ('png','svg'): export_graph(scene.graph,destination/'figures'/f'scene-{name}.{suffix}',frame='region',background=scene.background)
        coverage = scene.graph.growth().coverage_report() if scene.graph.growth().coverage else None
        fill_note = f'{coverage.occupied_tiles}/{coverage.usable_tiles} occupied tiles; {coverage.occupied_tile_area_fraction:.1%} of tile area has a node. This is a coarse coverage measure, not solid ink coverage.' if coverage else ''
        cards.append(f'<article><h3>{escape(name.replace("-"," ").title())}</h3><a href="figures/scene-{name}.png"><img loading="lazy" src="figures/scene-{name}.png" alt="{escape(note)}"></a><p>{escape(note)}</p><p>{len(scene.graph.nodes)} nodes of {scene.graph.target_nodes} requested. Stop: {scene.graph.growth().status.value}. {fill_note}</p><p><a href="scenes/{name}.json">JSON scene</a> &middot; <a href="scenes/{name}.yaml">YAML scene</a> &middot; <a href="figures/scene-{name}.svg">SVG</a></p><details><summary>Settings and command</summary><pre class="command">graph-ics render --config docs/scenes/{name}.yaml --output examples/output/{name}.png</pre><pre>{escape(scene_json(data).rstrip())}</pre></details></article>')
        print(f'Scene {name}: {len(scene.graph.nodes)} nodes',flush=True)
    return '<section id="scene-files"><h2>Dimensions, maps, boundaries and lettering</h2><p>Each example is a complete downloadable JSON or YAML scene. Edit its values, then pass it to <code>render --config</code> or <code>frames --config</code>. Coordinates and dimensions use world units; output scale controls pixels per world unit.</p><p>Ring wall = outer radius minus inner radius. A hollow circle needs inner diameter &times; output scale large enough to see; a one-pixel wall is a useful starting point. A letter stroke must be wider than twice the outer radius to fit a node, and longer than two radii plus two gaps plus the visible edge length to fit a connection. Increase the font size or reduce geometry dimensions for thin strokes. Fonts are resolved locally, so use the same installed font to reproduce outlines across machines.</p><p>Boundary files accept GeoJSON Polygon or MultiPolygon, including holes; a file path resolves relative to the scene. <code>text_region</code> uses glyphs as the allowed region; <code>texts[].exclusion_mode: glyph</code> excludes glyphs instead. Border strokes are centred on the supplied boundary and do not add collision padding. Density is a packing request, not an exact count.</p><div class="grid">'+''.join(cards)+'</div></section>'
