"""Cached replay rendering, PNG sequences, and bounded live generation."""
from __future__ import annotations
from math import ceil, isfinite
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, Literal
from shapely.geometry import Polygon, MultiPolygon, shape
from .colors import rgb_normalized
from .rendering import draw_node, draw_edge
from .replay import EventLog, EventRecorder, Playback, ReplayState
from .growth import StepResult
if TYPE_CHECKING:
    import cairo
    from .graph import Graph


class ReplayRenderer:
    """Cache completed edge/node paths separately, preserving static draw order."""
    def __init__(self, playback: Playback, *, margin: float = 5, scale: float = 1, background: str | None = None,
                 frame: Literal['region', 'artwork'] = 'region') -> None:
        try:
            import cairo
        except ImportError as error:
            raise ImportError('Install graph-ics[render] to render animation') from error
        if not isfinite(margin) or margin < 0 or not isfinite(scale) or scale <= 0: raise ValueError('Require finite margin >= 0 and scale > 0')
        if frame not in ('region', 'artwork'): raise ValueError('Unknown animation frame')
        if scale < playback.log.scene.minimum_scale: raise ValueError('Animation scale is below the contour readability scale')
        if background is not None: rgb_normalized(background)
        self.playback, self.margin, self.scale, self.background, self.frame = playback, margin, scale, background, frame
        region = shape(playback.log.scene.region)
        if not isinstance(region, (Polygon, MultiPolygon)): raise ValueError('Replay region must be polygonal')
        self.region: Polygon | MultiPolygon = region
        final = playback.log.validate()
        bounds = [node.bounds for node in final.nodes.values()]+[edge.footprint.bounds for edge in final.edges]+[text.bounds for text in playback.log.scene.texts]
        if frame == 'region': bounds.append(self.region.bounds)
        if playback.log.scene.border: bounds.append(self.region.buffer(float(playback.log.scene.configuration.get('border_width', 0.5))/2).bounds)
        if not bounds: raise ValueError('Cannot frame empty artwork')
        self.bounds = min(b[0] for b in bounds), min(b[1] for b in bounds), max(b[2] for b in bounds), max(b[3] for b in bounds)
        self.width = max(1, ceil((self.bounds[2]-self.bounds[0]+2*margin)*scale))
        self.height = max(1, ceil((self.bounds[3]-self.bounds[1]+2*margin)*scale))
        self.cached_events = 0
        self.cache_rebuilds = 0
        self._reset_cache()
        self.overlay = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, None)
        context = cairo.Context(self.overlay)
        self._draw_overlay(context)

    def _draw_overlay(self, context: cairo.Context[cairo.RecordingSurface] | cairo.Context[cairo.ImageSurface]) -> None:
        import cairo
        if self.playback.log.scene.border:
            context.set_source_rgba(*rgb_normalized(self.playback.log.scene.configuration.get('border_color', '#a6a6a6')), 1)
            context.set_line_width(self.playback.log.scene.configuration.get('border_width', 0.5))
            context.set_line_join(cairo.LINE_JOIN_ROUND)
            polygons = [self.region] if isinstance(self.region, Polygon) else self.region.geoms
            for polygon in polygons:
                for ring in [polygon.exterior, *polygon.interiors]:
                    for i, (x, y) in enumerate(ring.coords):
                        if i == 0: context.move_to(x, y)
                        else: context.line_to(x, y)
                    context.close_path()
            context.stroke()
        for text in self.playback.log.scene.texts:
            context.new_path()
            for kind, points in text.path:
                if kind == 0: context.move_to(*points)
                elif kind == 1: context.line_to(*points)
                elif kind == 2: context.curve_to(*points)
                elif kind == 3: context.close_path()
                else: raise ValueError('Unknown text path command')
            context.set_source_rgba(*rgb_normalized(text.color), text.opacity)
            context.fill()

    def _reset_cache(self) -> None:
        import cairo
        self.state = ReplayState()
        self.edge_cache = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, None)
        self.node_cache = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, None)
        self.cached_events = 0
        self.cache_rebuilds += 1

    def update(self, log: EventLog) -> None:
        """Append a live recording without changing its clock or fixed viewport."""
        if self.frame != 'region': raise ValueError('Live updates require a fixed region frame')
        old = self.playback.log
        if log.scene != old.scene or log.events[:len(old.events)] != old.events: raise ValueError('Live replay updates must extend the same log')
        replacement = Playback(log, seconds_per_event=self.playback.seconds_per_event, speed=self.playback.speed)
        replacement.seek(self.playback.position)
        replacement.paused = self.playback.paused
        self.playback = replacement

    def _sync(self, index: int) -> None:
        import cairo
        if index < self.cached_events: self._reset_cache()
        for event in self.playback.events[self.cached_events:index]:
            self.state.apply(event)
            if event.kind in ('branch', 'loop', 'join'): draw_edge(self.state.edges[-1], cairo.Context(self.edge_cache))
            if event.node is not None: draw_node(self.state.nodes[event.node.id], cairo.Context(self.node_cache))
            if event.kind == 'remove':
                self.node_cache = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, None)
                context = cairo.Context(self.node_cache)
                for node in self.state.nodes.values(): draw_node(node, context)
        self.cached_events = index

    def render(self, seconds: float | None = None) -> cairo.ImageSurface:
        import cairo
        if seconds is not None: self.playback.seek(seconds)
        index, progress = self.playback.cursor()
        self._sync(index)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        context = cairo.Context(surface)
        if self.background is not None:
            context.set_source_rgb(*rgb_normalized(self.background))
            context.paint()
        context.scale(self.scale, self.scale)
        context.translate(self.margin-self.bounds[0], self.margin-self.bounds[1])
        if index == len(self.playback.events):
            # Render the completed scene directly to avoid extra compositing-rounding in the caches.
            for edge in self.state.edges: draw_edge(edge, context)
            for node in self.state.nodes.values(): draw_node(node, context)
            self._draw_overlay(context)
            surface.flush()
            return surface
        context.set_source_surface(self.edge_cache)
        context.paint()
        event = self.playback.events[index] if index < len(self.playback.events) else None
        if event is not None and event.edge is not None and progress > 0:
            nodes = dict(self.state.nodes)
            if event.node is not None: nodes[event.node.id] = event.node.restore()
            edge = event.edge.restore(nodes)
            fraction = min(1, progress/0.75) if event.kind == 'branch' else progress
            # Reveal the actual styled edge through a growing rectangular clip.
            # Drawing a temporary solid segment would lose dash/dot/double styling.
            context.save()
            x, y = edge.start_point.x, edge.start_point.y
            dx, dy = -edge.nx, -edge.ny
            end_x, end_y = x+dx*edge.length*fraction, y+dy*edge.length*fraction
            half = edge.thickness/2+1
            context.new_path()
            context.move_to(x-dy*half, y+dx*half)
            context.line_to(end_x-dy*half, end_y+dx*half)
            context.line_to(end_x+dy*half, end_y-dx*half)
            context.line_to(x+dy*half, y-dx*half)
            context.close_path()
            context.clip()
            draw_edge(edge, context)
            context.restore()
        context.set_source_surface(self.node_cache)
        context.paint()
        if event is not None and event.node is not None:
            opacity = max(0, (progress-0.75)/0.25) if event.kind == 'branch' else progress
            if opacity > 0:
                node = event.node.restore()
                node.opacity *= opacity
                draw_node(node, context)
        context.set_source_surface(self.overlay)
        context.paint()
        surface.flush()
        return surface

    def export_gif(self, path: str | Path, *, fps: float = 20, max_frames: int = 500, max_pixels: int = 100_000_000) -> Path:
        """Export an opaque looping GIF; reject excessive frame storage before rendering."""
        from io import BytesIO
        from PIL import Image
        if not isfinite(fps) or not 0 < fps <= 100 or type(max_frames) is not int or max_frames < 1: raise ValueError('GIF requires 0 < fps <= 100 and a positive frame cap')
        count = ceil(self.playback.duration*fps)+1
        if count > max_frames or count*self.width*self.height > max_pixels: raise ValueError('GIF exceeds frame/pixel budget; reduce scale, fps or event duration')
        destination = Path(path)
        if destination.suffix.lower() != '.gif': raise ValueError('GIF output must end in .gif')
        if destination.exists(): raise FileExistsError(destination)
        if self.background is None: raise ValueError('GIF requires an opaque background; use PNG frames for alpha')
        frames: list[Image.Image] = []
        position = self.playback.position
        try:
            for index in range(count):
                stream = BytesIO()
                self.render(min(index/fps, self.playback.duration)).write_to_png(stream)
                stream.seek(0)
                with Image.open(stream) as image: frames.append(image.convert('RGB'))
            destination.parent.mkdir(parents=True, exist_ok=True)
            frames[0].save(destination, save_all=True, append_images=frames[1:], duration=[max(10, round(100/fps)*10)]*(count-1)+[1500], loop=0)
        finally:
            self.playback.seek(position)
            for frame in frames: frame.close()
        return destination

    def export_sequence(self, directory: str | Path, *, fps: float = 24, max_frames: int = 10000) -> tuple[Path, ...]:
        if not isfinite(fps) or fps <= 0 or type(max_frames) is not int or max_frames < 1: raise ValueError('Require positive fps and frame limit')
        count = ceil(self.playback.duration*fps)+1
        if count > max_frames: raise ValueError('Sequence exceeds frame limit; reduce fps or event duration')
        output = Path(directory)
        paths = tuple(output/f'frame_{index:06d}.png' for index in range(count))
        if any(path.exists() for path in paths): raise FileExistsError('Frame sequence destination already contains output frames')
        output.mkdir(parents=True, exist_ok=True)
        position = self.playback.position
        try:
            for index, path in enumerate(paths): self.render(min(index/fps, self.playback.duration)).write_to_png(str(path))
        finally:
            self.playback.seek(position)
        return paths


