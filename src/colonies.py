"""Explicit colony ownership, symmetric interactions, and spatial diagnostics."""
from __future__ import annotations
from dataclasses import dataclass
from math import atan2, cos, sin, isfinite
from typing import TYPE_CHECKING
import networkx as nx
from shapely.geometry import Point
from .colors import hex2rgb
from .node import Node
from .edge import Edge
if TYPE_CHECKING:
    from .graph import Graph


@dataclass(frozen=True)
class Colony:
    id: str
    seeds: tuple[tuple[float, float], ...]
    weight: float = 1
    color: str = '#a6b7c8'

    def __post_init__(self) -> None:
        if not self.id or not self.seeds: raise ValueError('Colony needs an ID and at least one seed')
        if not isfinite(self.weight) or self.weight <= 0: raise ValueError('Weight must be finite and positive')
        if not all(isfinite(x) and isfinite(y) for x, y in self.seeds): raise ValueError('Seed positions must be finite')
        hex2rgb(self.color)


@dataclass(frozen=True)
class Interaction:
    first: str
    second: str
    attraction: float = 0  # [-1, 1]: avoidance through attraction; independent of joining.
    allow_join: bool = False
    clearance: float = 0  # Minimum distance between visible rival geometry.

    def __post_init__(self) -> None:
        if not self.first or not self.second or self.first == self.second: raise ValueError('Interactions require two distinct colony IDs')
        if not isfinite(self.attraction) or not -1 <= self.attraction <= 1: raise ValueError('Attraction must be between -1 and 1')
        if type(self.allow_join) is not bool: raise ValueError('Join permission must be boolean')
        if not isfinite(self.clearance) or self.clearance < 0: raise ValueError('Clearance must be finite and nonnegative')
        if self.allow_join and self.clearance: raise ValueError('Joining and rival exclusion are mutually exclusive for a pair')


@dataclass(frozen=True)
class ColonySettings:
    colonies: tuple[Colony, ...]
    interactions: tuple[Interaction, ...] = ()
    influence_distance: float = 100
    target_bridges: int = 0
    bridge_attempts: int = 1000
    bridge_distance: float = 40

    def __post_init__(self) -> None:
        ids = [colony.id for colony in self.colonies]
        if not ids or len(ids) != len(set(ids)): raise ValueError('Colony IDs must be nonempty and unique')
        if not isfinite(sum(colony.weight for colony in self.colonies)): raise ValueError('Total colony weight must be finite')
        pairs: set[frozenset[str]] = set()
        for rule in self.interactions:
            pair = frozenset((rule.first, rule.second))
            if not pair.issubset(ids) or pair in pairs: raise ValueError('Unknown or duplicate interaction pair')
            pairs.add(pair)
        for value in (self.influence_distance, self.bridge_distance):
            if not isfinite(value) or value <= 0: raise ValueError('Interaction distances must be finite and positive')
        for value in (self.target_bridges, self.bridge_attempts):
            if type(value) is not int or value < 0: raise ValueError('Bridge limits must be nonnegative integers')

    def rule(self, first: str | None, second: str | None) -> Interaction | None:
        return next((rule for rule in self.interactions if {rule.first, rule.second} == {first, second}), None)

    def bias(self, graph: Graph, parent: Node, angle: float) -> float:
        radius = self.influence_distance
        x, y = parent.center.x, parent.center.y
        nearby = [graph._objects[key] for key in graph._index.query((x-radius, y-radius, x+radius, y+radius))]
        candidates = [n for n in nearby if isinstance(n, Node) and n.colony_id != parent.colony_id and n.distance_to(parent) <= radius
                      and (rule := self.rule(parent.colony_id, n.colony_id)) is not None and rule.attraction != 0]
        if not candidates: return angle
        target = min(candidates, key=lambda n: (n.distance_to(parent), n.id))
        rule = self.rule(parent.colony_id, target.colony_id)
        assert rule is not None
        direction = atan2(target.center.y-y, target.center.x-x)
        strength = abs(rule.attraction)
        dx, dy = (1-strength)*cos(angle)+rule.attraction*cos(direction), (1-strength)*sin(angle)+rule.attraction*sin(direction)
        return atan2(dy, dx) if abs(dx)+abs(dy) > 1e-12 else angle


def owners(obj: Node | Edge) -> set[str]:
    ids = (obj.colony_id,) if isinstance(obj, Node) else (obj.start_node.colony_id, obj.end_node.colony_id)
    return {key for key in ids if key is not None}


def visible_distance(first: Node | Edge, second: Node | Edge) -> float:
    if isinstance(first, Node) and isinstance(second, Node): return first.distance_to(second)-first.outer_radius-second.outer_radius
    if isinstance(first, Node):
        assert isinstance(second, Edge)
        return float(second.footprint.distance(first.center))-first.outer_radius
    if isinstance(second, Node): return float(first.footprint.distance(second.center))-second.outer_radius
    return float(first.footprint.distance(second.footprint))


def rival_clearance(settings: ColonySettings, first: Node | Edge, second: Node | Edge) -> float:
    return max((rule.clearance for a in owners(first) for b in owners(second) if a != b and (rule := settings.rule(a, b)) is not None), default=0)


@dataclass(frozen=True)
class ColonyPopulation:
    colony_id: str
    nodes: int
    attempts: int
    accepted: int
    rejected: int
    components: int
    territory_fraction: float


@dataclass(frozen=True)
class ColonyReport:
    populations: tuple[ColonyPopulation, ...]
    components: int
    bridges: int
    bridge_attempts: int
    bridge_shortfall: int
    clearance_rejections: int
    territory_samples: int


def territory_counts(graph: Graph, resolution: int) -> tuple[dict[str, int], int]:
    """Nearest-center allocation of a deterministic grid of usable region samples."""
    if type(resolution) is not int or not 1 <= resolution <= 200: raise ValueError('Territory resolution must be 1..200')
    counts: dict[str, int] = {}
    samples = 0
    if not graph.nodes: return counts, samples
    x0, y0, x1, y1 = graph.outline_polygon.bounds
    for row in range(resolution):
        for column in range(resolution):
            point = Point(x0+(column+0.5)*(x1-x0)/resolution, y0+(row+0.5)*(y1-y0)/resolution)
            if not graph.outline_polygon.covers(point) or any(area.covers(point) for area in graph._illegal_areas): continue
            nearest = min(graph.nodes, key=lambda n: (n.center.distance(point), n.id))
            if nearest.colony_id is not None: counts[nearest.colony_id] = counts.get(nearest.colony_id, 0)+1
            samples += 1
    return counts, samples


def component_ids(graph: Graph) -> dict[str, str]:
    return {key: min(component) for component in nx.connected_components(graph.to_networkx()) for key in component}
