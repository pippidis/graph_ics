"""Bounded random graph growth with explicit geometry and deterministic rebuilds."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from copy import deepcopy
from math import atan2, cos, isfinite, pi, sin
from random import Random
import warnings
from typing import Literal

import networkx as nx
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.geometry.base import BaseGeometry

from .text import Text, MeasuredText
from .color_fields import ColorField
from .colors import hex2rgb
from .drawing import DrawingContext
from .contours import ContourGuide, ContourReport, ContourSettings, RegionSpec
from .fields import SpatialFields, CallableField
from .colonies import ColonySettings, rival_clearance, visible_distance, component_ids
from .quality import AngleSettings, incident_angle
from .growth import GrowthGenerator, GrowthPolicy, GrowthSettings
from .edge import Edge, EdgeStyle
from .node import Node, NodeShape, shape_inradius_ratio
from .spatial import Bounds, SpatialIndex, SpatialHash, BruteForceIndex, CollisionStats

GRAPH_DEFAULT_OUTLINE_POLYGON = box(0, 0, 100, 100)
Field = Callable[[Point], float]
NodeFunction = Callable[[Node], float]


class Graph:
    """Grow a spatial forest using bounded random placement attempts.

    target_nodes counts every node, including supplied nodes and seeds.
    target_seed_nodes is the desired initial node count including supplied nodes.
    Edge lengths are visible segment lengths; callbacks return radians and visible
    length respectively. Boundaries allow touching, obstacles/other objects do not.
    Node buffers affect node-node and unrelated node-edge clearance, not boundaries.
    Growth uses an incremental frontier with indexed exact collision checks.
    """

    def __init__(self, target_nodes: int = 3, target_extra_edges: int = 0, target_seed_nodes: int = 1,
                 outline_polygon: Polygon | MultiPolygon = GRAPH_DEFAULT_OUTLINE_POLYGON, illegal_areas: Sequence[Polygon | MultiPolygon] | Polygon | MultiPolygon | None = None,
                 node_radius_scale_map: Field | None = None, edge_length_scale_map: Field | None = None, edge_thickness_scale_map: Field | None = None,
                 extra_edge_elongation_factor: float = 1.5, input_nodes: Sequence[Node] | None = None, draw_border: bool = False,
                 edge_length_min: float = 1.0, edge_length_max: float = 2.0, edge_thickness: float = 1.0,
                 node_inner_radius: float = 1.0, node_outer_radius: float = 2.0, node_buffer: float = 0.1,
                 node_direction_function: NodeFunction | None = None, node_length_function: NodeFunction | None = None,
                 *, seed: int | None = None, edge_node_distance: float = 1.0, node_color: str = '#545454', edge_color: str = '#a6b7c8',
                 node_opacity: float = 1.0, edge_opacity: float = 1.0, spatial_backend: Literal['hash', 'brute'] = 'hash', cell_size: float | None = None, fields: SpatialFields | None = None, region: RegionSpec | None = None, contours: ContourSettings | None = None, angles: AngleSettings | None = None, colonies: ColonySettings | None = None, texts: Sequence[Text] = (), node_shape: NodeShape = "circle", edge_style: EdgeStyle = "solid", color_field: ColorField | None = None, border_color: str = "#a6a6a6", border_width: float = 0.5) -> None:
        for name, value in [('target_nodes', target_nodes), ('target_seed_nodes', target_seed_nodes), ('target_extra_edges', target_extra_edges)]:
            if type(value) is not int or value < 0: raise ValueError(f'{name} must be a nonnegative integer')
        if seed is not None and type(seed) is not int: raise ValueError('seed must be an integer or None')

        if fields is not None and any(field is not None for field in (node_radius_scale_map, edge_length_scale_map, edge_thickness_scale_map)):
            raise ValueError('Use fields or legacy scale maps, not both')
        self.fields = fields or SpatialFields(
            radius=CallableField(lambda x, y: node_radius_scale_map(Point(x, y))) if node_radius_scale_map is not None else None,
            length=CallableField(lambda x, y: edge_length_scale_map(Point(x, y))) if edge_length_scale_map is not None else None,
            thickness=CallableField(lambda x, y: edge_thickness_scale_map(Point(x, y))) if edge_thickness_scale_map is not None else None)
        self.density_conflicts = 0
        if not isfinite(extra_edge_elongation_factor) or extra_edge_elongation_factor <= 0: raise ValueError('Extra-edge scale must be positive')
        if region is not None:
            if outline_polygon is not GRAPH_DEFAULT_OUTLINE_POLYGON: raise ValueError('Specify region or outline_polygon, not both')
            outline_polygon = region.resolve()
        self.colonies = colonies
        self.angles = angles or AngleSettings()
        self.contours = contours
        self.contour_guide: ContourGuide | None = None
        self.readable_failures = 0
        self.width_failures = 0
        self._minimum_radius = 0.0
        self._validate_polygon(outline_polygon)
        if not all(isfinite(v) for v in (edge_length_min, edge_length_max)) or not 0 < edge_length_min <= edge_length_max:
            raise ValueError('Require finite 0 < edge_length_min <= edge_length_max')
        # Validate styles with the same contracts used by the generated geometry.
        prototype = Node(shape=node_shape, color=node_color, opacity=node_opacity, outer_radius=node_outer_radius, inner_radius=node_inner_radius, buffer=node_buffer, min_edge_length=0)
        other = Node(2*node_outer_radius+2*edge_node_distance+edge_length_min, 0, outer_radius=node_outer_radius, inner_radius=node_inner_radius)
        Edge(prototype, other, style=edge_style, thickness=edge_thickness, color=edge_color, opacity=edge_opacity, edge_node_distance=edge_node_distance)
        if spatial_backend not in ('hash', 'brute'): raise ValueError('Spatial backend must be hash or brute')
        self.spatial_backend = spatial_backend
        self.cell_size = cell_size if cell_size is not None else max(2*(node_outer_radius+node_buffer), edge_length_max)
        SpatialHash(self.cell_size)  # Validate even when using the reference backend.
        self._index: SpatialIndex
        self._objects: list[Node | Edge] = []
        self.collision_stats = CollisionStats()
        self.target_nodes, self.target_seed_nodes = target_nodes, target_seed_nodes
        self.target_extra_edges = target_extra_edges
        self.extra_edge_elongation_factor = extra_edge_elongation_factor
        self.outline_polygon = outline_polygon
        self.node_inner_radius, self.node_outer_radius, self.node_buffer = node_inner_radius, node_outer_radius, node_buffer
        self.edge_length_min, self.edge_length_max = edge_length_min, edge_length_max
        self.edge_thickness, self.edge_node_distance = edge_thickness, edge_node_distance
        self.node_shape, self.edge_style = node_shape, edge_style
        self.node_color, self.edge_color = node_color, edge_color
        self.node_opacity, self.edge_opacity = node_opacity, edge_opacity
        self.node_direction_function, self.node_length_function = node_direction_function, node_length_function
        hex2rgb(border_color)
        if not isfinite(border_width) or border_width <= 0: raise ValueError('Border width must be positive and finite')
        self.border_color, self.border_width = border_color, border_width
        self.color_field = color_field
        self.draw_border = draw_border
        self.seed = seed
        self._rng = Random(seed)
        self._initial_rng_state = self._rng.getstate()
        self._illegal_areas: list[Polygon | MultiPolygon] = []
        self._build_illegal_areas(illegal_areas)
        self.texts: tuple[MeasuredText, ...] = tuple(text.measure() for text in texts)
        self._illegal_areas.extend(text.exclusion for text in self.texts)
        self._input_nodes = deepcopy(list(input_nodes or []))
        self._nodes: list[Node] = []
        self._edges: list[Edge] = []
        self.nx_graph: nx.DiGraph[str] = nx.DiGraph()
        self.built = False
        self._generator: GrowthGenerator | None = None
        if contours is not None:
            ratio = self.fields.ring_ratio if self.fields.ring_ratio is not None else node_inner_radius/node_outer_radius
            self._minimum_radius = max(contours.minimum_radius, contours.readability.radius_minimum(ratio)/shape_inradius_ratio(node_shape))
            self.contour_guide = ContourGuide(outline_polygon, contours, self._minimum_radius, node_outer_radius)
        if colonies is not None:
            if input_nodes: raise ValueError('Use colony seed positions instead of input_nodes when colonies are configured')
            self._input_nodes = []
            for colony in colonies.colonies:
                for x, y in colony.seeds:
                    node = self._new_node(x, y, is_seed=True)
                    node.colony_id, node.color = colony.id, colony.color
                    self._input_nodes.append(node)
            self.target_seed_nodes = len(self._input_nodes)
        if len(self._input_nodes) > target_nodes: raise ValueError('Supplied nodes exceed target_nodes')
        self._reset()

    @staticmethod
    def _validate_polygon(polygon: Polygon | MultiPolygon) -> None:
        if not isinstance(polygon, (Polygon, MultiPolygon)) or polygon.is_empty or not polygon.is_valid or polygon.area <= 0:
            raise ValueError('Region must be a valid nonempty Polygon or MultiPolygon')
        if not all(isfinite(v) for v in polygon.bounds): raise ValueError('Region bounds must be finite')

    @classmethod
    def historical(cls, *, target_nodes: int = 180, target_seed_nodes: int = 3, seed: int | None = 0,
                   outline_polygon: Polygon | MultiPolygon | None = None, illegal_areas: Sequence[Polygon | MultiPolygon] | Polygon | MultiPolygon | None = None) -> Graph:
        """Historical proportions at one-fifth scale on a default 600x360 region.

        Ring radii 2/4, edge width 1, endpoint gap 1.4, visible lengths 10–20.
        Colors use exact normalized hexadecimal channels rather than legacy /256.
        """
        region = box(0, 0, 600, 360) if outline_polygon is None else outline_polygon
        return cls(target_nodes=target_nodes, target_seed_nodes=target_seed_nodes, seed=seed, outline_polygon=region, illegal_areas=illegal_areas,
                   node_inner_radius=2, node_outer_radius=4, node_buffer=1, edge_thickness=1, edge_node_distance=1.4, edge_length_min=10, edge_length_max=20)

    @property
    def nodes(self) -> tuple[Node, ...]:
        """Accepted nodes in deterministic order; geometry is stationary after creation."""
        return tuple(self._nodes)

    @property
    def edges(self) -> tuple[Edge, ...]:
        return tuple(self._edges)

    def __str__(self) -> str:
        return f'GRAPH [Built={self.built}, Nodes={len(self._nodes)}, Edges={len(self._edges)}]'

    def __repr__(self) -> str:
        return '{built: ' + str(self.built) + ', nodes: ' + str(len(self._nodes)) + ', edges: ' + str(len(self._edges)) + '}'

    def _reset(self) -> None:
        self._generator = None
        self._event_listener: Callable[[str, Node | Edge | tuple[str, ...]], None] | None = None
        self.clearance_rejections = 0
        self._next_node_id = 0
        self._node_by_id: dict[str, Node] = {}
        self._index = SpatialHash(self.cell_size) if self.spatial_backend == 'hash' else BruteForceIndex()
        self._objects.clear()
        self.collision_stats = CollisionStats()
        self.density_conflicts = 0
        self.readable_failures = self.width_failures = self.neighbor_ratio_failures = 0
        self._boundary_count = 0
        self._anchor_cursor = 0
        self._terminal_reasons: dict[str, str] = {}
        self._rng.setstate(self._initial_rng_state)
        self._nodes.clear()
        self._edges.clear()
        self.nx_graph.clear()
        self.parents: dict[str, str | None] = {}
        self.built = False
        for node in deepcopy(self._input_nodes):
            if not self.can_place_node(node): raise ValueError('Supplied node violates bounds, obstacles, or node clearance')
            self._accept(node)

    def _accept(self, node: Node, edge: Edge | None = None) -> None:
        node.id = f'node_{self._next_node_id:06d}'
        self._next_node_id += 1
        self._node_by_id[node.id] = node
        self._index.insert(len(self._objects), self._envelope(node))
        self._objects.append(node)
        if edge is not None:
            self._index.insert(len(self._objects), self._envelope(edge))
            self._objects.append(edge)
        self._nodes.append(node)
        if self.contours is not None and self.boundary_terminal(node): self._boundary_count += 1
        self.nx_graph.add_node(node.id, outer_radius=node.outer_radius, colony_id=node.colony_id)
        self.parents[node.id] = edge.start_node.id if edge is not None else None
        if self._generator is not None and self._generator.coverage is not None: self._generator.coverage.accept(node)
        if edge is not None:
            self._edges.append(edge)
            self.nx_graph.add_edge(edge.start_node.id, node.id, length=edge.length, thickness=edge.thickness)

        if self._event_listener is not None: self._event_listener('branch' if edge is not None else 'seed', edge if edge is not None else node)

    def _accept_loop(self, edge: Edge, *, bridge: bool = False) -> None:
        if edge.start_node is edge.end_node or self.nx_graph.has_edge(edge.start_node.id, edge.end_node.id) or self.nx_graph.has_edge(edge.end_node.id, edge.start_node.id):
            raise ValueError('Loops cannot be self-edges or duplicate undirected pairs')
        self._index.insert(len(self._objects), self._envelope(edge))
        self._objects.append(edge)
        self._edges.append(edge)
        self.nx_graph.add_edge(edge.start_node.id, edge.end_node.id, length=edge.length, thickness=edge.thickness, loop=not bridge, bridge=bridge)
        if self._event_listener is not None: self._event_listener('join' if bridge else 'loop', edge)

    def component_ids(self) -> dict[str, str]:
        """Current connectivity labels; ownership and parent lineage stay separate."""
        return component_ids(self)

    def to_networkx(self, *, directed: bool = False) -> nx.Graph[str]:
        """Return an independent undirected graph by default; parents retain lineage."""
        return self.nx_graph.copy() if directed else self.nx_graph.to_undirected()

    def growth(self, *, settings: GrowthSettings | None = None, policy: GrowthPolicy | None = None) -> GrowthGenerator:
        """Return this run's generator; configure only before the first step/build."""
        if self._generator is None: return GrowthGenerator(self, settings=settings, policy=policy)
        if settings is not None or policy is not None: raise ValueError('Configure growth only when creating a generator')
        return self._generator

    def build(self, force: bool = False) -> bool:
        """Run the incremental engine to completion; inspect growth().status for why.

        force resets geometry and randomness, retaining this run's settings/policy.
        A completed run can be underfilled or cancelled; True means it has stopped.
        """
        if force:
            previous = self._generator
            self._reset()
            self.growth(settings=previous.settings if previous else None, policy=previous.policy if previous and previous.settings.coverage is None and self.colonies is None else None)
        generator = self.growth()
        while not generator.done: generator.step()
        return True

    def _build_illegal_areas(self, illegal_areas: Sequence[Polygon | MultiPolygon] | Polygon | MultiPolygon | None = None) -> None:
        if illegal_areas is None: return
        areas = [illegal_areas] if isinstance(illegal_areas, (Polygon, MultiPolygon)) else list(illegal_areas)
        for area in areas: self._validate_polygon(area)
        self._illegal_areas = areas

    def _new_node(self, x: float, y: float, is_seed: bool = False) -> Node:
        scale = self.fields.scale(self.fields.radius, x, y)
        coordinated = self.fields.scale(None, x, y)
        radius = self.node_outer_radius*scale
        ratio = self.node_inner_radius/self.node_outer_radius if self.fields.ring_ratio is None else self.fields.ring_ratio
        if self.contours is not None and self.contour_guide is not None and self.contours.adaptive:
            cap = min(max(0, self.contour_guide.distance.sample(x, y)), self.contour_guide.width.sample(x, y)/self.contours.width_divisor)
            radius = max(self._minimum_radius, min(radius, cap*(1-1e-9)))
        spacing = self.fields.spacing(x, y)
        buffer = self.node_buffer*coordinated
        if self.contours is not None: buffer = max(buffer, self.contours.readability.separation/(2*self.contours.readability.output_scale))
        if spacing and spacing < 2*(radius+buffer): self.density_conflicts += 1
        return Node(x, y, shape=self.node_shape, is_seed_node=is_seed, color=self.color_field.sample(x, y) if self.color_field else self.node_color, opacity=self.node_opacity, outer_radius=radius,
                    inner_radius=radius*ratio, buffer=buffer, min_edge_length=0, preferred_spacing=spacing)

    def _contour_scale(self, node: Node) -> float:
        if self.contours is None or not self.contours.adaptive: return 1
        original = self.node_outer_radius*self.fields.scale(self.fields.radius, node.center.x, node.center.y)
        return min(1, node.outer_radius/original)

    def _edge_gap(self, parent: Node, node: Node) -> float:
        value = self.edge_node_distance*self.fields.scale(None, (parent.center.x+node.center.x)/2, (parent.center.y+node.center.y)/2)
        value *= min(self._contour_scale(parent), self._contour_scale(node))
        if self.contours is not None: value = max(value, self.contours.readability.edge_gap/self.contours.readability.output_scale)
        return value

    def _new_edge(self, parent: Node, node: Node) -> Edge | None:
        thickness = self.edge_thickness*self.fields.scale(self.fields.thickness, (parent.center.x+node.center.x)/2, (parent.center.y+node.center.y)/2)
        thickness *= min(self._contour_scale(parent), self._contour_scale(node))
        if self.contours is not None: thickness = max(thickness, (3 if self.edge_style == "double" else 1)*self.contours.readability.stroke/self.contours.readability.output_scale)
        if parent.distance_to(node) <= parent.outer_radius+node.outer_radius+2*self._edge_gap(parent, node): return None
        return Edge(parent, node, style=self.edge_style, thickness=thickness, color=parent.color if self.colonies is not None else self.color_field.sample((parent.center.x+node.center.x)/2, (parent.center.y+node.center.y)/2) if self.color_field else self.edge_color, opacity=self.edge_opacity, edge_node_distance=self._edge_gap(parent, node))

    def boundary_distance(self, node: Node) -> float:
        return max(0, float(self.outline_polygon.boundary.distance(node.center))-node.outer_radius)

    def boundary_terminal(self, node: Node) -> bool:
        return self.contours is not None and self.boundary_distance(node) <= self.contours.tolerance/self.contours.readability.output_scale

    def contour_report(self) -> ContourReport:
        if self.contours is None or self.contour_guide is None: raise ValueError('Contour diagnostics require ContourSettings')
        nodes = self.nodes
        terminals = [n for n in nodes if self.nx_graph.degree(n.id) <= 1]
        unanchored = tuple(n.id for n in terminals if not self.boundary_terminal(n))
        tolerance = self.contours.anchor_spacing
        covered = sum(weight for point, weight in self.contour_guide.boundary_samples if any(point.distance(n.center) <= n.outer_radius+tolerance for n in nodes))
        perimeter = sum(weight for _, weight in self.contour_guide.boundary_samples)
        coverage = covered/perimeter if perimeter else 0.0
        return ContourReport(coverage, sum(self.boundary_terminal(n) for n in nodes), self.contour_guide.unreadable_boundary_samples, len(terminals), unanchored,
                             tuple(self.boundary_distance(n) for n in terminals), tuple((key, self._terminal_reasons.get(key, 'run_stopped_before_anchor')) for key in unanchored), self.readable_failures, self.width_failures, self.neighbor_ratio_failures,
                             bool(nodes) and not unanchored, self.contour_guide.width.resolution,
                             min((n.outer_radius for n in nodes), default=0), max((n.outer_radius for n in nodes), default=0))

    def _build_seed_nodes(self, target_seed_nodes: int | None = None) -> None:
        wanted = self.target_seed_nodes if target_seed_nodes is None else target_seed_nodes
        for _ in range(max(0, min(wanted, self.target_nodes)-len(self._nodes))):
            node = self.find_seed_node()
            if node is None: break
            self._accept(node)

    def _build_regular_nodes(self, nodes_to_build: int | None = None) -> None:
        remaining = max(0, self.target_nodes-len(self._nodes))
        if nodes_to_build is not None: remaining = min(remaining, max(0, nodes_to_build))
        for _ in range(remaining):
            if not self._nodes: break
            node, edge = self.find_next_node()
            if node is None: break
            self._accept(node, edge)

    def in_bounds(self, obj: BaseGeometry | Node | Edge) -> bool:
        """Require full containment; boundary touching is allowed.

        Disk containment uses analytic center-to-boundary distance rather than an
        inscribed polygon approximation. Edge footprints use exact butt rectangles.
        """
        if isinstance(obj, Node):
            return bool(self.outline_polygon.covers(obj.center) and obj.center.distance(self.outline_polygon.boundary) >= obj.outer_radius)
        geometry = obj.footprint if isinstance(obj, Edge) else obj
        return bool(not geometry.is_empty and self.outline_polygon.covers(geometry))

    def in_illegal_areas(self, obj: BaseGeometry | Node | Edge) -> bool:
        if isinstance(obj, Node): return any(area.distance(obj.center) <= obj.outer_radius for area in self._illegal_areas)
        geometry = obj.footprint if isinstance(obj, Edge) else obj
        return any(geometry.intersects(area) for area in self._illegal_areas)

    @staticmethod
    def _in_polygon(obj: BaseGeometry, polygon: Polygon | MultiPolygon | None) -> bool:
        """Compatibility helper; now means full containment, including the boundary."""
        return polygon is not None and not obj.is_empty and bool(polygon.covers(obj))

    @staticmethod
    def _envelope(obj: Node | Edge) -> Bounds:
        if isinstance(obj, Edge): return obj.footprint.bounds
        # Sum of both node envelopes is conservative for the max pair-spacing rule.
        radius = max(obj.buffer_radius + obj.min_edge_length, obj.preferred_spacing)
        x, y = obj.center.x, obj.center.y
        return x-radius, y-radius, x+radius, y+radius

    def _in_hole(self, obj: Node | Edge) -> bool:
        polygons = [self.outline_polygon] if isinstance(self.outline_polygon, Polygon) else self.outline_polygon.geoms
        for polygon in polygons:
            for ring in polygon.interiors:
                hole = Polygon(ring)
                if isinstance(obj, Node):
                    if hole.distance(obj.center) < obj.outer_radius: return True
                elif obj.footprint.intersection(hole).area > 0: return True
        return False

    def _can_place(self, obj: Node | Edge) -> bool:
        if self.contours is not None:
            readable = self.contours.readability
            if isinstance(obj, Node):
                if obj.outer_radius < self._minimum_radius-1e-8 or (obj.outer_radius-obj.inner_radius)*shape_inradius_ratio(obj.shape)*readable.output_scale < readable.stroke-1e-8 or 2*obj.inner_radius*shape_inradius_ratio(obj.shape)*readable.output_scale < readable.hole_diameter-1e-8 or (2*obj.buffer+obj.min_edge_length)*readable.output_scale < readable.separation-1e-8:
                    self.readable_failures += 1
                    return False
                if self.contour_guide is not None and self.contour_guide.distance.sample(obj.center.x, obj.center.y) >= 0 and self.contour_guide.width.sample(obj.center.x, obj.center.y) < 2*self._minimum_radius:
                    self.width_failures += 1
            elif obj.thickness/(3 if obj.style == "double" else 1)*readable.output_scale < readable.stroke-1e-8 or obj.edge_node_distance*readable.output_scale < readable.edge_gap-1e-8:
                self.readable_failures += 1
                return False
            elif max(obj.start_node.outer_radius, obj.end_node.outer_radius)/min(obj.start_node.outer_radius, obj.end_node.outer_radius) > self.contours.maximum_neighbor_ratio*(1+1e-8):
                self.neighbor_ratio_failures += 1
                return False
        stats = self.collision_stats
        if not self.in_bounds(obj):
            if self._in_hole(obj): stats.inner_exclusion += 1
            else: stats.outer_boundary += 1
            return False
        if self.in_illegal_areas(obj):
            stats.inner_exclusion += 1
            return False
        bounds = self._envelope(obj)
        gap = max((rule.clearance for rule in self.colonies.interactions), default=0) if self.colonies else 0
        keys = self._index.query((bounds[0]-gap, bounds[1]-gap, bounds[2]+gap, bounds[3]+gap))
        stats.queries += 1
        stats.queried_objects += len(keys)
        for key in keys:
            other = self._objects[key]
            stats.exact_checks += 1
            if self.colonies is not None:
                required = rival_clearance(self.colonies, obj, other)
                if required and visible_distance(obj, other)+1e-9 < required:
                    self.clearance_rejections += 1
                    return False
            if isinstance(obj, Edge): overlap = obj.overlap(other)
            elif isinstance(other, Edge): overlap = other.overlap(obj)
            else: overlap = obj.overlap(other)
            if overlap:
                if isinstance(other, Node): stats.node_clearance += 1
                else: stats.edge_clearance += 1
                return False
        return True

    def can_place_node(self, node: Node) -> bool:
        return self._can_place(node)

    def candidate_angle(self, edge: Edge) -> float:
        angles: list[float] = []
        for center, other in ((edge.start_node, edge.end_node), (edge.end_node, edge.start_node)):
            if center.id not in self.nx_graph: continue
            neighbors = set(self.nx_graph.predecessors(center.id)) | set(self.nx_graph.successors(center.id))
            angles.extend(incident_angle(center, other, self._node_by_id[key]) for key in neighbors if key != other.id)
        return min(angles, default=180)

    def can_place_edge(self, edge: Edge) -> bool:
        if self.colonies is not None and edge.start_node.colony_id != edge.end_node.colony_id:
            rule = self.colonies.rule(edge.start_node.colony_id, edge.end_node.colony_id)
            if rule is None or not rule.allow_join: return False
        return self.candidate_angle(edge)+1e-9 >= self.angles.minimum and self._can_place(edge)

    def _remove_isolated_nodes(self) -> tuple[str, ...]:
        removed = tuple(node.id for node in self._nodes if self.nx_graph.degree(node.id) == 0)
        keys = set(removed)
        self._nodes = [node for node in self._nodes if node.id not in keys]
        self._objects = [obj for obj in self._objects if not isinstance(obj, Node) or obj.id not in keys]
        self.nx_graph.remove_nodes_from(removed)
        for key in removed:
            self.parents.pop(key, None)
            self._node_by_id.pop(key, None)
            self._terminal_reasons.pop(key, None)
        self._boundary_count = sum(self.boundary_terminal(node) for node in self._nodes)
        self._index = SpatialHash(self.cell_size) if self.spatial_backend == 'hash' else BruteForceIndex()
        for index, obj in enumerate(self._objects): self._index.insert(index, self._envelope(obj))
        if removed and self._event_listener is not None: self._event_listener('remove', removed)
        return removed

    def find_seed_node(self, attempts: int = 100, *, boundary_only: bool = False) -> Node | None:
        min_x, min_y, max_x, max_y = self.outline_polygon.bounds
        for _ in range(attempts):
            if self.contours is not None and self.contour_guide is not None and self.contours.mode == 'follow' and self.contour_guide.anchors and (boundary_only or self._rng.random() < self.contours.boundary_fraction):
                if boundary_only:
                    anchor = self.contour_guide.anchors[self._anchor_cursor % len(self.contour_guide.anchors)]
                    self._anchor_cursor += 1
                else: anchor = self._rng.choice(self.contour_guide.anchors)
                node = self._new_node(anchor.center.x, anchor.center.y, is_seed=True)
            else:
                node = self._new_node(self._rng.uniform(min_x, max_x), self._rng.uniform(min_y, max_y), is_seed=True)
            if self.can_place_node(node): return node
        return None

    def _neighbor_node(self, parent: Node, x: float, y: float) -> Node:
        node = self._new_node(x, y)
        node.colony_id = parent.colony_id
        if self.colonies is not None: node.color = parent.color
        if self.contours is not None:
            maximum = parent.outer_radius*self.contours.maximum_neighbor_ratio
            if node.outer_radius > maximum:
                ratio = node.inner_radius/node.outer_radius
                node.outer_radius, node.inner_radius = maximum, maximum*ratio
        return node

    def boundary_seed_needed(self) -> bool:
        if self.colonies is not None: return False
        if self._generator is not None and self._generator.coverage is not None and not self._generator.coverage.settings.allow_components: return False
        return (self.contours is not None and self.contour_guide is not None and self.contours.mode == 'follow' and bool(self.contour_guide.anchors)
                and self._boundary_count < self.target_nodes*self.contours.boundary_fraction and self._anchor_cursor < len(self.contour_guide.anchors)*2)

    def find_node_candidate(self, parent: Node | None = None) -> tuple[Node, Node]:
        """Propose a neighbor; requires an existing node and performs no placement."""
        if not self._nodes: raise ValueError('Create a seed before requesting a neighbor candidate')
        parent = self._rng.choice(self._nodes) if parent is None else parent
        angle = self.node_direction_function(parent) if self.node_direction_function is not None else self._rng.uniform(0, 2*pi)
        visible_length = self.node_length_function(parent) if self.node_length_function is not None else self._rng.uniform(self.edge_length_min, self.edge_length_max)
        if not isfinite(angle) or not isfinite(visible_length) or visible_length <= 0: raise ValueError('Callbacks must return finite radians and a positive visible length')
        if self.contours is not None and self.contour_guide is not None and self.contours.mode != 'contain' and self._rng.random() < self.contours.guidance and (self.contours.mode == 'terminate' or self._boundary_count < self.target_nodes*self.contours.boundary_fraction):
            guide = self.contour_guide
            if self.contours.mode == 'follow':
                anchor = guide.nearest(parent.center)
                if anchor is not None:
                    same = [a for a in guide.anchors if a.component == anchor.component]
                    index = same.index(anchor)
                    target = same[(index+self._rng.randint(1, min(3, len(same))))%len(same)].center
                    if parent.center.distance(anchor.center) <= self.contours.anchor_spacing:
                        return parent, self._neighbor_node(parent, target.x, target.y)
                    tangent = anchor.tangent
                    toward = atan2(anchor.center.y-parent.center.y, anchor.center.x-parent.center.x)
                    angle = atan2(sin(tangent)+sin(toward), cos(tangent)+cos(toward))
            else:
                terminal_target = guide.terminal_center(parent.center, max(self._minimum_radius, parent.outer_radius/self.contours.maximum_neighbor_ratio))
                if terminal_target is not None and guide.anchors and (self.nx_graph.out_degree(parent.id) > 0 or any(n.center.distance(terminal_target) < n.buffer_radius+self._minimum_radius for n in self._nodes if n is not parent)):
                    nearby = sorted(guide.anchors, key=lambda a: a.center.distance(parent.center))[:8]
                    terminal_target = self._rng.choice(nearby).center
                if terminal_target is not None:
                    candidate = self._neighbor_node(parent, terminal_target.x, terminal_target.y)
                    separation = parent.center.distance(terminal_target)
                    if separation <= parent.outer_radius+candidate.outer_radius+2*self._edge_gap(parent, candidate)+visible_length:
                        return parent, candidate
                    angle = atan2(terminal_target.y-parent.center.y, terminal_target.x-parent.center.x)
        if self.colonies is not None: angle = self.colonies.bias(self, parent, angle)
        distance = parent.outer_radius + self.node_outer_radius + 2*self.edge_node_distance + visible_length
        for _ in range(self.fields.refinement_steps):
            node = self._neighbor_node(parent, parent.center.x+cos(angle)*distance, parent.center.y+sin(angle)*distance)
            length_scale = (self.fields.scale(self.fields.length, parent.center.x, parent.center.y)+self.fields.scale(self.fields.length, node.center.x, node.center.y))/2
            desired = max(parent.outer_radius+node.outer_radius+2*self._edge_gap(parent, node)+visible_length*length_scale*min(self._contour_scale(parent), self._contour_scale(node)),
                          max(parent.preferred_spacing, node.preferred_spacing)*(1+1e-9))
            if abs(distance-desired) <= 1e-8: break
            distance = desired
        return parent, self._neighbor_node(parent, parent.center.x+cos(angle)*distance, parent.center.y+sin(angle)*distance)

    def find_next_node(self, attempts: int = 100) -> tuple[Node | None, Edge | None]:
        if not self._nodes: return self.find_seed_node(attempts), None
        for _ in range(attempts):
            parent, candidate = self.find_node_candidate()
            if not self.can_place_node(candidate): continue
            edge = self._new_edge(parent, candidate)
            if edge is not None and self.can_place_edge(edge): return candidate, edge
        return None, None

    def draw(self, context: DrawingContext, x_shift: float = 0, y_shift: float = 0, draw_nodes: bool = True, draw_edges: bool = True,
             draw_outline: bool = True, draw_text: bool = True) -> DrawingContext:
        """Compatibility wrapper for the shared renderer."""
        from .rendering import draw_graph
        return draw_graph(self, context, x_shift, y_shift, draw_nodes=draw_nodes, draw_edges=draw_edges, draw_outline=draw_outline, draw_text=draw_text)

    def get_bounds(self) -> tuple[float, float, float, float]:
        return self.outline_polygon.bounds

    def get_extent(self, buffer: float = 0) -> tuple[float, float, float, float]:
        """Visible bounds in min_x, min_y, max_x, max_y order; empty graphs return zeros."""
        if not isfinite(buffer) or buffer < 0: raise ValueError('Extent margin must be finite and nonnegative')
        bounds = [n.bounds for n in self._nodes] + [e.footprint.bounds for e in self._edges] + [text.bounds for text in self.texts]
        if self.draw_border: bounds.append(self.outline_polygon.buffer(self.border_width/2).bounds)
        if not bounds: return -buffer, -buffer, buffer, buffer
        return min(b[0] for b in bounds)-buffer, min(b[1] for b in bounds)-buffer, max(b[2] for b in bounds)+buffer, max(b[3] for b in bounds)+buffer

    def get_exstent(self, buffer: float = 0) -> tuple[float, float, float, float]:
        """Deprecated spelling; retains the old min_x, max_x, min_y, max_y order."""
        warnings.warn('Use get_extent() with min_x, min_y, max_x, max_y ordering', DeprecationWarning, stacklevel=2)
        min_x, min_y, max_x, max_y = self.get_extent(buffer)
        return min_x, max_x, min_y, max_y

    def get_size(self, buffer: float = 0) -> tuple[float, float]:
        min_x, min_y, max_x, max_y = self.get_extent(buffer)
        return max_x-min_x, max_y-min_y
