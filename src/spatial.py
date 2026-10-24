"""Conservative spatial broad phase; exact geometry remains authoritative."""

from dataclasses import dataclass
from math import floor, isfinite
from typing import Protocol

Bounds = tuple[float, float, float, float]


def validate_bounds(bounds: Bounds) -> None:
    if not all(isfinite(v) for v in bounds) or bounds[0] > bounds[2] or bounds[1] > bounds[3]:
        raise ValueError('Bounds must be finite and ordered')


def intersects(a: Bounds, b: Bounds) -> bool:
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


class SpatialIndex(Protocol):
    def insert(self, key: int, bounds: Bounds) -> None: ...
    def query(self, bounds: Bounds) -> tuple[int, ...]: ...


class BruteForceIndex:
    """Reference implementation: all inserted objects, in acceptance order."""
    def __init__(self) -> None:
        self.bounds: dict[int, Bounds] = {}

    def insert(self, key: int, bounds: Bounds) -> None:
        validate_bounds(bounds)
        if key in self.bounds: raise ValueError('Index keys must be unique')
        self.bounds[key] = bounds

    def query(self, bounds: Bounds) -> tuple[int, ...]:
        validate_bounds(bounds)
        return tuple(sorted(self.bounds))


class SpatialHash(BruteForceIndex):
    """Every touched cell is indexed, including boundaries and negative coordinates.

    Oversized envelopes use a conservative overflow list rather than allocating
    unbounded cells. Oversized queries fall back to a scan. Results are sorted,
    deduplicated keys, independent of dictionary/set iteration order.
    """
    def __init__(self, cell_size: float, max_cells: int = 4096) -> None:
        super().__init__()
        if not isfinite(cell_size) or cell_size <= 0: raise ValueError('Cell size must be finite and positive')
        if type(max_cells) is not int or max_cells <= 0: raise ValueError('Cell limit must be a positive integer')
        self.cell_size, self.max_cells = cell_size, max_cells
        self.cells: dict[tuple[int, int], list[int]] = {}
        self.overflow: list[int] = []

    def _cells(self, bounds: Bounds) -> list[tuple[int, int]] | None:
        scaled = tuple(v/self.cell_size for v in bounds)
        if not all(isfinite(v) for v in scaled): return None
        x0, y0, x1, y1 = (floor(v) for v in scaled)
        if (x1-x0+1)*(y1-y0+1) > self.max_cells: return None
        return [(x, y) for x in range(x0, x1+1) for y in range(y0, y1+1)]

    def insert(self, key: int, bounds: Bounds) -> None:
        super().insert(key, bounds)
        cells = self._cells(bounds)
        if cells is None:
            self.overflow.append(key)
        else:
            for cell in cells: self.cells.setdefault(cell, []).append(key)

    def query(self, bounds: Bounds) -> tuple[int, ...]:
        validate_bounds(bounds)
        cells = self._cells(bounds)
        keys = set(self.bounds) if cells is None else set(self.overflow)
        if cells is not None:
            for cell in cells: keys.update(self.cells.get(cell, ()))
        return tuple(key for key in sorted(keys) if intersects(bounds, self.bounds[key]))


@dataclass
class CollisionStats:
    queries: int = 0
    queried_objects: int = 0
    exact_checks: int = 0
    outer_boundary: int = 0
    inner_exclusion: int = 0
    node_clearance: int = 0
    edge_clearance: int = 0
