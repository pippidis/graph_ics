"""World-coordinate scalar fields and bounded spatial style controls."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import floor, isfinite, sqrt
from pathlib import Path
from typing import Literal, Protocol
import sys

from .spatial import Bounds, validate_bounds


class ScalarField(Protocol):
    def sample(self, x: float, y: float) -> float: ...


@dataclass(frozen=True)
class ConstantField:
    value: float

    def __post_init__(self) -> None:
        if not isfinite(self.value): raise ValueError('Field value must be finite')

    def sample(self, x: float, y: float) -> float:
        return self.value


@dataclass(frozen=True)
class CallableField:
    function: Callable[[float, float], float]

    def sample(self, x: float, y: float) -> float:
        value = self.function(x, y)
        if not isfinite(value): raise ValueError('Field returned a nonfinite value')
        return value


@dataclass(frozen=True)
class ImageField:
    """Bilinear scalar raster; row zero maps to min_y (screen-down coordinates).

    Pixel centers at the first/last row and column map to the world bounds.
    Values may be any finite scalars. PNG loading maps a selected channel from
    [0,1] to value_range; RGB is unpremultiplied, transparent RGB becomes zero.
    """
    pixels: tuple[tuple[float, ...], ...]
    bounds: Bounds
    outside: Literal['clamp', 'constant', 'error'] = 'clamp'
    outside_value: float = 0.0

    def __post_init__(self) -> None:
        validate_bounds(self.bounds)
        if self.bounds[0] == self.bounds[2] or self.bounds[1] == self.bounds[3]: raise ValueError('Image world bounds need positive area')
        if not self.pixels or not self.pixels[0] or any(len(row) != len(self.pixels[0]) for row in self.pixels): raise ValueError('Raster must be rectangular and nonempty')
        if not all(isfinite(v) for row in self.pixels for v in row) or not isfinite(self.outside_value): raise ValueError('Raster values must be finite')
        if self.outside not in ('clamp', 'constant', 'error'): raise ValueError('Invalid out-of-range policy')

    def sample(self, x: float, y: float) -> float:
        if not isfinite(x) or not isfinite(y): raise ValueError('Sample coordinates must be finite')
        x0, y0, x1, y1 = self.bounds
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            if self.outside == 'error': raise ValueError('Sample lies outside image bounds')
            if self.outside == 'constant': return self.outside_value
        u = min(1, max(0, (x-x0)/(x1-x0)))*(len(self.pixels[0])-1)
        v = min(1, max(0, (y-y0)/(y1-y0)))*(len(self.pixels)-1)
        i, j = floor(u), floor(v)
        k, next_row = min(i+1, len(self.pixels[0])-1), min(j+1, len(self.pixels)-1)
        a = self.pixels[j][i]*(1-(u-i))+self.pixels[j][k]*(u-i)
        b = self.pixels[next_row][i]*(1-(u-i))+self.pixels[next_row][k]*(u-i)
        return a*(1-(v-j))+b*(v-j)

    @classmethod
    def from_png(cls, path: str | Path, bounds: Bounds, *, channel: Literal['red', 'green', 'blue', 'alpha', 'luminance'] = 'luminance',
                 value_range: tuple[float, float] = (0, 1), outside: Literal['clamp', 'constant', 'error'] = 'clamp', outside_value: float = 0) -> ImageField:
        import cairo
        if channel not in ('red', 'green', 'blue', 'alpha', 'luminance'): raise ValueError('Unknown image channel')
        if not all(isfinite(v) for v in value_range): raise ValueError('Image range must be finite')
        image = cairo.ImageSurface.create_from_png(str(path))
        image.flush()
        data, stride = image.get_data(), image.get_stride()
        rows: list[tuple[float, ...]] = []
        for y in range(image.get_height()):
            row: list[float] = []
            for x in range(image.get_width()):
                offset = y*stride+x*4
                pixel = int.from_bytes(data[offset:offset+4], sys.byteorder)
                alpha = 255 if image.get_format() == cairo.FORMAT_RGB24 else (pixel >> 24) & 255
                r, g, b = (((pixel >> shift) & 255)/alpha if alpha else 0.0 for shift in (16, 8, 0))
                value = {'red': r, 'green': g, 'blue': b, 'alpha': alpha/255, 'luminance': 0.2126*r+0.7152*g+0.0722*b}[channel]
                row.append(value_range[0]+value*(value_range[1]-value_range[0]))
            rows.append(tuple(row))
        return cls(tuple(rows), bounds, outside, outside_value)


def positive_sample(field: ScalarField | None, x: float, y: float, default: float = 1) -> float:
    value = default if field is None else field.sample(x, y)
    if not isfinite(value) or value <= 0: raise ValueError('Style and density fields must return positive finite values')
    return value


@dataclass(frozen=True)
class SpatialFields:
    """Scale multipliers are independent; density is nodes per square world unit.

    coordinated_scale links radius, buffer, gap, length, and thickness. Density
    derives preferred center spacing as 1/sqrt(density), not an exact count.
    """
    radius: ScalarField | None = None
    length: ScalarField | None = None
    thickness: ScalarField | None = None
    density: ScalarField | None = None
    coordinated_scale: ScalarField | None = None
    scale_limits: tuple[float, float] = (0.1, 10)
    spacing_limits: tuple[float, float] = (0.1, 10000)
    ring_ratio: float | None = None
    refinement_steps: int = 6

    def __post_init__(self) -> None:
        for low, high in (self.scale_limits, self.spacing_limits):
            if not isfinite(low) or not isfinite(high) or not 0 < low <= high: raise ValueError('Require positive finite ordered limits')
        if self.ring_ratio is not None and (not isfinite(self.ring_ratio) or not 0 <= self.ring_ratio < 1): raise ValueError('Ring ratio must be in [0,1)')
        if type(self.refinement_steps) is not int or not 1 <= self.refinement_steps <= 32: raise ValueError('Refinement steps must be between 1 and 32')

    def scale(self, field: ScalarField | None, x: float, y: float) -> float:
        value = positive_sample(field, x, y)*positive_sample(self.coordinated_scale, x, y)
        if not isfinite(value): raise ValueError('Combined scale overflowed')
        return min(self.scale_limits[1], max(self.scale_limits[0], value))

    def spacing(self, x: float, y: float) -> float:
        if self.density is None: return 0
        value = 1/sqrt(positive_sample(self.density, x, y))
        return min(self.spacing_limits[1], max(self.spacing_limits[0], value))
