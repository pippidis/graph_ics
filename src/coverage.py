"""Approximate population coverage over clipped usable tiles, not empty-space area."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor, isfinite
from random import Random
from typing import TYPE_CHECKING

from shapely.geometry import box, Polygon, MultiPolygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from .fields import positive_sample
from .node import Node

if TYPE_CHECKING:
    from .graph import Graph


@dataclass(frozen=True)
class CoverageSettings:
    tile_size: float = 25
    max_tiles: int = 4096
    parent_choices: int = 8
    allow_components: bool = True
    reseed_attempts: int = 200
    boundary_weight: float = 1
    boundary_band: float = 10
    narrow_weight: float = 1
    narrow_width: float = 20
    reseed_interval: int = 0
    seed_components: bool = False

    def __post_init__(self) -> None:
        if type(self.seed_components) is not bool: raise ValueError('seed_components must be boolean')
        if type(self.reseed_interval) is not int or self.reseed_interval < 0: raise ValueError('reseed_interval must be a nonnegative integer')
        for value in (self.tile_size, self.boundary_weight, self.boundary_band, self.narrow_weight, self.narrow_width):
            if not isfinite(value) or value <= 0: raise ValueError('Coverage dimensions and weights must be positive and finite')
        for value in (self.max_tiles, self.parent_choices):
            if type(value) is not int or value <= 0: raise ValueError('Coverage sampling limits must be positive integers')
        if type(self.reseed_attempts) is not int or self.reseed_attempts < 0: raise ValueError('Reseeding budget must be nonnegative')


@dataclass
class CoverageTile:
    column: int
    row: int
    geometry: BaseGeometry
    expected: float
    actual: int = 0

    @property
    def deficit(self) -> float:
        return max(0, self.expected-self.actual)


@dataclass(frozen=True)
class CoverageReport:
    expected_nodes: float
    actual_nodes: int
    residual_underfill: float
    occupied_tiles: int
    usable_tiles: int
    tile_size: float
    reseed_attempts: int
    reseeds: int
    occupied_tile_area_fraction: float = 0


class CoverageTracker:
    """Four area-weighted clipped quadrature samples per tile integrate density.

    Without a density field, normalize usable area weights to target_nodes.
    With a density field, retain the requested integral, even if unattainable.
    Scheduling examines a fixed-size random tournament, not all active parents.
    """
    def __init__(self, graph: Graph, settings: CoverageSettings) -> None:
        if settings.narrow_weight != 1 and graph.contour_guide is None: raise ValueError('Narrow-region weighting requires contour width estimates')
        self.settings, self.graph = settings, graph
        region = graph.outline_polygon.difference(unary_union(graph._illegal_areas))
        self.pending_components = sorted(([region] if isinstance(region, Polygon) else list(region.geoms) if isinstance(region, MultiPolygon) else []), key=lambda part: part.area, reverse=True) if settings.seed_components else []
        self.component_attempts = 0
        self.x0, self.y0, x1, y1 = graph.outline_polygon.bounds
        self.tile_size = settings.tile_size
        while ceil((x1-self.x0)/self.tile_size)*ceil((y1-self.y0)/self.tile_size) > settings.max_tiles: self.tile_size *= 1.25
        self.tiles: list[CoverageTile] = []
        self.lookup: dict[tuple[int, int], CoverageTile] = {}
        for column in range(ceil((x1-self.x0)/self.tile_size)):
            for row in range(ceil((y1-self.y0)/self.tile_size)):
                left, top = self.x0+column*self.tile_size, self.y0+row*self.tile_size
                geometry = region.intersection(box(left, top, left+self.tile_size, top+self.tile_size))
                if geometry.area <= 0: continue
                expected = 0.0
                for dx in (0, 0.5):
                    for dy in (0, 0.5):
                        part = geometry.intersection(box(left+dx*self.tile_size, top+dy*self.tile_size, left+(dx+0.5)*self.tile_size, top+(dy+0.5)*self.tile_size))
                        if part.area <= 0: continue
                        point = part.representative_point()
                        weight = settings.boundary_weight if region.boundary.distance(point) <= settings.boundary_band else 1
                        if graph.contour_guide is not None and graph.contour_guide.width.sample(point.x, point.y) < settings.narrow_width: weight *= settings.narrow_weight
                        expected += part.area*positive_sample(graph.fields.density, point.x, point.y)*weight
                if not isfinite(expected): raise ValueError('Integrated density is too large')
                tile = CoverageTile(column, row, geometry, expected)
                self.tiles.append(tile)
                self.lookup[column, row] = tile
        total = sum(tile.expected for tile in self.tiles)
        if not isfinite(total): raise ValueError('Total integrated density is too large')
        if graph.fields.density is None:
            for tile in self.tiles: tile.expected = graph.target_nodes*tile.expected/total if total else 0
        for node in graph.nodes: self.accept(node)

    def key(self, node: Node) -> tuple[int, int]:
        return floor((node.center.x-self.x0)/self.tile_size), floor((node.center.y-self.y0)/self.tile_size)

    def accept(self, node: Node) -> None:
        tile = self.lookup.get(self.key(node))
        if tile is not None: tile.actual += 1

    def score(self, node: Node) -> float:
        x, y = self.key(node)
        return sum(tile.deficit for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (tile := self.lookup.get((x+dx, y+dy))) is not None)

    def select_parent(self, frontier: list[Node], rng: Random) -> int:
        choices = rng.sample(range(len(frontier)), min(len(frontier), self.settings.parent_choices))
        return max(choices, key=lambda index: self.score(frontier[index]))

    def seed(self, rng: Random, *, fill_area: bool = False) -> Node | None:
        if self.pending_components:
            component = self.pending_components[0]
            x0,y0,x1,y1 = component.bounds
            point = component.representative_point()
            x,y = (point.x,point.y) if self.component_attempts == 0 else (rng.uniform(x0,x1),rng.uniform(y0,y1))
            node = self.graph._new_node(x,y,is_seed=True)
            valid = component.covers(node.center) and self.graph.can_place_node(node)
            self.component_attempts += 1
            if valid or self.component_attempts >= 32:
                self.pending_components.pop(0)
                self.component_attempts = 0
            return node if valid else None
        candidates = [tile for tile in self.tiles if fill_area or tile.deficit > 0]
        if not candidates: return None
        tile = rng.choices(candidates, weights=[t.geometry.area/(1+t.actual)**2 if fill_area else t.deficit for t in candidates], k=1)[0]
        x0, y0, x1, y1 = tile.geometry.bounds
        node = self.graph._new_node(rng.uniform(x0, x1), rng.uniform(y0, y1), is_seed=True)
        return node if tile.geometry.covers(node.center) and self.graph.can_place_node(node) else None

    def report(self, attempts: int, reseeds: int) -> CoverageReport:
        return CoverageReport(sum(t.expected for t in self.tiles), sum(t.actual for t in self.tiles), sum(t.deficit for t in self.tiles),
                              sum(t.actual > 0 for t in self.tiles), len(self.tiles), self.tile_size, attempts, reseeds,
                              sum(t.geometry.area for t in self.tiles if t.actual > 0)/sum(t.geometry.area for t in self.tiles) if self.tiles else 0)
