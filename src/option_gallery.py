"""Visual controls reference generated from the same public factories and renderer."""
from __future__ import annotations
from pathlib import Path
from html import escape
import json
from math import log1p
from .samples import build_example
from .gallery_page import gallery_page
from .node import NODE_SHAPES
from .edge import EDGE_STYLES
from .quality import AngleSettings
from .rendering import export_graph
from .styles import GraphStyle
from .validation import validate_graph
from .replay import EventRecorder, Playback
from .animation import ReplayRenderer
from .uk import population_field, population_region, WIDTH, HEIGHT, population_data

# Each CLI switch has a short definition and a visual example anchor. File-management
# switches share the artifact demonstration: they change storage, not graph geometry.
CLI_OPTIONS: tuple[tuple[str, str, str], ...] = (
    ('--fill-area', 'Search unfilled space with periodic reseeding; nodes remains a safety cap. Stops report exhausted search or limits, not complete packing.', 'scene-files'),
    ('--config', 'Load a complete JSON/YAML scene; file paths resolve beside that scene.', 'scene-files'),
    ('--gif', 'Export an opaque looping GIF instead of individual PNG frames.', 'animation'),
    ('--node-inner-radius / --node-outer-radius / --node-buffer', 'Inner and outer ring radii, and clearance to unrelated geometry, in world units.', 'scene-files'),
    ('--edge-thickness / --edge-node-distance / --edge-length-min / --edge-length-max', 'Full stroke width, ring-to-line gap, and visible length range in world units.', 'scene-files'),
    ('--example', 'Select a documented recipe; list shows names and describe explains it.', 'angles'),
    ('--palette', 'Choose colours for the complete scene; geometry stays the same unless text width changes.', 'palettes'),
    ('--seed', 'Change the random layout; reuse the seed to reproduce it.', 'seeds'),
    ('--nodes', 'Requested total population including seeds. Constraints can stop growth below it.', 'population'),
    ('--node-shape', 'Circle, square, diamond, triangle or hexagon; hollow unless inner radius is zero.', 'shapes'),
    ('--edge-style', 'Solid, dashed, dotted or double lines inside a collision-protected corridor.', 'lines'),
    ('--minimum-angle', 'Hard ban below this incident angle in degrees; straight continuation is 180.', 'angles'),
    ('--preferred-angle', 'Soft angular target; must be at least the hard minimum when nonzero.', 'angles'),
    ('--angle-penalty', 'Strength from 0 to 1 of soft rejection below the preferred angle.', 'angles'),
    ('--scale', 'Output units per world unit: larger image, same geometry. Compare native dimensions below.', 'output'),
    ('--margin', 'World-unit whitespace around the region, scaled with the image.', 'output'),
    ('--transparent', 'Leave the background transparent. Checkerboard indicates alpha in these previews.', 'output'),
    ('--output', 'PNG/SVG file for render; new folder for frames; gallery folder for gallery.', 'files'),
    ('--record', 'Save accepted events as JSONL while rendering; later replay needs no growth rerun.', 'animation'),
    ('--log', 'Read recorded geometry for frames. Recipe, seed and node target do not rebuild it.', 'animation'),
    ('--fps', 'Frames per second. More samples make the same event timeline smoother.', 'animation'),
    ('--seconds-per-event', 'Increase to slow the recorded growth; each event is given this duration.', 'animation'),
    ('--max-frames', 'Safety cap: an oversized frame sequence is rejected, not silently truncated.', 'animation'),
    ('--force', 'Allow render to replace its existing image or recording; does not affect appearance.', 'files'),
    ('--all-palettes', 'Expand every regular recipe across all ten palettes instead of the curated selection.', 'palettes'),
    ('--quick', 'Generate six small scenes plus this controls guide; omit for all recipes and large examples.', 'files'),
    ('--help / -h', 'Show command-specific usage and defaults; no image is generated.', 'files'),
)


