"""Small static SVG/PNG exporter. Cairo is imported only when exporting."""

from __future__ import annotations

from math import ceil, isfinite, pi, cos, sin
from pathlib import Path
from typing import Literal, TYPE_CHECKING

from .colors import rgb_normalized
from .drawing import DrawingContext, BUTT_CAP, ROUND_JOIN
from .node import Node
from .edge import Edge
from shapely.geometry import Polygon
if TYPE_CHECKING:
    from .graph import Graph



def draw_node(node: Node, context: DrawingContext, x_shift: float = 0, y_shift: float = 0) -> DrawingContext:
    context.new_path()
    x, y = node.center.x+x_shift, node.center.y+y_shift
    context.set_source_rgba(*rgb_normalized(node.color), node.opacity)
    if node.shape == 'circle':
        context.arc(x, y, (node.outer_radius+node.inner_radius)/2, 0, 2*pi)
        context.set_line_width(node.outer_radius-node.inner_radius)
        context.stroke()
    else:
        sides = {'square': 4, 'diamond': 4, 'triangle': 3, 'hexagon': 6}[node.shape]
        rotation = pi/4 if node.shape == 'square' else -pi/2
        # Opposite winding cuts a hollow centre. Every vertex stays inside the reserved disk.
        for radius, direction in ((node.outer_radius, 1), (node.inner_radius, -1)):
            if radius == 0: continue
            for i in range(sides):
                angle = rotation+direction*i*2*pi/sides
                point = (x+radius*cos(angle), y+radius*sin(angle))
                if i == 0: context.move_to(*point)
                else: context.line_to(*point)
            context.close_path()
        context.fill()
    return context


def draw_edge(edge: Edge, context: DrawingContext, x_shift: float = 0, y_shift: float = 0) -> DrawingContext:
    context.new_path()
    context.set_line_cap(BUTT_CAP)
    context.set_source_rgba(*rgb_normalized(edge.color), edge.opacity)
    context.set_line_width(edge.thickness/3 if edge.style == 'double' else edge.thickness)
    x, y = edge.start_point.x+x_shift, edge.start_point.y+y_shift
    dx, dy = -edge.nx, -edge.ny
    length = edge.length
    if edge.style == 'dotted':
        radius = min(edge.thickness/2, length/2)
        count = max(1, int(length/(edge.thickness*2.5)))
        for i in range(count):
            distance = length*(i+0.5)/count
            context.new_path()
            context.arc(x+dx*distance, y+dy*distance, radius, 0, 2*pi)
            context.fill()
        return context
    if edge.style == 'double':
        for offset in (-edge.thickness/3, edge.thickness/3):
            context.move_to(x-dy*offset, y+dx*offset)
            context.line_to(x+dx*length-dy*offset, y+dy*length+dx*offset)
    elif edge.style == 'dashed':
        count = max(1, ceil(length/(edge.thickness*6)))
        for i in range(count):
            start, end = length*i/count, min(length, length*(i+0.65)/count)
            context.move_to(x+dx*start, y+dy*start)
            context.line_to(x+dx*end, y+dy*end)
    else:
        context.move_to(x, y)
        context.line_to(x+dx*length, y+dy*length)
    context.stroke()
    return context


def draw_graph(graph: Graph, context: DrawingContext, x_shift: float = 0, y_shift: float = 0, *, draw_nodes: bool = True, draw_edges: bool = True,
               draw_outline: bool = True, draw_text: bool = True) -> DrawingContext:
    if draw_edges:
        for edge in graph.edges: draw_edge(edge, context, x_shift, y_shift)
    if draw_nodes:
        for node in graph.nodes: draw_node(node, context, x_shift, y_shift)
    if draw_outline and graph.draw_border:
        context.new_path()
        context.set_source_rgba(*rgb_normalized(graph.border_color), 1)
        context.set_line_width(graph.border_width)
        context.set_line_join(ROUND_JOIN)
        polygons = [graph.outline_polygon] if isinstance(graph.outline_polygon, Polygon) else list(graph.outline_polygon.geoms)
        for polygon in polygons:
            for ring in [polygon.exterior, *polygon.interiors]:
                for i, (x, y) in enumerate(ring.coords):
                    if i == 0: context.move_to(x+x_shift, y+y_shift)
                    else: context.line_to(x+x_shift, y+y_shift)
                context.close_path()
        context.stroke()
    if draw_text:
        for measured in graph.texts:
            context.save()
            try:
                context.translate(x_shift, y_shift)
                context.new_path()
                context.append_path(measured.path)
                context.set_source_rgba(*rgb_normalized(measured.text.color), measured.text.opacity)
                context.fill()
            finally:
                context.restore()
    return context


def export_graph(graph: Graph, path: str | Path, *, margin: float = 5, scale: float = 1, background: str | None = None,
                 frame: Literal['artwork', 'region'] = 'artwork') -> tuple[int, int]:
    """Export built geometry and return output dimensions in pixels/world-scaled units.

    Parameters
    ----------
    margin: Nonnegative world-unit margin around the selected frame.
    scale: Positive output units per world unit; shared by PNG and SVG.
    background: Hexadecimal RGB or None for transparency.
    frame: Crop to visible artwork, or retain the entire allowed region.

    Raises
    ------
    ValueError: Invalid options, unsupported suffix, or an empty artwork frame.
    ImportError: The optional render dependency is not installed.
    """
    if not isfinite(margin) or margin < 0 or not isfinite(scale) or scale <= 0: raise ValueError('Require a nonnegative margin and positive finite scale')
    if frame not in ('artwork', 'region'): raise ValueError('frame must be artwork or region')
    if graph.contours is not None and scale < graph.contours.readability.output_scale: raise ValueError('Export scale is below the readability design scale; regenerate or increase export scale')
    destination = Path(path)
    if destination.suffix.lower() not in ('.svg', '.png'): raise ValueError('Export path must end in .svg or .png')
    if frame == 'artwork' and not graph.nodes and not graph.draw_border and not graph.texts: raise ValueError('Cannot crop an empty graph to artwork')
    if background is not None: rgb_normalized(background)
    try:
        import cairo
    except ImportError as error:
        raise ImportError('Install graph-ics[render] to export SVG or PNG') from error
    if frame == 'artwork':
        min_x, min_y, max_x, max_y = graph.get_extent()
    else:
        min_x, min_y, max_x, max_y = graph.get_bounds()
        if graph.draw_border: min_x, min_y, max_x, max_y = min_x-graph.border_width/2, min_y-graph.border_width/2, max_x+graph.border_width/2, max_y+graph.border_width/2
        for measured in graph.texts:
            a, b, c, d = measured.bounds
            min_x, min_y, max_x, max_y = min(min_x, a), min(min_y, b), max(max_x, c), max(max_y, d)
    width, height = max(1, ceil((max_x-min_x+2*margin)*scale)), max(1, ceil((max_y-min_y+2*margin)*scale))
    destination.parent.mkdir(parents=True, exist_ok=True)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height) if destination.suffix.lower() == '.png' else cairo.SVGSurface(str(destination), width, height)
    try:
        context = cairo.Context(surface)
        if background is not None:
            context.set_source_rgb(*rgb_normalized(background))
            context.paint()
        context.scale(scale, scale)
        context.translate(margin-min_x, margin-min_y)
        draw_graph(graph, context)
        if isinstance(surface, cairo.ImageSurface): surface.write_to_png(str(destination))
    finally:
        surface.finish()
    return width, height
