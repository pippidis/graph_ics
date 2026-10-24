"""Deterministic, attempt-bounded frontier growth over one authoritative Graph."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from random import Random
from math import isfinite

import networkx as nx
from typing import TYPE_CHECKING, Protocol

from .colonies import ColonyPopulation, ColonyReport, territory_counts
from .quality import QualityReport, incident_angle
from itertools import combinations
from .edge import Edge
from .coverage import CoverageSettings, CoverageTracker, CoverageReport
from .node import Node

if TYPE_CHECKING:
    from .graph import Graph


class GrowthStatus(str, Enum):
    RUNNING = 'running'
    TARGET_REACHED = 'target_reached'
    FRONTIER_EXHAUSTED = 'frontier_exhausted'
    ATTEMPT_BUDGET_EXHAUSTED = 'attempt_budget_exhausted'
    CANCELLED = 'cancelled'
    CONSTRAINT_UNMET = 'constraint_unmet'
    CLEANED_UNDERFILLED = 'cleaned_underfilled'
    NODE_LIMIT_REACHED = 'node_limit_reached'
    FILL_SEARCH_EXHAUSTED = 'fill_search_exhausted'


class GrowthPolicy(Protocol):
    """Select an active parent; direction is independently supplied by Graph callbacks."""
    def select_parent(self, frontier: tuple[Node, ...], rng: Random) -> int: ...


@dataclass(frozen=True)
class RandomFrontier:
    def select_parent(self, frontier: tuple[Node, ...], rng: Random) -> int:
        return rng.randrange(len(frontier))


@dataclass(frozen=True)
class NewestTip:
    def select_parent(self, frontier: tuple[Node, ...], rng: Random) -> int:
        return max(range(len(frontier)), key=lambda i: frontier[i].id)


@dataclass(frozen=True)
class GrowthSettings:
    failures_per_parent: int = 30
    seed_attempts: int = 100
    total_attempts: int | None = None
    coverage: CoverageSettings | None = None
    max_degree: int = 6
    loop_attempts: int = 1000
    loop_distance: float = 40
    remove_isolated_nodes: bool = True
    refill_passes: int = 0
    refill_attempts: int = 1000
    fill_area: bool = False

    def __post_init__(self) -> None:
        if type(self.fill_area) is not bool: raise ValueError('fill_area must be boolean')
        if type(self.remove_isolated_nodes) is not bool: raise ValueError('Cleanup must be boolean')
        for value in (self.refill_passes, self.refill_attempts):
            if type(value) is not int or value < 0: raise ValueError('Refill limits must be nonnegative integers')
        for value in (self.failures_per_parent, self.seed_attempts, self.max_degree, self.loop_attempts):
            if type(value) is not int or value <= 0: raise ValueError('Attempt limits must be positive integers')
        if self.total_attempts is not None and (type(self.total_attempts) is not int or self.total_attempts < 0):
            raise ValueError('Total attempts must be a nonnegative integer or None')
        if not isfinite(self.loop_distance) or self.loop_distance <= 0: raise ValueError('Loop distance must be finite and positive')


@dataclass(frozen=True)
class Addition:
    node: Node
    edge: Edge | None  # None identifies an accepted seed.
    colony_id: str | None = None


@dataclass(frozen=True)
class Join:
    edge: Edge
    first_colony: str
    second_colony: str
    first_component: str
    second_component: str


@dataclass(frozen=True)
class Completion:
    status: GrowthStatus
    attempts: int
    nodes: int


@dataclass(frozen=True)
class StepResult:
    additions: tuple[Addition, ...]
    attempts: int
    total_attempts: int
    active_parents: int
    status: GrowthStatus
    completion: Completion | None = None
    loop_additions: tuple[Edge, ...] = ()
    removed_node_ids: tuple[str, ...] = ()
    joins: tuple[Join, ...] = ()


class GrowthGenerator:
    """One generator owns a graph until reset; settings/geometry stay fixed during growth.

    Failures accumulate per parent (success does not reset the budget). Retiring a
    parent is a heuristic. A step budget pauses work, whereas total_attempts is a
    terminal run limit. Cancellation retains connected geometry and applies configured cleanup.
    """
    def __init__(self, graph: Graph, *, settings: GrowthSettings | None = None, policy: GrowthPolicy | None = None) -> None:
        if graph._generator is not None: raise ValueError('This graph already has a generator; use graph.growth() or reset it')
        self.graph = graph
        self.settings = settings or GrowthSettings()
        if self.settings.fill_area:
            if graph.colonies is not None or policy is not None: raise ValueError('Area fill currently requires unowned coverage growth')
            coverage = self.settings.coverage or CoverageSettings(reseed_attempts=5000)
            self.settings = replace(self.settings, coverage=replace(coverage, seed_components=True, reseed_interval=coverage.reseed_interval or 100))
        if policy is not None and self.settings.coverage is not None: raise ValueError('Coverage scheduling and an explicit parent policy cannot be combined')
        if policy is not None and graph.colonies is not None: raise ValueError('Colonies use weighted scheduling instead of an explicit parent policy')
        self.policy = policy or RandomFrontier()
        self.bridge_attempts = self.bridges_added = 0
        self._step_joins: list[Join] = []
        self._colony_attempts: dict[str, int] = {}
        self._colony_accepted: dict[str, int] = {}
        self.coverage = CoverageTracker(graph, self.settings.coverage) if self.settings.coverage is not None else None
        self.reseed_attempts = self.reseeds = self.loop_attempts = self.loops_added = 0
        self.node_stop: GrowthStatus | None = None
        self.loop_stop: str | None = None
        self._loop_phase = False
        self._step_loops: list[Edge] = []
        self.rng = graph._rng
        self._frontier = list(graph.nodes)
        self._failures = {node.id: 0 for node in self._frontier}
        self._seed_failures = 0
        self._seeding = len(graph.nodes) < min(graph.target_seed_nodes, graph.target_nodes)
        self.attempts = 0
        self.status = GrowthStatus.RUNNING
        self._reported = False
        self.removed_nodes = self.refill_passes = self.refill_attempts = self.refill_additions = 0
        self.hard_rejections = self.soft_rejections = 0
        self._step_removed: list[str] = []
        graph._generator = self

    @property
    def done(self) -> bool:
        return self.status != GrowthStatus.RUNNING

    def _check_owner(self) -> None:
        if self.graph._generator is not self: raise RuntimeError('Generator was invalidated by graph reset')

    def _can_reseed(self) -> bool:
        return self.graph.colonies is None and self.coverage is not None and self.coverage.settings.allow_components and self.reseed_attempts < self.coverage.settings.reseed_attempts and (self.settings.fill_area or any(t.deficit > 0 for t in self.coverage.tiles))

    def coverage_report(self) -> CoverageReport:
        if self.coverage is None: raise ValueError('Coverage tracking is not enabled')
        return self.coverage.report(self.reseed_attempts, self.reseeds)

    def _bridges_pending(self) -> bool:
        settings = self.graph.colonies
        return settings is not None and self.bridges_added < settings.target_bridges and self.bridge_attempts < settings.bridge_attempts

    def _select_parent(self) -> int:
        settings = self.graph.colonies
        if settings is None:
            return self.coverage.select_parent(self._frontier, self.rng) if self.coverage is not None else self.policy.select_parent(tuple(self._frontier), self.rng)
        active = {node.colony_id for node in self._frontier}
        choices = [colony for colony in settings.colonies if colony.id in active]
        colony = self.rng.choices(choices, weights=[item.weight for item in choices], k=1)[0]
        indices = [index for index, node in enumerate(self._frontier) if node.colony_id == colony.id]
        if self.coverage is not None:
            selected = self.coverage.select_parent([self._frontier[index] for index in indices], self.rng)
            return indices[selected]
        return self.rng.choice(indices)

    def colony_report(self, *, territory_resolution: int = 20) -> ColonyReport:
        settings = self.graph.colonies
        if settings is None: raise ValueError('Colony diagnostics require ColonySettings')
        counts, samples = territory_counts(self.graph, territory_resolution)
        network = self.graph.to_networkx()
        populations: list[ColonyPopulation] = []
        for colony in settings.colonies:
            ids = [node.id for node in self.graph.nodes if node.colony_id == colony.id]
            attempts, accepted = self._colony_attempts.get(colony.id, 0), self._colony_accepted.get(colony.id, 0)
            populations.append(ColonyPopulation(colony.id, len(ids), attempts, accepted, attempts-accepted,
                                               nx.number_connected_components(network.subgraph(ids)), counts.get(colony.id, 0)/samples if samples else 0))
        return ColonyReport(tuple(populations), nx.number_connected_components(network), self.bridges_added, self.bridge_attempts,
                            max(0, settings.target_bridges-self.bridges_added), self.graph.clearance_rejections, samples)

    def _try_bridge(self) -> None:
        settings = self.graph.colonies
        assert settings is not None
        self.bridge_attempts += 1
        first = self.rng.choice(self.graph._nodes)
        radius = settings.bridge_distance
        x, y = first.center.x, first.center.y
        labels = self.graph.component_ids()
        candidates = [self.graph._objects[key] for key in self.graph._index.query((x-radius, y-radius, x+radius, y+radius))]
        nearby = [node for node in candidates if isinstance(node, Node) and node is not first and node.distance_to(first) <= radius
                  and labels[node.id] != labels[first.id] and (rule := settings.rule(first.colony_id, node.colony_id)) is not None and rule.allow_join]
        if not nearby: return
        second = self.rng.choice(nearby)
        if max(self.graph.nx_graph.degree(first.id), self.graph.nx_graph.degree(second.id)) >= self.settings.max_degree: return
        edge = self.graph._new_edge(first, second)
        scale = (self.graph.fields.scale(self.graph.fields.length, first.center.x, first.center.y)+self.graph.fields.scale(self.graph.fields.length, second.center.x, second.center.y))/2
        if edge is None or edge.length > self.graph.edge_length_max*scale*self.graph.extra_edge_elongation_factor or not self._accepts_edge(edge): return
        assert first.colony_id is not None and second.colony_id is not None
        self.graph._accept_loop(edge, bridge=True)
        self.bridges_added += 1
        self._step_joins.append(Join(edge, first.colony_id, second.colony_id, labels[first.id], labels[second.id]))

    def _finish_if_needed(self) -> None:
        exhausted = (self.settings.total_attempts is not None and self.attempts >= self.settings.total_attempts) or (self.refill_passes > 0 and self.refill_attempts >= self.settings.refill_attempts)
        if not self._loop_phase:
            if len(self.graph._nodes) >= self.graph.target_nodes: self.node_stop = GrowthStatus.NODE_LIMIT_REACHED if self.settings.fill_area else GrowthStatus.TARGET_REACHED
            elif exhausted: self.node_stop = GrowthStatus.ATTEMPT_BUDGET_EXHAUSTED
            elif not self._seeding and not self._frontier and not self.graph.boundary_seed_needed() and not self._can_reseed(): self.node_stop = GrowthStatus.FILL_SEARCH_EXHAUSTED if self.settings.fill_area else GrowthStatus.FRONTIER_EXHAUSTED
            if self.node_stop is not None:
                if (self.graph.target_extra_edges or self._bridges_pending()) and not exhausted and len(self.graph.nodes) >= 2: self._loop_phase = True
                else:
                    self.status = self.node_stop
                    if self.graph.target_extra_edges: self.loop_stop = 'total_attempt_budget_exhausted' if exhausted else 'insufficient_nodes'
        if self._loop_phase:
            if self._bridges_pending() and not exhausted: self.loop_stop = None
            elif self.loops_added >= self.graph.target_extra_edges: self.loop_stop = 'target_reached'
            elif exhausted: self.loop_stop = 'total_attempt_budget_exhausted'
            elif self.loop_attempts >= self.settings.loop_attempts: self.loop_stop = 'loop_attempt_budget_exhausted'
            if self.loop_stop is not None: self.status = GrowthStatus.ATTEMPT_BUDGET_EXHAUSTED if exhausted else self.node_stop or GrowthStatus.FRONTIER_EXHAUSTED
        if self.done:
            removed = self._cleanup()
            if (removed or self.refill_passes) and len(self.graph.nodes) < self.graph.target_nodes and not exhausted and self.refill_passes < self.settings.refill_passes and self.refill_attempts < self.settings.refill_attempts:
                self.refill_passes += 1
                self._frontier = [n for n in self.graph.nodes if self.graph.contours is None or self.graph.contours.mode != 'terminate' or not self.graph.boundary_terminal(n)]
                self._failures = {n.id: 0 for n in self._frontier}
                if self._frontier or self._can_reseed():
                    self.status = GrowthStatus.RUNNING
                    self.node_stop = None
                    self.loop_stop = None
                    self._loop_phase = False
            if self.status == GrowthStatus.TARGET_REACHED and len(self.graph.nodes) < self.graph.target_nodes: self.status = GrowthStatus.CLEANED_UNDERFILLED
        if self.done and self.graph.contours is not None and self.graph.contours.strict_terminals and not self.graph.contour_report().strict_satisfied:
            self.status = GrowthStatus.CONSTRAINT_UNMET
        self.graph.built = self.done

    def _cleanup(self) -> tuple[str, ...]:
        removed = self.graph._remove_isolated_nodes() if self.settings.remove_isolated_nodes else ()
        self._step_removed.extend(removed)
        self.removed_nodes += len(removed)
        keys = set(removed)
        self._frontier = [node for node in self._frontier if node.id not in keys]
        for key in removed: self._failures.pop(key, None)
        if self.coverage is not None:
            for tile in self.coverage.tiles: tile.actual = 0
            for node in self.graph.nodes: self.coverage.accept(node)
        return removed

    def _accepts_edge(self, edge: Edge) -> bool:
        angle = self.graph.candidate_angle(edge)
        if angle+1e-9 < self.graph.angles.minimum:
            self.hard_rejections += 1
            return False
        if not self.graph.can_place_edge(edge): return False
        probability = self.graph.angles.acceptance(angle)
        if probability < 1 and self.rng.random() >= probability:
            self.soft_rejections += 1
            return False
        return True

    def quality_report(self) -> QualityReport:
        angles: list[float] = []
        network = self.graph.to_networkx()
        for node in self.graph.nodes:
            angles.extend(incident_angle(node, self.graph._node_by_id[a], self.graph._node_by_id[b]) for a, b in combinations(network.neighbors(node.id), 2))
        histogram = [0]*6
        for angle in angles: histogram[min(5, int(angle/30))] += 1
        return QualityReport(self.removed_nodes, self.refill_passes, self.refill_attempts, self.refill_additions, self.hard_rejections, self.soft_rejections,
                             min(angles) if angles else None, tuple(histogram), len(self.graph.nodes), max(0, self.graph.target_nodes-len(self.graph.nodes)))

    def _try_loop(self) -> None:
        self.loop_attempts += 1
        graph = self.graph
        first = self.rng.choice(graph._nodes)
        radius = self.settings.loop_distance
        x, y = first.center.x, first.center.y
        candidates = [graph._objects[key] for key in graph._index.query((x-radius, y-radius, x+radius, y+radius))]
        nearby = [n for n in candidates if isinstance(n, Node) and n is not first and first.distance_to(n) <= radius]
        if not nearby: return
        second = self.rng.choice(nearby)
        if graph.nx_graph.has_edge(first.id, second.id) or graph.nx_graph.has_edge(second.id, first.id): return
        if max(graph.nx_graph.degree(first.id), graph.nx_graph.degree(second.id)) >= self.settings.max_degree: return
        if graph.colonies is not None and first.colony_id != second.colony_id:
            rule = graph.colonies.rule(first.colony_id, second.colony_id)
            if rule is None or not rule.allow_join: return
        # Cycles and component-joining bridges have separate budgets and events.
        if not nx.has_path(graph.nx_graph.to_undirected(as_view=True), first.id, second.id): return
        edge = graph._new_edge(first, second)
        length_scale = (graph.fields.scale(graph.fields.length, first.center.x, first.center.y)+graph.fields.scale(graph.fields.length, second.center.x, second.center.y))/2
        maximum_length = graph.edge_length_max*length_scale*graph.extra_edge_elongation_factor
        if edge is not None and edge.length <= maximum_length and self._accepts_edge(edge):
            graph._accept_loop(edge)
            self.loops_added += 1
            self._step_loops.append(edge)

    def _result(self, additions: list[Addition], attempts: int) -> StepResult:
        completion = None
        if self.done and not self._reported:
            completion = Completion(self.status, self.attempts, len(self.graph._nodes))
            self._reported = True
            if self.graph._event_listener is not None: self.graph._event_listener('complete', ())
        return StepResult(tuple(additions), attempts, self.attempts, len(self._frontier), self.status, completion, tuple(self._step_loops), tuple(self._step_removed), tuple(self._step_joins))

    def cancel(self) -> StepResult:
        self._check_owner()
        self._step_loops = []
        self._step_joins = []
        self._step_removed = []
        if not self.done:
            self._cleanup()
            self.status = GrowthStatus.CANCELLED
            if self._loop_phase: self.loop_stop = 'cancelled'
            self.graph.built = True
        return self._result([], 0)

    def step(self, max_attempts: int = 100) -> StepResult:
        self._check_owner()
        if type(max_attempts) is not int or max_attempts <= 0: raise ValueError('Step budget must be a positive integer')
        self._step_loops = []
        self._step_joins = []
        self._step_removed = []
        additions: list[Addition] = []
        used = 0
        if not self.done: self._finish_if_needed()
        while not self.done and used < max_attempts:
            used += 1
            self.attempts += 1
            if self.refill_passes: self.refill_attempts += 1
            if self._loop_phase:
                if self._bridges_pending(): self._try_bridge()
                else: self._try_loop()
                self._finish_if_needed()
                continue
            periodic_seed = self.coverage is not None and self.coverage.settings.reseed_interval > 0 and self.attempts % self.coverage.settings.reseed_interval == 0
            if not self._seeding and (not self._frontier or periodic_seed) and not self.graph.boundary_seed_needed() and self._can_reseed():
                self.reseed_attempts += 1
                node = self.coverage.seed(self.rng, fill_area=self.settings.fill_area) if self.coverage is not None else None
                if node is not None:
                    self.graph._accept(node)
                    if self.refill_passes: self.refill_additions += 1
                    self._frontier.append(node)
                    self._failures[node.id] = 0
                    self.reseeds += 1
                    additions.append(Addition(node, None, node.colony_id))
                self._finish_if_needed()
                continue
            boundary_seed = not self._seeding and self.graph.boundary_seed_needed() and (not self._frontier or self.rng.random() < 0.25)
            if self._seeding or boundary_seed:
                node = self.coverage.seed(self.rng, fill_area=self.settings.fill_area) if self.coverage is not None and self.coverage.settings.seed_components and not boundary_seed and self.graph.colonies is None else self.graph.find_seed_node(attempts=1, boundary_only=boundary_seed)
                if node is None:
                    self._seed_failures += 1
                    if self._seed_failures >= self.settings.seed_attempts: self._seeding = False
                else:
                    self.graph._accept(node)
                    if self.refill_passes: self.refill_additions += 1
                    self._frontier.append(node)
                    self._failures[node.id] = 0
                    additions.append(Addition(node, None, node.colony_id))
                    self._seed_failures = 0
                    self._seeding = len(self.graph._nodes) < min(self.graph.target_seed_nodes, self.graph.target_nodes)
            else:
                index = self._select_parent()
                if type(index) is not int or not 0 <= index < len(self._frontier): raise ValueError('Policy returned an invalid frontier index')
                parent = self._frontier[index]
                if parent.colony_id is not None: self._colony_attempts[parent.colony_id] = self._colony_attempts.get(parent.colony_id, 0)+1
                _, node = self.graph.find_node_candidate(parent)
                edge = self.graph._new_edge(parent, node)
                if self.graph.nx_graph.degree(parent.id) < self.settings.max_degree and edge is not None and self.graph.can_place_node(node) and self._accepts_edge(edge):
                    self.graph._accept(node, edge)
                    if parent.colony_id is not None: self._colony_accepted[parent.colony_id] = self._colony_accepted.get(parent.colony_id, 0)+1
                    if self.refill_passes: self.refill_additions += 1
                    if self.graph.contours is None or self.graph.contours.mode != 'terminate' or not self.graph.boundary_terminal(node):
                        self._frontier.append(node)
                        self._failures[node.id] = 0
                    additions.append(Addition(node, edge, node.colony_id))
                else:
                    self._failures[parent.id] += 1
                    if self._failures[parent.id] >= self.settings.failures_per_parent:
                        self.graph._terminal_reasons[parent.id] = 'parent_attempt_budget_exhausted'
                        self._frontier[index] = self._frontier[-1]
                        self._frontier.pop()
                        del self._failures[parent.id]
            self._finish_if_needed()
        return self._result(additions, used)
