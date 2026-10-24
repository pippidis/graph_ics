"""Independent STRtree broad phase for scalable final-geometry validation."""
from dataclasses import dataclass
from shapely.geometry import box
from shapely.strtree import STRtree
from .graph import Graph
from .node import Node
from .edge import Edge
from .colonies import rival_clearance, visible_distance


@dataclass(frozen=True)
class ValidationReport:
    objects: int
    candidate_pairs: int


def validate_graph(graph: Graph) -> ValidationReport:
    objects: list[Node | Edge] = [*graph.nodes, *graph.edges]
    envelopes = []
    gap = max((rule.clearance for rule in graph.colonies.interactions), default=0) if graph.colonies else 0
    for obj in objects:
        if not graph.in_bounds(obj) or graph.in_illegal_areas(obj): raise ValueError('Object violates region or obstacle geometry')
        if isinstance(obj, Node):
            radius = max(obj.buffer_radius+obj.min_edge_length, obj.preferred_spacing)
            x, y = obj.center.x, obj.center.y
            envelopes.append(box(x-radius, y-radius, x+radius, y+radius))
        else: envelopes.append(box(*obj.footprint.bounds))
    tree = STRtree(envelopes)
    checked = 0
    for i, obj in enumerate(objects):
        query = envelopes[i].buffer(gap, join_style='mitre') if gap else envelopes[i]
        for raw_index in tree.query(query):
            j = int(raw_index)
            if j <= i: continue
            other = objects[j]
            checked += 1
            overlap = obj.overlap(other) if isinstance(obj, Edge) else other.overlap(obj) if isinstance(other, Edge) else obj.overlap(other)
            if overlap: raise ValueError('Accepted geometry overlaps')
            if graph.colonies is not None:
                required = rival_clearance(graph.colonies, obj, other)
                if required and visible_distance(obj, other)+1e-9 < required: raise ValueError('Rival clearance violated')
    report = graph.growth().quality_report()
    if report.minimum_angle is not None and report.minimum_angle+1e-9 < graph.angles.minimum: raise ValueError('Junction violates hard angle minimum')
    if graph.growth().done and graph.growth().settings.remove_isolated_nodes and any(degree == 0 for _, degree in graph.nx_graph.degree()): raise ValueError('Finished graph has isolated nodes')
    return ValidationReport(len(objects), checked)
