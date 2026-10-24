"""Straight edges clipped away from node rings, with butt-ended strokes."""

from __future__ import annotations

from math import isfinite
from typing import Literal


from shapely.geometry import LineString, Point, Polygon

from .colors import hex2rgb
from .drawing import DrawingContext
from .node import Node
from .obj import Obj
from .vector import Vector

EdgeStyle = Literal["solid", "dashed", "dotted", "double"]
EDGE_STYLES: tuple[EdgeStyle, ...] = ("solid", "dashed", "dotted", "double")

EDGE_DEFAULT_THICKNESS = 1.0
EDGE_DEFAULT_COLOR = '#a6b7c8'
EDGE_DEFAULT_OPACITY = 1.0
EDGE_DEFAULT_NODE_DISTANCE = 1.0


class Edge(Obj):
    """A visible segment separated from each endpoint ring by a fixed gap.

    The footprint is the full butt-ended stroke rectangle. Node coordinates
    must remain fixed after construction; moving geometry is a future stage.
    """

    def __init__(self, start_node: Node, end_node: Node, thickness: float = 1.0, color: str = EDGE_DEFAULT_COLOR,
                 opacity: float = 1.0, edge_node_distance: float = 1.0, style: EdgeStyle = "solid") -> None:
        if style not in EDGE_STYLES: raise ValueError("Unknown edge style")
        self.style = style
        if not all(isfinite(v) for v in (thickness, opacity, edge_node_distance)): raise ValueError('Edge values must be finite')
        if thickness <= 0 or edge_node_distance < 0: raise ValueError('Thickness must be positive and endpoint gap nonnegative')
        if not 0 <= opacity <= 1: raise ValueError('Opacity must be between zero and one')
        hex2rgb(color)
        self.start_node, self.end_node = start_node, end_node
        self.thickness, self.opacity = float(thickness), float(opacity)
        self.color, self.edge_node_distance = color, float(edge_node_distance)
        self.vector = Vector(start_node.center, end_node.center)
        # Vector retains the historical p1-p2 direction; subtraction goes toward p2.
        self.nx, self.ny = self.vector.get_normalized()
        if self.vector.length <= start_node.outer_radius + end_node.outer_radius + 2*edge_node_distance:
            raise ValueError('Nodes are too close for a positive visible edge length')
        self.start_point = Point(start_node.center.x-self.nx*(start_node.outer_radius+edge_node_distance), start_node.center.y-self.ny*(start_node.outer_radius+edge_node_distance))
        self.end_point = Point(end_node.center.x+self.nx*(end_node.outer_radius+edge_node_distance), end_node.center.y+self.ny*(end_node.outer_radius+edge_node_distance))
        self.line_string = LineString([self.start_point, self.end_point])
        self.footprint: Polygon = self.line_string.buffer(self.thickness/2, cap_style='flat')

    @property
    def length(self) -> float:
        """Length of the visible segment, excluding endpoint gaps and rings."""
        return float(self.line_string.length)

    def overlap(self, other: Edge | Node) -> bool:
        """Check full strokes and unrelated node clearances, including touching.

        Endpoint nodes are allowed: their explicit edge gap controls attachment.
        Shared-node edges still undergo visible-stroke collision checks.
        """
        if isinstance(other, Edge): return bool(self.footprint.intersects(other.footprint))
        if other is self.start_node or other is self.end_node: return False
        return float(self.footprint.distance(other.center)) <= other.buffer_radius

    def draw(self, context: DrawingContext, x_shift: float = 0, y_shift: float = 0) -> DrawingContext:
        """Compatibility wrapper for the shared renderer."""
        from .rendering import draw_edge
        return draw_edge(self, context, x_shift, y_shift)