def generate_controls(destination: Path) -> Path:
    figures = destination/'figures'
    figures.mkdir(parents=True, exist_ok=True)
    cards: list[str] = []
    records: list[dict[str, object]] = []
    generate_style_key(figures)

    def case(group: str, name: str, explanation: str, *, recipe: str = 'sprawl', seed: int = 7, nodes: int = 480,
             shape: str = 'circle', line: str = 'solid', palette: str = 'porcelain', scale: float = 1, margin: float = 16,
             transparent: bool = False, angles: AngleSettings | None = None) -> None:
        # Lookups retain the public Literal types after validating the gallery specification.
        selected_shape = next(value for value in NODE_SHAPES if value == shape)
        selected_line = next(value for value in EDGE_STYLES if value == line)
        graph = build_example(recipe, seed=seed, nodes=nodes, palette=palette, node_shape=selected_shape, edge_style=selected_line, angles=angles)
        graph.build()
        validate_graph(graph)
        stem = 'control-'+name
        background = None if transparent else GraphStyle.named(palette).background
        dimensions = export_graph(graph, figures/(stem+'.png'), background=background, scale=scale, margin=margin, frame='region')
        export_graph(graph, figures/(stem+'.svg'), background=background, scale=scale, margin=margin, frame='region')
        command = f'graph-ics render --example {recipe} --palette {palette} --nodes {nodes} --seed {seed} --node-shape {shape} --edge-style {line} --scale {scale} --margin {margin}'
        if transparent: command += ' --transparent'
        if angles is not None: command += f' --minimum-angle {angles.minimum} --preferred-angle {angles.preferred} --angle-penalty {angles.penalty}'
        command += f' --output examples/output/{name}.png'
        records.append(dict(group=group, name=name, explanation=explanation, command=command, dimensions=dimensions, nodes=len(graph.nodes)))
        cards.append(f'<article class="{group}"><h3>{escape(name.replace("-", " ").title())}</h3><a class="alpha" href="figures/{stem}.png"><img src="figures/{stem}.png" loading="lazy" alt="{escape(name)}"></a><p>{escape(explanation)}</p><p>{dimensions[0]} &times; {dimensions[1]}; {len(graph.nodes)} nodes</p><details><summary>Reproduce / SVG</summary><pre class="command">{escape(command)}</pre><a href="figures/{stem}.svg">SVG</a></details></article>')

    sections: list[str] = []
    def section(group: str, title: str, explanation: str) -> None:
        sections.append(f'<section id="{group}"><h2>{title}</h2><p>{explanation}</p><div class="grid">'+''.join(card for card in cards if card.startswith(f'<article class="{group}"'))+'</div></section>')

    for shape in NODE_SHAPES: case('shapes', 'shape-'+shape, 'Same layout and outer radius. Polygon corners fit inside the reserved circle; endpoint gaps can therefore look larger.', shape=shape)
    section('shapes', 'Node shapes', 'These vary only the visible node outline. Shape choice is preserved by replay.<br><img class="style-key" src="figures/style-key.png" alt="Enlarged shape and connection style key">')
    for line in EDGE_STYLES: case('lines', 'line-'+line, 'Same layout and full-width collision corridor. Dashed gaps remain reserved; double lines split the width into thirds.', recipe='lines', line=line)
    section('lines', 'Connection patterns', 'Line patterns are rendering styles on straight connections. Curves, arrows and moving paths are not implemented.')
    for name, angles in (('free', AngleSettings()), ('hard-45', AngleSettings(45)), ('soft-80', AngleSettings(0,80,0.9)), ('strict-60-90', AngleSettings(60,90,0.9))):
        case('angles', 'angles-'+name, f'Hard minimum {angles.minimum} degrees; preference {angles.preferred}; penalty {angles.penalty}. Identical seed and target, different rejection decisions.', angles=angles, nodes=480)
    section('angles', 'Angle restrictions', 'Hard rules forbid small junctions; soft penalties merely make them less likely. Stricter settings change the subsequent random growth and can reduce coverage.')
    for seed in (7,19): case('seeds', f'seed-{seed}', 'Same settings, different random layout.', seed=seed)
    section('seeds', 'Random seeds', 'Compare patterns while holding all geometry controls fixed.')
    for count in (60,180,480): case('population', f'nodes-{count}', 'Increasing the requested population fills more of the available canvas.', nodes=count)
    section('population', 'Population target', 'A target is not a promise. Every candidate must fit and the attempt budget is finite.')
    for name in GraphStyle.palette_names(): case('palettes', 'palette-'+name, 'Only the colour scheme changes here; no text means the exact same geometry.', palette=name)
    section('palettes', 'Colour schemes', 'Porcelain is white; Linen and Light are warm near-white alternatives. Arctic is a dark blue ice palette.')
    for name, scale, margin, alpha in (('normal',1,16,False),('double-resolution',2,16,False),('wide-margin',1,80,False),('transparent',1,16,True)):
        case('output', name, 'Compare the dimensions and whitespace; growth geometry is unchanged.', scale=scale, margin=margin, transparent=alpha)
    section('output', 'Export scale, margin and transparency', 'Thumbnails fit the same column width. Open the image to compare native resolution; SVG remains vector. Alpha is shown over a checkerboard.')

    from .scene_gallery import generate_scene_gallery
    sections.append(generate_scene_gallery(destination))
    graph = build_example('sprawl', nodes=480, palette='porcelain')
    with EventRecorder(graph, path=destination/'example-growth.jsonl') as recorder: graph.build()
    log = recorder.snapshot()
    renderer = ReplayRenderer(Playback(log, seconds_per_event=0.015), background='#ffffff')
    gif = figures/'growth.gif'
    if gif.exists(): gif.unlink()
    renderer.export_gif(gif, fps=15, max_frames=300)
    from PIL import Image
    with Image.open(gif) as animation:
        animation.seek(getattr(animation,'n_frames',1)-1)
        animation.convert('RGB').save(figures/'growth-poster.png')
    sections.append('<section id="animation"><h2>Watch the graph grow</h2><p>A complete 480-node growth run, followed by a pause on the finished artwork. Use Play animation to watch the sequence, or pause to return to the completed artwork. <a href="figures/growth.gif" download>Download GIF</a> or <a href="example-growth.jsonl">download the event log</a>.</p><img class="style-key" src="figures/growth-poster.png" data-poster="figures/growth-poster.png" data-animation="figures/growth.gif" alt="Animated growth from seeds to a filled graph"><p>Higher fps gives more samples of the same timeline; seconds per event changes speed. GIF needs an opaque background and has a limited colour palette; use PNG frames for transparency and full colour. The exporter rejects oversized frame or pixel budgets before rendering.</p><pre class="command">graph-ics frames --log docs/example-growth.jsonl --gif --palette porcelain --fps 15 --seconds-per-event 0.015 --max-frames 300 --output examples/output/growth.gif</pre></section>')
    sections.append('<section id="files"><h2>Commands and files</h2><p>list and describe print information; render writes one PNG/SVG, optionally with a JSONL log; frames writes a numbered PNG sequence; gallery writes this library. --force only permits overwriting render outputs. --quick selects the six-scene smoke gallery; this controls page is still included. --output chooses their location, without altering the artwork.</p><pre class="command">graph-ics list\ngraph-ics describe density\ngraph-ics render --help\ngraph-ics gallery --output examples/gallery</pre><p>All generated figures sit in figures/ below the gallery index. Open the PNG/SVG links above to compare file formats visually.</p></section>')
    rows = ''.join(f'<tr><td><code>{escape(option)}</code></td><td>{escape(note)}</td><td><a href="#{anchor}">Visual example</a></td></tr>' for option,note,anchor in CLI_OPTIONS)
    anchors = [('scene-files','Dimensions & scenes'),('shapes','Shapes'),('lines','Connections'),('angles','Angles'),('seeds','Seeds'),('population','Population'),('palettes','Palettes'),('output','Export'),('animation','Replay'),('files','Files')]
    navigation = '<nav class="section-nav" aria-label="Visual guide sections">'+''.join(f'<a href="#{anchor}">{label}</a>' for anchor,label in anchors)+'</nav>'
    intro = '<header class="intro"><span class="eyebrow">Visual guide</span><h1>Change one thing.</h1><p>Compare the controls side by side. Each example explains what changes, what stays fixed, and how to reproduce the result.</p></header>'
    reference = '<details id="cli"><summary>All command-line options</summary><div class="table-scroll"><table><thead><tr><th scope="col">Option</th><th scope="col">What it does</th><th scope="col">Example</th></tr></thead><tbody>'+rows+'</tbody></table></div></details>'
    html = gallery_page('Visual guide', intro+navigation+reference+''.join(sections), active='controls')
    path = destination/'controls.html'
    path.write_text(html,encoding='utf-8')
    (destination/'controls-manifest.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    generate_population_preview(destination)
    return path


def generate_population_preview(destination: Path) -> None:
    import cairo
    from shapely.geometry import Point
    raster, region = population_field(), population_region()
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 550,1000)
    context = cairo.Context(surface)
    context.set_source_rgb(1,1,1)
    context.paint()
    for row in range(500):
        for column in range(275):
            x,y = (column+0.5)*WIDTH/275, (row+0.5)*HEIGHT/500
            if not region.covers(Point(x,y)): continue
            value = min(1,log1p(raster.sample(x,y))/log1p(10000))
            context.set_source_rgb(0.86-0.75*value,0.94-0.55*value,0.97-0.4*value)
            context.rectangle(column*2,row*2,2,2)
            context.fill()
    surface.write_to_png(str(destination/'figures'/'uk-density-input.png'))
    metadata = population_data()['metadata']
    graph_preview = '<a href="figures/uk_population-porcelain.png"><img src="figures/uk_population-porcelain.png" alt="UK density-guided graph"></a>' if (destination/'figures'/'uk_population-porcelain.png').exists() else '<p>Run the full gallery (omit --quick) or the command below to generate the UK graph.</p>'
    content = '<header class="intro"><span class="eyebrow">Data-driven growth</span><h1>The shape of a population.</h1><p>UK population-density estimates guide a network inside the country boundary. Cities become finer and denser; rural areas leave more breathing room.</p></header>'
    content += '<div class="comparison"><figure><img src="figures/uk-density-input.png" alt="WorldPop 2020 population density across the UK"><figcaption>Input: 2020 estimates, persons per square kilometre. Pale blue is near zero; dark blue is 10,000 or more. The colour scale is logarithmic.</figcaption></figure><figure>'+graph_preview+'<figcaption>Output: a density-guided graph. Open the image for its full resolution. Nodes do not represent individual people.</figcaption></figure></div>'
    content += '<section><h2>Make this example</h2><pre class="command">graph-ics render --example uk_population --palette porcelain --output examples/output/uk.png</pre><p>The input is bundled with the library and runs offline. It includes Northern Ireland and UK islands, and excludes the Republic of Ireland. Small islands and narrow coastal features may remain empty.</p></section>'
    content += '<section><h2>From density to spacing</h2><p>Population spans a wide range. A logarithmic mapping compresses the extremes so city structure remains readable: <code>t = min(1, log(1+density)/log(10001))</code>. Preferred spacing is <code>5 + 20*(1-t)</code>; geometry scale is <code>0.45 + 0.9*(1-t)</code>. Cities receive smaller, closer nodes. Collision checks and finite attempt budgets still limit packing.</p><p>This is an artistic transformation, not a linear population map. The source raster is resampled from approximately 1 km to 360 by 560 cells. The boundary is simplified; no-data samples become zero. Pixel centres share the boundary projection: longitude scaled by cos(55 degrees), north at the top. This display projection is not equal-area.</p></section>'
    content += '<section><h2>Different uses of the same map</h2><p>Population is just one scalar input. Compare spacing-only, colour-only, and coordinated size/spacing below. The scene guide also demonstrates abstract radial fields and painted rasters, suitable for visual emphasis or any other spatial measurement.</p><div class="grid">'+''.join(f'<article><h3>{title} / {palette}</h3><a href="figures/{name}-{palette}.png"><img loading="lazy" src="figures/{name}-{palette}.png" alt="{title}"></a><pre class="command">graph-ics render --example {name} --palette {palette} --output examples/output/{name}-{palette}.png</pre></article>' for recipe,title in [('uk_population','UK: size and spacing'),('uk_density_only','UK: spacing only'),('uk_colors','UK: colour only'),('spain_population','Spain: size and spacing')] for palette in ('porcelain','arctic') for name in [recipe] if (destination/'figures'/f'{name}-{palette}.png').exists())+'</div><p>Spain uses the same 2020 WorldPop source and Natural Earth boundaries. The crop includes mainland Spain and the Balearic Islands; the Canary Islands are excluded. Small territories may be empty after geometric filtering.</p></section>'
    content += '<section><h2>Sources</h2><p><a href="https://www.worldpop.org/doi/10.5258/SOTON/WP00674">WorldPop / CIESIN, Global High Resolution Population Denominators</a>, 2020 density estimates, distributed under <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. Boundary: <a href="https://www.naturalearthdata.com/about/terms-of-use/">Natural Earth</a> 5.1.2, public domain.</p><details><summary>Download query and provenance</summary><pre>'+escape(json.dumps(metadata,indent=2))+'</pre></details></section>'
    (destination/'uk_population.html').write_text(gallery_page('UK population map', content, active='uk'),encoding='utf-8')



def generate_style_key(figures: Path) -> None:
    import cairo
    from .node import Node
    from .edge import Edge
    from .rendering import draw_node, draw_edge
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 760, 280)
    context = cairo.Context(surface)
    context.set_source_rgb(1,1,1)
    context.paint()
    context.set_font_size(15)
    for i, shape in enumerate(NODE_SHAPES):
        draw_node(Node(75+i*150,55,outer_radius=25,inner_radius=15,color='#284d68',shape=shape),context)
        context.move_to(40+i*150,105)
        context.show_text(shape)
    for i, style in enumerate(EDGE_STYLES):
        first, second = Node(25+i*185,185,outer_radius=9,inner_radius=5), Node(155+i*185,185,outer_radius=9,inner_radius=5)
        draw_edge(Edge(first,second,thickness=7,color='#284d68',style=style),context)
        draw_node(first,context)
        draw_node(second,context)
        context.move_to(60+i*185,235)
        context.show_text(style)
    surface.write_to_png(str(figures/'style-key.png'))
