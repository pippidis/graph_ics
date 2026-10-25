"""Cropped graph_ics wordmark: a window into a larger, continuing network."""
from pathlib import Path
from math import ceil, isfinite
from dataclasses import replace
from shapely.geometry import box
from .styles import GraphStyle
from .graph import Graph
from .text import Text
from .growth import GrowthSettings
from .coverage import CoverageSettings
from .colors import rgb_normalized
from .validation import validate_graph


def make_logo(path: str | Path, *, width: float = 600, height: float = 250, zoom: float = 1.15, palette: str = 'porcelain', seed: int = 7, scale: float = 1) -> tuple[int, int]:
    """Generate a PNG/SVG wordmark, cropping a larger network at the viewport edges.

    Width/height are world units; scale controls output resolution. Zoom increases
    network dimensions while keeping the wordmark fitted to the same frame.
    The default uses the Porcelain white background and red text. Seed fixes growth.
    """
    if not all(isfinite(v) and v > 0 for v in (width,height,zoom,scale)): raise ValueError('Logo dimensions, zoom and scale must be positive and finite')
    destination=Path(path)
    if destination.suffix.lower() not in ('.png','.svg'): raise ValueError('Logo output must be PNG or SVG')
    if width*height*scale*scale > 40_000_000: raise ValueError('Logo exceeds the 40-million-pixel output budget')
    graph = _build_logo(width,height,zoom,palette,seed)
    return _export_logo(graph,destination,width,height,scale,palette)


def _build_logo(width: float, height: float, zoom: float, palette: str, seed: int) -> Graph:
    base=GraphStyle.named(palette)
    style=replace(base,node_inner_radius=base.node_inner_radius*zoom,node_outer_radius=base.node_outer_radius*zoom,node_buffer=base.node_buffer*zoom,
                  edge_thickness=base.edge_thickness*zoom,edge_node_distance=base.edge_node_distance*zoom,edge_length_min=base.edge_length_min*zoom,edge_length_max=base.edge_length_max*zoom)
    text=Text('graph_ics',0,0,size=100,bold=True,padding=2.5*zoom,exclusion_mode='glyph',color=style.text_color)
    measured=text.measure()
    x0,y0,x1,y1=measured.bounds
    factor=min(width*0.79/(x1-x0),height*0.40/(y1-y0))
    fitted=replace(text,size=text.size*factor)
    x0,y0,x1,y1=fitted.measure().bounds
    fitted=replace(fitted,x=width/2-(x0+x1)/2,y=height/2-(y0+y1)/2)
    bleed=max(80*zoom,style.edge_length_max*3)
    area=(width+2*bleed)*(height+2*bleed)
    cap=min(20000,max(100,ceil(area/(100*zoom*zoom))))
    graph=style.create_graph(target_nodes=cap,target_seed_nodes=min(20,cap),seed=seed,outline_polygon=box(-bleed,-bleed,width+bleed,height+bleed),texts=(fitted,))
    graph.growth(settings=GrowthSettings(fill_area=True,total_attempts=min(500000,cap*60),coverage=CoverageSettings(tile_size=30*zoom,reseed_attempts=2500)))
    graph.build()
    validate_graph(graph)
    return graph


def _export_logo(graph: Graph, destination: Path, width: float, height: float, scale: float, palette: str) -> tuple[int,int]:
    import cairo
    style=GraphStyle.named(palette)
    dimensions=(ceil(width*scale),ceil(height*scale))
    destination.parent.mkdir(parents=True,exist_ok=True)
    surface=cairo.ImageSurface(cairo.FORMAT_ARGB32,*dimensions) if destination.suffix.lower()=='.png' else cairo.SVGSurface(str(destination),*dimensions)
    try:
        context=cairo.Context(surface)
        context.scale(scale,scale)
        if style.background is not None:
            context.set_source_rgb(*rgb_normalized(style.background))
            context.paint()
        context.rectangle(0,0,width,height)
        context.clip()
        graph.draw(context)
        if destination.suffix.lower()=='.png': surface.write_to_png(str(destination))
    finally: surface.finish()
    return dimensions


