"""Contour semantics, readable scale limits, and bounded geometric guidance."""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, ceil, hypot, isfinite
from typing import Literal

from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import nearest_points
from shapely.geometry.base import BaseGeometry

Area = Polygon | MultiPolygon


def valid_area(area: Area) -> None:
    if not isinstance(area, (Polygon, MultiPolygon)) or area.is_empty or not area.is_valid or area.area <= 0:
        raise ValueError('Contours must be valid nonempty polygons; repair is never implicit')
    if not all(isfinite(v) for v in area.bounds): raise ValueError('Contour bounds must be finite')


@dataclass(frozen=True)
class RegionSpec:
    shape: Area
    mode: Literal['inside', 'outside', 'band'] = 'inside'
    padding: float = 0
    canvas: Area | None = None
    band_width: float = 20

    def resolve(self) -> Area:
        valid_area(self.shape)
        if not isfinite(self.padding) or self.padding < 0: raise ValueError('Padding must be finite and nonnegative')
        if self.mode not in ('inside', 'outside', 'band'): raise ValueError('Unknown region mode')
        if self.canvas is not None: valid_area(self.canvas)
        result: BaseGeometry
        if self.mode == 'inside': result = self.shape.buffer(-self.padding) if self.padding else self.shape
        elif self.mode == 'outside':
            if self.canvas is None: raise ValueError('Outside mode requires a finite canvas')
            result = self.canvas.buffer(-self.padding).difference(self.shape.buffer(self.padding))
        else:
            if not isfinite(self.band_width) or self.band_width <= 0: raise ValueError('Band width must be finite and positive')
            result = self.shape.boundary.buffer(self.band_width/2).buffer(-self.padding)
            if self.canvas is not None: result = result.intersection(self.canvas)
        if not isinstance(result, (Polygon, MultiPolygon)): raise ValueError('Region has no polygonal usable area')
        valid_area(result)
        return result


@dataclass(frozen=True)
class Readability:
    """Minimum dimensions in output pixels/points; scale is output units per world unit."""
    output_scale: float = 1
    stroke: float = 0.5
    hole_diameter: float = 1
    edge_gap: float = 0.75
    separation: float = 0.75

    def __post_init__(self) -> None:
        if not isfinite(self.output_scale) or self.output_scale <= 0: raise ValueError('Output scale must be positive')
        if not all(isfinite(v) and v >= 0 for v in (self.stroke, self.hole_diameter, self.edge_gap, self.separation)): raise ValueError('Readable dimensions must be finite and nonnegative')

    def radius_minimum(self, ratio: float) -> float:
        if ratio == 0 and self.hole_diameter: raise ValueError('A readable hole requires a positive ring ratio')
        return max(self.stroke/(1-ratio), self.hole_diameter/(2*ratio) if ratio else 0)/self.output_scale


@dataclass(frozen=True)
class ContourSettings:
    mode: Literal['contain', 'follow', 'terminate'] = 'contain'
    adaptive: bool = True
    minimum_radius: float = 1
    maximum_neighbor_ratio: float = 2
    width_resolution: float = 10
    width_samples: int = 10000
    width_divisor: float = 4
    anchor_spacing: float = 15
    max_anchors: int = 2000
    boundary_fraction: float = 0.6
    tangent_window: float = 10
    guidance: float = 0.85
    tolerance: float = 0.5  # Output units, converted with readability.output_scale.
    strict_terminals: bool = False
    readability: Readability = Readability()

    def __post_init__(self) -> None:
        if self.mode not in ('contain', 'follow', 'terminate'): raise ValueError('Unknown boundary treatment')
        for value in (self.minimum_radius, self.width_resolution, self.width_divisor, self.anchor_spacing, self.tangent_window):
            if not isfinite(value) or value <= 0: raise ValueError('Contour dimensions must be positive and finite')
        if not isfinite(self.maximum_neighbor_ratio) or self.maximum_neighbor_ratio < 1: raise ValueError('Neighbor ratio must be at least one')
        if not all(isfinite(v) and 0 <= v <= 1 for v in (self.boundary_fraction, self.guidance)): raise ValueError('Fractions must be in [0,1]')
        if not isfinite(self.tolerance) or self.tolerance < 0: raise ValueError('Tolerance must be nonnegative')
        for count in (self.width_samples, self.max_anchors):
            if type(count) is not int or count < 4: raise ValueError('Sampling budgets must be integers of at least four')


@dataclass(frozen=True)
class BoundaryAnchor:
    center: Point
    component: int
    arc: float
    tangent: float


class DistanceField:
    """Signed distance in world units; positive inside the resolved usable region."""
    def __init__(self, region: Area) -> None:
        valid_area(region)
        self.region = region

    def sample(self, x: float, y: float) -> float:
        if not isfinite(x) or not isfinite(y): raise ValueError('Sample coordinates must be finite')
        point = Point(x, y)
        distance = float(self.region.boundary.distance(point))
        return distance if self.region.covers(point) else -distance


