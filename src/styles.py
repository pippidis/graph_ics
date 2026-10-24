"""Reusable visual proportions with typed graph construction."""
from __future__ import annotations
from dataclasses import dataclass
from collections.abc import Sequence
from math import isfinite
from shapely.geometry import Polygon, MultiPolygon, box
from .graph import Graph
from .node import Node, NodeShape
from .edge import Edge, EdgeStyle
from .text import Text
from .fields import SpatialFields
from .contours import RegionSpec, ContourSettings
from .colonies import ColonySettings
from .quality import AngleSettings
from .colors import hex2rgb
from .color_fields import ColorField


@dataclass(frozen=True)
class GraphStyle:
    node_shape: NodeShape = "circle"
    edge_style: EdgeStyle = "solid"
    node_inner_radius: float = 2
    node_outer_radius: float = 4
    node_buffer: float = 1
    edge_thickness: float = 1
    edge_node_distance: float = 1.4
    edge_length_min: float = 10
    edge_length_max: float = 20
    node_color: str = '#545454'
    edge_color: str = '#a6b7c8'
    background: str | None = '#101318'
    text_color: str = '#e04e3b'
    colony_colors: tuple[str, ...] = ('#ef916c', '#71b9e8', '#a5c77e')

    def __post_init__(self) -> None:
        if not all(isfinite(v) and v > 0 for v in (self.edge_length_min, self.edge_length_max)) or self.edge_length_min > self.edge_length_max:
            raise ValueError('Style requires finite 0 < minimum edge length <= maximum')
        first = Node(shape=self.node_shape, outer_radius=self.node_outer_radius, inner_radius=self.node_inner_radius, buffer=self.node_buffer, color=self.node_color)
        second = Node(2*self.node_outer_radius+2*self.edge_node_distance+self.edge_length_min, 0, outer_radius=self.node_outer_radius, inner_radius=self.node_inner_radius)
        Edge(first, second, style=self.edge_style, thickness=self.edge_thickness, color=self.edge_color, edge_node_distance=self.edge_node_distance)
        if self.background is not None: hex2rgb(self.background)
        hex2rgb(self.text_color)
        if len(self.colony_colors) < 2: raise ValueError('Styles need at least two colony colors')
        for color in self.colony_colors: hex2rgb(color)

    @classmethod
    def historical(cls) -> GraphStyle:
        return cls()

    @classmethod
    def light(cls) -> GraphStyle:
        return cls.named('light')

    @classmethod
    def named(cls, name: str) -> GraphStyle:
        try: palette = PALETTES[name]
        except KeyError as error: raise ValueError(f'Unknown palette {name!r}; choose from {", ".join(PALETTES)}') from error
        return cls(node_color=palette.nodes, edge_color=palette.edges, background=palette.background, text_color=palette.text, colony_colors=palette.colonies)

    @staticmethod
    def palette_names() -> tuple[str, ...]:
        return tuple(PALETTES)

    def create_graph(self, *, target_nodes: int = 180, target_seed_nodes: int = 3, target_extra_edges: int = 0, seed: int | None = 0,
                     outline_polygon: Polygon | MultiPolygon | None = None, region: RegionSpec | None = None,
                     illegal_areas: Sequence[Polygon | MultiPolygon] | Polygon | MultiPolygon | None = None, texts: Sequence[Text] = (),
                     fields: SpatialFields | None = None, colonies: ColonySettings | None = None, angles: AngleSettings | None = None, contours: ContourSettings | None = None, draw_border: bool = False, color_field: ColorField | None = None, border_color: str = "#a6a6a6", border_width: float = 0.5) -> Graph:
        if outline_polygon is not None and region is not None: raise ValueError('Specify outline_polygon or region, not both')
        outline = region.resolve() if region is not None else outline_polygon if outline_polygon is not None else box(0, 0, 600, 360)
        return Graph(node_shape=self.node_shape, edge_style=self.edge_style, target_nodes=target_nodes, target_seed_nodes=target_seed_nodes, target_extra_edges=target_extra_edges, seed=seed, outline_polygon=outline,
                     illegal_areas=illegal_areas, texts=texts, fields=fields, colonies=colonies, angles=angles, contours=contours, draw_border=draw_border, color_field=color_field, border_color=border_color, border_width=border_width,
                     node_inner_radius=self.node_inner_radius, node_outer_radius=self.node_outer_radius, node_buffer=self.node_buffer, node_color=self.node_color,
                     edge_thickness=self.edge_thickness, edge_node_distance=self.edge_node_distance, edge_length_min=self.edge_length_min,
                     edge_length_max=self.edge_length_max, edge_color=self.edge_color)


@dataclass(frozen=True)
class Palette:
    nodes: str
    edges: str
    background: str
    text: str
    colonies: tuple[str, ...]


PALETTES: dict[str, Palette] = {
    'porcelain': Palette('#284d68', '#7f9baa', '#ffffff', '#a64152', ('#284d68', '#a64152', '#458276')),
    'linen': Palette('#806348', '#a59779', '#fffdf5', '#596d49', ('#806348', '#596d49', '#9a617a')),
    'historical': Palette('#545454', '#a6b7c8', '#101318', '#e04e3b', ('#ef916c', '#71b9e8', '#a5c77e')),
    'light': Palette('#355569', '#607d8b', '#faf7f0', '#b44235', ('#b44235', '#27718a', '#597943')),
    'arctic': Palette('#a5dce5', '#527e9e', '#0b1d2c', '#eefaff', ('#a5dce5', '#8c9fe8', '#e4f2ef')),
    'aurora': Palette('#63d5a4', '#876fc4', '#101726', '#ddf4ae', ('#63d5a4', '#c698e8', '#e0d487')),
    'ember': Palette('#f3a55d', '#b4514d', '#251719', '#ffe2b0', ('#f3a55d', '#da7066', '#ded0b1')),
    'forest': Palette('#a9c68c', '#638c78', '#142720', '#f2e3af', ('#a9c68c', '#dfb66c', '#8cbcc5')),
    'orchid': Palette('#dea5d9', '#8d87c3', '#221c35', '#ffe6f1', ('#dea5d9', '#98bee1', '#e9c392')),
    'blueprint': Palette('#edf5fb', '#8fb9df', '#193e72', '#f6db8a', ('#edf5fb', '#e5c76f', '#92cfc4')),
}
