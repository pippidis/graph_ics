"""Circular nodes with explicit inner/outer radii and collision clearance."""

from __future__ import annotations

from math import isfinite, cos, pi
from typing import Literal


from uuid import uuid4
from shapely.geometry import Point

from .colors import hex2rgb
from .drawing import DrawingContext
from .obj import Obj

NodeShape = Literal["circle", "square", "diamond", "triangle", "hexagon"]
NODE_SHAPES: tuple[NodeShape, ...] = ("circle", "square", "diamond", "triangle", "hexagon")

def shape_inradius_ratio(shape: NodeShape) -> float:
    """Inscribed/circumscribed radius; also scales a regular polygon ring's wall width."""
    return 1 if shape == 'circle' else cos(pi/{'square': 4, 'diamond': 4, 'triangle': 3, 'hexagon': 6}[shape])


NODE_DEFAULT_BUFFER = 1.0
NODE_DEFAULT_INNER_RADIUS = 1.0
NODE_DEFAULT_OUTER_RADIUS = 2.0
NODE_DEFAULT_MIN_EDGE_LENGTH = 1.0
NODE_DEFAULT_COLOR = '#545454'
NODE_DEFAULT_OPACITY = 1.0


class Node(Obj):
    """A hollow ring; its entire outer disk is reserved during placement.

    Coordinates and radii use world units. Buffer is additional node clearance;
    min_edge_length is additional pairwise node spacing, not endpoint clipping.
    Graphs assign deterministic IDs on acceptance; standalone nodes use UUIDs.
    """

    def __init__(self, x: float = 0, y: float = 0, is_seed_node: bool = False, color: str = NODE_DEFAULT_COLOR,
                 opacity: float = 1.0, outer_radius: float = 2.0, inner_radius: float = 1.0, buffer: float = 1.0, min_edge_length: float = 1.0, preferred_spacing: float = 0.0, colony_id: str | None = None, shape: NodeShape = "circle") -> None:
        if shape not in NODE_SHAPES: raise ValueError("Unknown node shape")
        self.shape = shape
        values = (x, y, opacity, outer_radius, inner_radius, buffer, min_edge_length, preferred_spacing)
        if not all(isfinite(value) for value in values): raise ValueError('Node values must be finite')
        if not 0 <= inner_radius < outer_radius: raise ValueError('Require 0 <= inner_radius < outer_radius')
        if buffer < 0 or min_edge_length < 0 or preferred_spacing < 0: raise ValueError('Node clearance must be nonnegative')
        if not 0 <= opacity <= 1: raise ValueError('Opacity must be between zero and one')
        hex2rgb(color)
        self.colony_id = colony_id
        self.center = Point(x, y)
        self.outer_radius = float(outer_radius)
        self.inner_radius = float(inner_radius)
        self.buffer = float(buffer)
        self.min_edge_length = float(min_edge_length)
        self.preferred_spacing = float(preferred_spacing)
        self.is_seed_node = is_seed_node
        self.color = color
        self.opacity = float(opacity)
        self.id = f'node_{uuid4().hex}'

    @property
    def buffer_radius(self) -> float:
        return self.outer_radius + self.buffer

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Visible disk bounds in min_x, min_y, max_x, max_y order."""
        x, y, radius = self.center.x, self.center.y, self.outer_radius
        return x-radius, y-radius, x+radius, y+radius

    def __str__(self) -> str:
        return f'({self.center.x}, {self.center.y})'

    def __repr__(self) -> str:
        return f'NODE ({self.center.x}, {self.center.y})'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node): return NotImplemented
        return bool(self.center == other.center)

    def overlap(self, other: Node) -> bool:
        """Reject overlapping or touching node clearance disks."""
        return self.distance_to(other) <= max(self.buffer_radius + other.buffer_radius + max(self.min_edge_length, other.min_edge_length), self.preferred_spacing, other.preferred_spacing)

    def distance_to(self, other: Node) -> float:
        return float(self.center.distance(other.center))

    def draw(self, context: DrawingContext, x_shift: float = 0, y_shift: float = 0) -> DrawingContext:
        """Compatibility wrapper for the shared renderer."""
        from .rendering import draw_node
        return draw_node(self, context, x_shift, y_shift)