class LiveGrowth:
    """Pause/resume generation in this process; optional recording is independent."""
    def __init__(self, graph: Graph, *, record: bool = True, path: str | Path | None = None, retain: bool = True) -> None:
        if not record and path is not None: raise ValueError('A recording destination requires recording')
        self.graph = graph
        self.generator = graph.growth()
        self.recorder = EventRecorder(graph, path=path, retain=retain) if record else None
        self.paused = False

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def tick(self, max_attempts: int = 100, *, time_budget_ms: float | None = None) -> tuple[StepResult, ...]:
        if type(max_attempts) is not int or max_attempts <= 0: raise ValueError('Attempt budget must be a positive integer')
        if time_budget_ms is not None and (not isfinite(time_budget_ms) or time_budget_ms < 0): raise ValueError('Time budget must be finite and nonnegative')
        if self.paused or self.generator.done: return ()
        if time_budget_ms is None: return (self.generator.step(max_attempts),)
        deadline = perf_counter()+time_budget_ms/1000
        results: list[StepResult] = []
        used = 0
        while not self.generator.done and used < max_attempts and perf_counter() < deadline:
            result = self.generator.step(1)
            results.append(result)
            used += result.attempts
        return tuple(results)

    def close(self) -> None:
        if self.recorder is not None: self.recorder.close()
