"""Versioned geometry logs and a clock independent of graph generation."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from math import isfinite
from pathlib import Path
from typing import Any, Literal, TextIO, TYPE_CHECKING
import json
import networkx as nx
from shapely.geometry import mapping, shape, Polygon, MultiPolygon
from .colors import rgb_normalized
from .node import Node, NodeShape
from .edge import Edge, EdgeStyle
from .fields import ScalarField, ConstantField, ImageField, CallableField
if TYPE_CHECKING:
    from .graph import Graph

EventKind = Literal['seed', 'branch', 'loop', 'join', 'remove', 'complete']


def field_metadata(value: ScalarField | None) -> dict[str, Any] | None:
    if value is None: return None
    if isinstance(value, (ConstantField, ImageField)): return dict(type=type(value).__name__, parameters=asdict(value))
    if isinstance(value, CallableField): return dict(type='CallableField', callable_name=getattr(value.function, '__qualname__', type(value.function).__name__))
    return dict(type=type(value).__name__, implementation='external; recorded geometry is authoritative')


@dataclass(frozen=True)
class NodeRecord:
    id: str
    x: float
    y: float
    inner_radius: float
    outer_radius: float
    buffer: float
    min_edge_length: float
    preferred_spacing: float
    color: str
    opacity: float
    is_seed: bool
    colony_id: str | None
    shape: NodeShape = "circle"

    @classmethod
    def capture(cls, node: Node) -> NodeRecord:
        return cls(node.id, node.center.x, node.center.y, node.inner_radius, node.outer_radius, node.buffer, node.min_edge_length,
                   node.preferred_spacing, node.color, node.opacity, node.is_seed_node, node.colony_id, node.shape)

    def restore(self) -> Node:
        if not isinstance(self.id, str) or not self.id: raise ValueError('Node IDs must be nonempty strings')
        node = Node(self.x, self.y, outer_radius=self.outer_radius, inner_radius=self.inner_radius, buffer=self.buffer, min_edge_length=self.min_edge_length,
                    preferred_spacing=self.preferred_spacing, color=self.color, opacity=self.opacity, is_seed_node=self.is_seed, colony_id=self.colony_id, shape=self.shape)
        node.id = self.id
        return node


@dataclass(frozen=True)
class EdgeRecord:
    start: str
    end: str
    thickness: float
    gap: float
    color: str
    opacity: float
    style: EdgeStyle = "solid"

    @classmethod
    def capture(cls, edge: Edge) -> EdgeRecord:
        return cls(edge.start_node.id, edge.end_node.id, edge.thickness, edge.edge_node_distance, edge.color, edge.opacity, edge.style)

    def restore(self, nodes: dict[str, Node]) -> Edge:
        return Edge(nodes[self.start], nodes[self.end], thickness=self.thickness, edge_node_distance=self.gap, color=self.color, opacity=self.opacity, style=self.style)


@dataclass(frozen=True)
class Event:
    kind: EventKind
    node: NodeRecord | None = None
    edge: EdgeRecord | None = None
    removed: tuple[str, ...] = ()
    status: str | None = None
    attempts: int | None = None


@dataclass(frozen=True)
class TextRecord:
    color: str
    opacity: float
    bounds: tuple[float, float, float, float]
    path: tuple[tuple[int, tuple[float, ...]], ...]
    specification: dict[str, Any]


@dataclass(frozen=True)
class Scene:
    region: dict[str, Any]
    border: bool
    texts: tuple[TextRecord, ...]
    configuration: dict[str, Any]
    minimum_scale: float = 0

    @classmethod
    def capture(cls, graph: Graph) -> Scene:
        run = graph.growth()
        parameters = ('target_nodes', 'target_seed_nodes', 'target_extra_edges', 'extra_edge_elongation_factor', 'node_inner_radius', 'node_outer_radius',
                      'node_shape', 'edge_style', 'node_buffer', 'edge_thickness', 'edge_node_distance', 'edge_length_min', 'edge_length_max', 'node_color', 'edge_color', 'node_opacity', 'edge_opacity', 'spatial_backend', 'cell_size', 'border_color', 'border_width')
        configuration = {name: getattr(graph, name) for name in parameters}
        configuration.update(seed=graph.seed, growth=asdict(run.settings), angles=asdict(graph.angles),
                             colonies=asdict(graph.colonies) if graph.colonies else None, contours=asdict(graph.contours) if graph.contours else None,
                             obstacles=[mapping(area) for area in graph._illegal_areas], policy=type(run.policy).__name__,
                             fields={name: field_metadata(getattr(graph.fields, name)) for name in ('radius', 'length', 'thickness', 'density', 'coordinated_scale')},
                             scale_limits=graph.fields.scale_limits, spacing_limits=graph.fields.spacing_limits, ring_ratio=graph.fields.ring_ratio, refinement_steps=graph.fields.refinement_steps,
                             direction_callback=graph.node_direction_function is not None, length_callback=graph.node_length_function is not None)
        texts = tuple(TextRecord(t.text.color, t.text.opacity, t.bounds, tuple((int(kind), tuple(points)) for kind, points in t.path), asdict(t.text)) for t in graph.texts)
        return cls(dict(mapping(graph.outline_polygon)), graph.draw_border, texts, configuration, graph.contours.readability.output_scale if graph.contours else 0)


@dataclass
class ReplayState:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    parents: dict[str, str | None] = field(default_factory=dict)
    network: nx.Graph[str] = field(default_factory=nx.Graph)
    seen: set[str] = field(default_factory=set)
    status: str | None = None

    def apply(self, event: Event) -> None:
        if (event.node is not None) != (event.kind in ('seed', 'branch')): raise ValueError('Unexpected node payload')
        if (event.edge is not None) != (event.kind in ('branch', 'join', 'loop')): raise ValueError('Unexpected edge payload')
        if event.kind != 'remove' and event.removed: raise ValueError('Unexpected removal payload')
        if event.kind != 'complete' and (event.status is not None or event.attempts is not None): raise ValueError('Unexpected completion payload')
        if self.status is not None: raise ValueError('Events cannot follow completion')
        if event.kind in ('seed', 'branch'):
            if event.node is None or event.node.id in self.seen: raise ValueError('Missing or reused node ID')
            if event.kind == 'branch' and (event.edge is None or event.edge.end != event.node.id or event.edge.start not in self.nodes): raise ValueError('Branch parent must already exist')
            node = event.node.restore()
            self.nodes[node.id] = node
            self.seen.add(node.id)
            self.network.add_node(node.id, colony_id=node.colony_id)
            self.parents[node.id] = event.edge.start if event.kind == 'branch' and event.edge else None
        if event.kind in ('branch', 'loop', 'join'):
            edge = event.edge
            if edge is None or edge.start not in self.nodes or edge.end not in self.nodes or edge.start == edge.end or self.network.has_edge(edge.start, edge.end): raise ValueError('Invalid or duplicate edge reference')
            connected = nx.has_path(self.network, edge.start, edge.end)
            if event.kind == 'join' and connected: raise ValueError('Join must connect different components')
            if event.kind == 'loop' and not connected: raise ValueError('Loop must remain within a component')
            self.edges.append(edge.restore(self.nodes))
            self.network.add_edge(edge.start, edge.end, bridge=event.kind == 'join', loop=event.kind == 'loop')
        elif event.kind == 'remove':
            for key in event.removed:
                if key not in self.nodes or self.network.degree(key): raise ValueError('Only existing isolated nodes can be removed')
                del self.nodes[key]
                del self.parents[key]
                self.network.remove_node(key)
        elif event.kind == 'complete':
            if not event.status: raise ValueError('Completion needs a status')
            self.status = event.status
        elif event.kind not in ('seed', 'branch', 'loop', 'join'): raise ValueError('Unknown event kind')


@dataclass(frozen=True)
class EventLog:
    scene: Scene
    events: tuple[Event, ...]
    version: int = 1

    def validate(self) -> ReplayState:
        if self.version != 1: raise ValueError('Unsupported replay version')
        region = shape(self.scene.region)
        if not isinstance(region, (Polygon, MultiPolygon)) or region.is_empty or not region.is_valid: raise ValueError('Invalid replay region')
        if not isfinite(self.scene.minimum_scale) or self.scene.minimum_scale < 0: raise ValueError('Invalid readability scale')
        if type(self.scene.border) is not bool: raise ValueError('Border flag must be boolean')
        border_width = self.scene.configuration.get('border_width',0.5)
        border_color = self.scene.configuration.get('border_color','#a6a6a6')
        if not isinstance(border_width,(int,float)) or not isfinite(border_width) or border_width <= 0: raise ValueError('Invalid border width')
        if not isinstance(border_color,str): raise ValueError('Invalid border colour')
        rgb_normalized(border_color)
        json.dumps(self.scene.configuration, allow_nan=False)
        for text in self.scene.texts:
            rgb_normalized(text.color)
            if not isfinite(text.opacity) or not 0 <= text.opacity <= 1: raise ValueError('Invalid text opacity')
            if len(text.bounds) != 4 or not all(isfinite(v) for v in text.bounds) or text.bounds[0] >= text.bounds[2] or text.bounds[1] >= text.bounds[3]: raise ValueError('Invalid text bounds')
            for kind, points in text.path:
                if kind not in (0, 1, 2, 3) or len(points) != {0: 2, 1: 2, 2: 6, 3: 0}[kind] or not all(isfinite(v) for v in points): raise ValueError('Invalid text path')
        state = ReplayState()
        for event in self.events: state.apply(event)
        return state

    def save(self, path: str | Path) -> None:
        self.validate()
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('w', encoding='utf-8') as stream:
            stream.write(json.dumps(dict(version=self.version, scene=asdict(self.scene)), allow_nan=False)+'\n')
            for event in self.events: stream.write(json.dumps(asdict(event), allow_nan=False)+'\n')

    @classmethod
    def load(cls, path: str | Path) -> EventLog:
        try:
            with Path(path).open(encoding='utf-8') as stream:
                header = json.loads(next(stream))
                if header['version'] != 1: raise ValueError('Unsupported replay version')
                data = header['scene']
                texts = tuple(TextRecord(t['color'], t['opacity'], tuple(t['bounds']), tuple((kind, tuple(points)) for kind, points in t['path']), t['specification']) for t in data['texts'])
                scene = Scene(data['region'], data['border'], texts, data['configuration'], data['minimum_scale'])
                events = []
                for line in stream:
                    item = json.loads(line)
                    events.append(Event(item['kind'], NodeRecord(**item['node']) if item['node'] else None, EdgeRecord(**item['edge']) if item['edge'] else None,
                                        tuple(item['removed']), item['status'], item['attempts']))
            log = cls(scene, tuple(events))
            log.validate()
            return log
        except (KeyError, TypeError, StopIteration, json.JSONDecodeError) as error:
            raise ValueError('Malformed replay log') from error


class EventRecorder:
    """Optional recorder; streaming without retention avoids keeping the event list."""
    def __init__(self, graph: Graph, *, path: str | Path | None = None, retain: bool = True) -> None:
        if graph._event_listener is not None: raise ValueError('Graph already has a recorder')
        if graph.edges: raise ValueError('Attach recording before accepting edges')
        if graph._generator is not None and (graph._generator.attempts or graph._generator.done): raise ValueError('Attach recording before growth starts')
        if not retain and path is None: raise ValueError('Non-retained recording requires a destination')
        self.graph, self.retain = graph, retain
        self.scene = Scene.capture(graph)
        self.events: list[Event] = []
        self.stream: TextIO | None = None
        self.closed = False
        if path is not None:
            destination = Path(path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            self.stream = destination.open('w', encoding='utf-8')
            self.stream.write(json.dumps(dict(version=1, scene=asdict(self.scene)), allow_nan=False)+'\n')
        for node in graph.nodes: self._write(Event('seed', node=NodeRecord.capture(node)))
        graph._event_listener = self._listen

    def _write(self, event: Event) -> None:
        if self.retain: self.events.append(event)
        if self.stream is not None:
            self.stream.write(json.dumps(asdict(event), allow_nan=False)+'\n')
            self.stream.flush()

    def _listen(self, kind: str, obj: Node | Edge | tuple[str, ...]) -> None:
        if kind == 'seed' and isinstance(obj, Node): self._write(Event('seed', node=NodeRecord.capture(obj)))
        elif kind in ('branch', 'join', 'loop') and isinstance(obj, Edge):
            if kind == 'branch': self._write(Event('branch', node=NodeRecord.capture(obj.end_node), edge=EdgeRecord.capture(obj)))
            elif kind == 'join': self._write(Event('join', edge=EdgeRecord.capture(obj)))
            else: self._write(Event('loop', edge=EdgeRecord.capture(obj)))
        elif kind == 'remove' and isinstance(obj, tuple): self._write(Event('remove', removed=obj))
        elif kind == 'complete': self._write(Event('complete', status=self.graph.growth().status.value, attempts=self.graph.growth().attempts))
        else: raise ValueError('Invalid graph event')

    def snapshot(self) -> EventLog:
        if not self.retain: raise ValueError('Read the streamed log instead')
        return EventLog(self.scene, tuple(self.events))

    def close(self) -> None:
        if self.graph._event_listener == self._listen: self.graph._event_listener = None
        if self.stream is not None: self.stream.close()
        self.closed = True

    def __enter__(self) -> EventRecorder:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class Playback:
    """User-controlled replay clock; times are seconds, unrelated to generation time."""
    def __init__(self, log: EventLog, *, seconds_per_event: float = 0.1, speed: float = 1) -> None:
        log.validate()
        if not isfinite(seconds_per_event) or seconds_per_event <= 0: raise ValueError('Event duration must be finite and positive')
        self.log = log
        self.seconds_per_event = seconds_per_event
        self.events = tuple(event for event in log.events if event.kind != 'complete')
        self.position = 0.0
        self.paused = False
        self.speed = speed

    @property
    def speed(self) -> float:
        return self._speed

    @speed.setter
    def speed(self, value: float) -> None:
        if not isfinite(value) or value <= 0: raise ValueError('Playback speed must be finite and positive')
        self._speed = value

    @property
    def duration(self) -> float:
        return len(self.events)*self.seconds_per_event

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def seek(self, seconds: float) -> float:
        if not isfinite(seconds) or seconds < 0: raise ValueError('Seek time must be finite and nonnegative')
        self.position = min(seconds, self.duration)
        return self.position

    def advance(self, elapsed: float) -> float:
        if not isfinite(elapsed) or elapsed < 0: raise ValueError('Elapsed time must be finite and nonnegative')
        if not self.paused: self.seek(self.position+elapsed*self.speed)
        return self.position

    def cursor(self) -> tuple[int, float]:
        if self.position >= self.duration: return len(self.events), 0
        units = self.position/self.seconds_per_event
        index = int(units)
        return index, units-index
