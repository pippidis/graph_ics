"""Small vector helper retaining the historical p1-minus-p2 convention."""

from math import isfinite
from shapely.geometry import Point


class Vector:
    def __init__(self, p1: Point, p2: Point) -> None:
        if p1.is_empty or p2.is_empty or not all(isfinite(v) for v in (p1.x, p1.y, p2.x, p2.y)): raise ValueError('Vector endpoints must be finite points')
        if p1 == p2: raise ValueError('Cannot normalize a zero vector')
        self.p1, self.p2 = p1, p2
        self.x, self.y = p1.x-p2.x, p1.y-p2.y

    def get_length(self) -> float:
        return float(self.p1.distance(self.p2))

    def get_normalized(self) -> tuple[float, float]:
        return self.x/self.length, self.y/self.length

    def __repr__(self) -> str:
        return f'[{self.x},{self.y}]'

    def __str__(self) -> str:
        return f'Vector: [{self.x},{self.y}] from {self.p1} to {self.p2}'

    @property
    def length(self) -> float:
        return self.get_length()
