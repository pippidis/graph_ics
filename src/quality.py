"""Angular quality controls measured between outward center-to-center rays."""
from dataclasses import dataclass
from math import atan2, degrees, isfinite
from .node import Node


@dataclass(frozen=True)
class AngleSettings:
    minimum: float = 0
    preferred: float = 0
    penalty: float = 0

    def __post_init__(self) -> None:
        if not all(isfinite(v) for v in (self.minimum, self.preferred, self.penalty)): raise ValueError('Angle settings must be finite')
        if not 0 <= self.minimum <= 180 or not 0 <= self.preferred <= 180: raise ValueError('Angles must be between 0 and 180 degrees')
        if self.preferred and self.preferred < self.minimum: raise ValueError('Preferred angle must be at least the hard minimum')
        if not 0 <= self.penalty <= 1: raise ValueError('Penalty must be between 0 and 1')

    def acceptance(self, angle: float) -> float:
        if angle+1e-9 < self.minimum: return 0
        if self.preferred <= self.minimum or angle >= self.preferred: return 1
        return 1-self.penalty*(self.preferred-angle)/(self.preferred-self.minimum)


def incident_angle(center: Node, first: Node, second: Node) -> float:
    ax, ay = first.center.x-center.center.x, first.center.y-center.center.y
    bx, by = second.center.x-center.center.x, second.center.y-center.center.y
    return degrees(atan2(abs(ax*by-ay*bx), ax*bx+ay*by))


@dataclass(frozen=True)
class QualityReport:
    removed_nodes: int
    refill_passes: int
    refill_attempts: int
    refill_additions: int
    hard_rejections: int
    soft_rejections: int
    minimum_angle: float | None
    angle_histogram: tuple[int, ...]  # Six 30-degree bins, last includes 180.
    achieved_nodes: int
    target_shortfall: int