def generate_logos(directory: str | Path = 'docs/logo') -> Path:
    """Write landscape, banner, wide banner, square and portrait assets beneath a logo index."""
    from .gallery_page import gallery_page
    output=Path(directory)
    figures=output/'figures'
    figures.mkdir(parents=True,exist_ok=True)
    variants=(('landscape',600,250),('banner',1000,250),('wide-banner',2000,250),('square',512,512),('portrait',500,750))
    cards=[]
    for name,width,height in variants:
        graph=_build_logo(width,height,1.15,'porcelain',7)
        for suffix in ('png','svg'): _export_logo(graph,figures/f'{name}.{suffix}',width,height,1,'porcelain')
        _export_logo(graph,figures/f'{name}@2x.png',width,height,2,'porcelain')
        cards.append(f'<article><h2>{name.title()}</h2><a href="figures/{name}.png"><img src="figures/{name}.png" alt="graph_ics {name} logo, cropped from a continuing network"></a><p>{width} &times; {height}; double resolution {width*2} &times; {height*2}.</p><p><a href="figures/{name}.svg" download>SVG</a> &middot; <a href="figures/{name}.png" download>PNG</a> &middot; <a href="figures/{name}@2x.png" download>PNG 2&times;</a></p><pre class="command">from graph_ics import make_logo\nmake_logo("logo.png", width={width}, height={height}, scale=2)</pre></article>')
    content='<header class="intro"><span class="eyebrow">Wordmark</span><h1>graph_ics</h1><p>A close-up window into an ongoing network. The graph is generated beyond the frame, then clipped: partial rings and connections at the edges suggest that it continues.</p></header><p>The default is Porcelain: white, blue-grey connections and red lettering. Width and height choose the composition; scale changes resolution. Zoom enlarges the network texture without enlarging the wordmark. Seed changes the layout; palette changes its colours. SVG scales to any display size.</p><div class="grid">'+''.join(cards)+'</div>'
    content += generate_icons(output)
    html=gallery_page('Logo',content,active='logo')
    index=output/'index.html'
    index.write_text(html,encoding='utf-8')
    return index


def make_icon(path: str | Path, *, size: int = 256) -> tuple[int, int]:
    """Draw the five-node branching icon as PNG, SVG or a multi-size ICO."""
    if type(size) is not int or not 16 <= size <= 2048: raise ValueError('Icon size must be an integer from 16 to 2048')
    destination=Path(path)
    suffix=destination.suffix.lower()
    if suffix not in ('.png','.svg','.ico'): raise ValueError('Icon output must be PNG, SVG or ICO')
    import cairo
    from io import BytesIO
    dimension=256 if suffix=='.ico' else size
    destination.parent.mkdir(parents=True,exist_ok=True)
    surface=cairo.SVGSurface(str(destination),dimension,dimension) if suffix=='.svg' else cairo.ImageSurface(cairo.FORMAT_ARGB32,dimension,dimension)
    try:
        context=cairo.Context(surface)
        context.scale(dimension/64,dimension/64)
        context.set_source_rgb(1,1,1)
        context.paint()
        points=((30,32),(12,12),(53,17),(43,53),(10,48))
        context.set_source_rgb(*rgb_normalized('#7f9baa'))
        context.set_line_width(2.1)
        for index in (1,2,3,4):
            x,y=points[0]
            nx,ny=points[index]
            dx,dy=nx-x,ny-y
            length=(dx*dx+dy*dy)**0.5
            context.move_to(x+dx*6.7/length,y+dy*6.7/length)
            context.line_to(nx-dx*6.7/length,ny-dy*6.7/length)
        context.stroke()
        for index,(x,y) in enumerate(points):
            context.new_path()
            context.arc(x,y,4.7,0,6.283185307179586)
            context.set_source_rgb(*rgb_normalized('#a64152' if index==0 else '#284d68'))
            context.set_line_width(2.2)
            if index==0: context.fill()
            else: context.stroke()
        if suffix=='.png': surface.write_to_png(str(destination))
        elif suffix=='.ico':
            from PIL import Image
            buffer=BytesIO()
            surface.write_to_png(buffer)
            buffer.seek(0)
            with Image.open(buffer) as image: image.save(destination,format='ICO',sizes=[(value,value) for value in (16,24,32,48,64,128,256)])
    finally: surface.finish()
    return dimension,dimension


def generate_icons(directory: str | Path) -> str:
    """Write browser icons and return their logo-page download section."""
    figures=Path(directory)/'figures'
    make_icon(figures/'favicon.svg')
    make_icon(figures/'favicon.ico')
    for size in (16,32,64,180,512): make_icon(figures/f'icon-{size}.png',size=size)
    links=' &middot; '.join(f'<a href="figures/icon-{size}.png" download>{size}px PNG</a>' for size in (16,32,64,180,512))
    return '<section id="website-icon"><h2>Website icon</h2><p>The selected small branching graph: four hollow blue nodes connected to one red junction, simplified for browser tabs and bookmarks.</p><p><img src="figures/icon-64.png" width="64" height="64" alt="graph_ics website icon"> <img src="figures/icon-32.png" width="32" height="32" alt="32 pixel preview"> <img src="figures/icon-16.png" width="16" height="16" alt="16 pixel preview"></p><p><a href="figures/favicon.svg" download>SVG</a> &middot; <a href="figures/favicon.ico" download>Multi-size ICO</a> &middot; '+links+'</p><pre class="command">from graph_ics import make_icon\nmake_icon("favicon.ico")\nmake_icon("icon.png", size=512)</pre></section>'
