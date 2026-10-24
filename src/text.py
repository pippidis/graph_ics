"""Baseline-positioned text measured as reusable Cairo paths, without temporary files."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from typing import TYPE_CHECKING, Literal
from shapely.geometry import Polygon, MultiPolygon, box
from shapely.geometry.base import BaseGeometry
from .colors import hex2rgb
if TYPE_CHECKING:
    import cairo


@dataclass(frozen=True)
class Text:
    content: str
    x: float
    y: float  # Baseline in the same downward-positive world coordinates as graph geometry.
    size: float = 32
    font: str = 'sans-serif'
    padding: float = 8
    color: str = '#e04e3b'
    opacity: float = 1
    align: Literal['left', 'center', 'right'] = 'left'
    bold: bool = False
    italic: bool = False
    padding_em: float = 0  # Additional exclusion padding as a fraction of font size.
    exclusion_mode: Literal['box', 'glyph'] = 'box'

    def __post_init__(self) -> None:
        if not self.content.strip() or any(ord(char) < 32 or ord(char) == 127 for char in self.content): raise ValueError('Text must contain visible single-line content without control characters')
        if not self.font.strip(): raise ValueError('Font family must not be empty')
        if not all(isfinite(value) for value in (self.x, self.y, self.size, self.padding, self.opacity, self.padding_em)): raise ValueError('Text dimensions must be finite')
        if self.size <= 0 or self.padding < 0 or self.padding_em < 0 or not 0 <= self.opacity <= 1: raise ValueError('Require positive text size, nonnegative padding, and opacity in [0, 1]')
        if not isfinite(self.effective_padding): raise ValueError('Combined text padding must be finite')
        if self.align not in ('left', 'center', 'right'): raise ValueError('Unknown text alignment')
        if type(self.bold) is not bool or type(self.italic) is not bool: raise ValueError('Font style flags must be boolean')
        if self.exclusion_mode not in ('box', 'glyph'): raise ValueError('Unknown text exclusion mode')
        hex2rgb(self.color)

    @property
    def effective_padding(self) -> float:
        return self.padding+self.padding_em*self.size

    def measure(self) -> MeasuredText:
        try:
            import cairo
        except ImportError as error:
            raise ImportError('Install graph-ics[render] to measure text') from error
        surface = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, None)
        try:
            context = cairo.Context(surface)
            options = cairo.FontOptions()
            options.set_hint_metrics(cairo.HINT_METRICS_OFF)
            options.set_hint_style(cairo.HINT_STYLE_NONE)
            context.set_font_options(options)
            context.select_font_face(self.font, cairo.FONT_SLANT_ITALIC if self.italic else cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if self.bold else cairo.FONT_WEIGHT_NORMAL)
            context.set_font_size(self.size)
            advance = context.text_extents(self.content).x_advance
            baseline_x = self.x-advance*({'left': 0, 'center': 0.5, 'right': 1}[self.align])
            context.move_to(baseline_x, self.y)
            context.text_path(self.content)
            bounds = context.path_extents()
            if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]: raise ValueError('Text has no measurable ink')
            return MeasuredText(self, bounds, advance, baseline_x, context.copy_path())
        finally:
            surface.finish()


@dataclass(frozen=True)
class MeasuredText:
    text: Text
    bounds: tuple[float, float, float, float]
    advance: float
    baseline_x: float
    path: cairo.Path

    @property
    def glyph_region(self) -> Polygon | MultiPolygon:
        """Flatten font outlines to 0.05 world units, preserving counters (letter holes)."""
        import cairo
        surface = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, None)
        context = cairo.Context(surface)
        context.set_tolerance(0.05)
        context.append_path(self.path)
        rings: list[Polygon] = []
        points: list[tuple[float, float]] = []
        for kind, coordinates in context.copy_path_flat():
            if kind == cairo.PATH_MOVE_TO:
                if len(points) >= 3:
                    ring = Polygon(points)
                    if ring.area: rings.append(ring)
                points = [(coordinates[0], coordinates[1])]
            elif kind == cairo.PATH_LINE_TO:
                points.append((coordinates[0], coordinates[1]))
            elif kind == cairo.PATH_CLOSE_PATH and len(points) >= 3:
                ring = Polygon(points)
                if ring.area: rings.append(ring)
                points = []
        if len(points) >= 3:
            ring = Polygon(points)
            if ring.area: rings.append(ring)
        result: BaseGeometry = Polygon()
        for ring in rings: result = result.symmetric_difference(ring)
        surface.finish()
        if not isinstance(result, (Polygon, MultiPolygon)) or result.is_empty or not result.is_valid: raise ValueError('Font did not produce valid polygonal glyphs')
        return result

    @property
    def exclusion(self) -> Polygon | MultiPolygon:
        if self.text.exclusion_mode == 'glyph': return self.glyph_region.buffer(self.text.effective_padding+0.05)

        x0, y0, x1, y1 = self.bounds
        padding = self.text.effective_padding
        return box(x0-padding, y0-padding, x1+padding, y1+padding)