class LocalWidth:
    """Bounded sampled distance-ridge estimate, not an exact medial axis.

    Eight-neighbor maxima approximate inscribed-disk ridges. Sampling automatically
    coarsens to max_samples; features below this resolution may be missed.
    """
    def __init__(self, region: Area, resolution: float, max_samples: int) -> None:
        if not isfinite(resolution) or resolution <= 0 or type(max_samples) is not int or max_samples < 4: raise ValueError('Width resolution and sampling budget must be positive')
        self.distance = DistanceField(region)
        x0, y0, x1, y1 = region.bounds
        self.resolution = max(resolution, ((x1-x0)*(y1-y0)/max_samples)**0.5)
        nx, ny = max(1, ceil((x1-x0)/self.resolution)), max(1, ceil((y1-y0)/self.resolution))
        while nx*ny > max_samples:
            self.resolution *= 1.1
            nx, ny = max(1, ceil((x1-x0)/self.resolution)), max(1, ceil((y1-y0)/self.resolution))
        values = {(i, j): self.distance.sample(x0+(i+0.5)*self.resolution, y0+(j+0.5)*self.resolution) for i in range(nx) for j in range(ny)}
        self.ridges = [(x0+(i+0.5)*self.resolution, y0+(j+0.5)*self.resolution, radius) for (i, j), radius in values.items()
                       if radius > 0 and all(radius >= values.get((i+di, j+dj), -1) for di in (-1, 0, 1) for dj in (-1, 0, 1))]

    def sample(self, x: float, y: float) -> float:
        disks = [(hypot(x-cx, y-cy), radius) for cx, cy, radius in self.ridges if hypot(x-cx, y-cy) <= radius+self.resolution]
        if disks: return 2*min(disks)[1]
        return 2*max(0, self.distance.sample(x, y))


class ContourGuide:
    def __init__(self, region: Area, settings: ContourSettings, minimum_radius: float, preferred_radius: float) -> None:
        self.region, self.settings = region, settings
        self.distance = DistanceField(region)
        self.width = LocalWidth(region, settings.width_resolution, settings.width_samples)
        inset = region.buffer(-(minimum_radius+1e-7))
        original_polygons = [region] if isinstance(region, Polygon) else list(region.geoms)
        original_rings = [LineString(r.coords) for polygon in original_polygons for r in (polygon.exterior, *polygon.interiors)]
        perimeter = sum(r.length for r in original_rings)
        self.boundary_samples: list[tuple[Point, float]] = []
        for ring in original_rings:
            count = max(1, int(settings.max_anchors*ring.length/perimeter))
            for i in range(count):
                if len(self.boundary_samples) >= settings.max_anchors: break
                self.boundary_samples.append((ring.interpolate(i*ring.length/count), ring.length/count))
        self.unreadable_boundary_samples = sum(inset.is_empty or inset.distance(point) > 2*minimum_radius for point, _ in self.boundary_samples)
        polygons = [inset] if isinstance(inset, Polygon) else list(inset.geoms) if isinstance(inset, MultiPolygon) else []
        rings = [LineString(ring.coords) for polygon in polygons for ring in (polygon.exterior, *polygon.interiors) if not ring.is_empty]
        total = sum(ring.length for ring in rings)
        spacing = max(settings.anchor_spacing, total/max(1, settings.max_anchors-len(rings)))
        self.anchors: list[BoundaryAnchor] = []
        for component, ring in enumerate(rings):
            count = max(1, int(ring.length/spacing))
            # Include vertices where direction changes sharply, subject to the same hard budget.
            distances = {i*ring.length/count for i in range(count)}
            coords = list(ring.coords)
            for i in range(1, len(coords)-1):
                a, b, c = coords[i-1], coords[i], coords[i+1]
                u, v = (b[0]-a[0], b[1]-a[1]), (c[0]-b[0], c[1]-b[1])
                if u[0]*v[0]+u[1]*v[1] < 0.7*hypot(*u)*hypot(*v): distances.add(float(ring.project(Point(b))))
            for arc in sorted(distances):
                if len(self.anchors) >= settings.max_anchors: break
                point = ring.interpolate(arc)
                radius = max(minimum_radius, min(preferred_radius, self.width.sample(point.x, point.y)/settings.width_divisor))
                usable = region.buffer(-(radius+1e-7))
                if not usable.is_empty:
                    shifted = nearest_points(point, usable.boundary)[1]
                    if point.distance(shifted) <= 2*radius: point = shifted
                before, after = ring.interpolate((arc-settings.tangent_window/2)%ring.length), ring.interpolate((arc+settings.tangent_window/2)%ring.length)
                self.anchors.append(BoundaryAnchor(point, component, arc, atan2(after.y-before.y, after.x-before.x)))

    def nearest(self, point: Point) -> BoundaryAnchor | None:
        return min(self.anchors, key=lambda anchor: anchor.center.distance(point)) if self.anchors else None

    def terminal_center(self, point: Point, radius: float) -> Point | None:
        inset = self.region.buffer(-(radius+1e-7))
        if inset.is_empty: return None
        return nearest_points(point, inset.boundary)[1]


@dataclass(frozen=True)
class ContourReport:
    boundary_coverage: float
    boundary_nodes: int
    unreadable_boundary_samples: int
    terminal_count: int
    unanchored_terminals: tuple[str, ...]
    terminal_distances: tuple[float, ...]
    unanchored_reasons: tuple[tuple[str, str], ...]
    readable_failures: int
    width_failures: int
    neighbor_ratio_failures: int
    strict_satisfied: bool
    sampled_width_resolution: float
    minimum_radius: float
    maximum_radius: float
