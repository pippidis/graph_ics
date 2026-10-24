"""Spatial colour ramps sampled independently of geometry density."""
from dataclasses import dataclass
from typing import Protocol
from math import isfinite
from .fields import ScalarField
from .colors import hex2rgb


class ColorField(Protocol):
    def sample(self, x: float, y: float) -> str: ...


@dataclass(frozen=True)
class ColorRamp:
    field: ScalarField
    colors: tuple[str, ...] = ('#284d68', '#eead64', '#a64152')

    def __post_init__(self) -> None:
        if len(self.colors) < 2: raise ValueError('Colour ramps need at least two stops')
        for color in self.colors: hex2rgb(color)

    def sample(self, x: float, y: float) -> str:
        value = self.field.sample(x, y)
        if not isfinite(value): raise ValueError('Colour field must return finite values')
        position = min(1, max(0, value))*(len(self.colors)-1)
        index = min(len(self.colors)-2, int(position))
        fraction = position-index
        left, right = hex2rgb(self.colors[index]), hex2rgb(self.colors[index+1])
        return '#'+''.join(f'{round(a+(b-a)*fraction):02x}' for a,b in zip(left,right))
