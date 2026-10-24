"""Declarative, versioned JSON/YAML scenes; all file references resolve beside the scene."""
from __future__ import annotations
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any, cast
import json
from math import exp, isfinite
from shapely.geometry import Polygon, MultiPolygon, box, shape
from shapely.errors import ShapelyError
from .graph import Graph
from .styles import GraphStyle
from .text import Text
from .fields import ScalarField, ConstantField, CallableField, ImageField, SpatialFields
from .color_fields import ColorRamp
from .growth import GrowthSettings
from .coverage import CoverageSettings
from .contours import ContourSettings
from .quality import AngleSettings


def mapping(value: Any, allowed: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value): raise ValueError(f'{name} must be an object')
    unknown = value.keys()-allowed
    if unknown: raise ValueError(f'Unknown {name} keys: {", ".join(sorted(unknown))}')
    return dict(cast(dict[str, Any], value))


def scalar_field(spec: Any, bounds: tuple[float, float, float, float]) -> ScalarField:
    if isinstance(spec, (int, float)) and not isinstance(spec, bool): return ConstantField(spec)
    data = mapping(spec, {'kind', 'min', 'max', 'axis', 'pixels', 'bounds', 'center', 'sigma'}, 'field')
    kind = data.get('kind', 'gradient')
    low, high = float(data.get('min', 0)), float(data.get('max', 1))
    if not isfinite(low) or not isfinite(high): raise ValueError('Field endpoints must be finite')
    x0,y0,x1,y1 = bounds
    if kind == 'raster': return ImageField(tuple(tuple(float(v) for v in row) for row in data['pixels']), tuple(data.get('bounds', bounds)))
    if kind == 'gradient':
        axis = data.get('axis', 'x')
        if axis not in ('x','y'): raise ValueError('Gradient axis must be x or y')
        return CallableField(lambda x,y: low+(high-low)*min(1,max(0,(x-x0)/(x1-x0) if axis=='x' else (y-y0)/(y1-y0))))
    if kind == 'radial':
        cx,cy = data.get('center', ((x0+x1)/2,(y0+y1)/2))
        sigma = float(data.get('sigma', min(x1-x0,y1-y0)/4))
        if not isfinite(sigma) or sigma <= 0: raise ValueError('Radial sigma must be positive')
        return CallableField(lambda x,y: low+(high-low)*exp(-((x-cx)**2+(y-cy)**2)/(2*sigma*sigma)))
    raise ValueError('Field kind must be gradient, radial or raster')


@dataclass(frozen=True)
class SceneConfig:
    graph: Graph
    background: str | None

    @classmethod
    def load(cls, path: str | Path) -> SceneConfig:
        source = Path(path)
        text = source.read_text(encoding='utf-8')
        if source.suffix.lower() == '.json': data = json.loads(text)
        elif source.suffix.lower() in ('.yaml','.yml'):
            import yaml
            try: data = yaml.safe_load(text)
            except yaml.YAMLError as error: raise ValueError(f'Invalid YAML: {error}') from error
        else: raise ValueError('Scene file must be JSON or YAML')
        try: return cls.from_mapping(data, base=source.parent)
        except (TypeError, KeyError, AttributeError) as error: raise ValueError(f'Invalid scene: {error}') from error

    @classmethod
    def from_mapping(cls, value: Any, *, base: Path = Path('.')) -> SceneConfig:
        json.dumps(value,allow_nan=False)
        data = mapping(value, {'version','palette','style','width','height','nodes','seeds','seed','boundary','boundary_style','texts','text_region','fields','color_map','angles','growth','contours'}, 'scene')
        if type(data.get('version',1)) is not int or data.get('version',1) != 1: raise ValueError('Unsupported scene version')
        style = replace(GraphStyle.named(data.get('palette','arctic')), **mapping(data.get('style',{}), {f.name for f in fields(GraphStyle)}, 'style'))
        width,height = float(data.get('width',600)),float(data.get('height',400))
        if not isfinite(width) or not isfinite(height) or width <= 0 or height <= 0: raise ValueError('Canvas dimensions must be positive')
        outline: Polygon | MultiPolygon = box(0,0,width,height)
        boundary = data.get('boundary')
        if boundary is not None:
            if isinstance(boundary, str): boundary = json.loads((base/boundary).read_text(encoding='utf-8'))
            if boundary.get('type') == 'Feature': boundary = boundary['geometry']
            try: geometry = shape(boundary)
            except (ShapelyError, TypeError, KeyError, AttributeError, IndexError) as error: raise ValueError(f'Invalid boundary geometry: {error}') from error
            if not isinstance(geometry,(Polygon,MultiPolygon)): raise ValueError('Boundary must be a GeoJSON Polygon or MultiPolygon')
            outline = geometry
        if 'text_region' in data:
            spec = mapping(data['text_region'], {f.name for f in fields(Text)}, 'text_region')
            outline = Text(**spec).measure().glyph_region
        text_specs = data.get('texts',[])
        texts = tuple(Text(**mapping(item,{f.name for f in fields(Text)},'text')) for item in text_specs)
        spatial = mapping(data.get('fields',{}), {'radius','length','thickness','density','coordinated_scale','scale_limits','spacing_limits','ring_ratio','refinement_steps'}, 'fields')
        spatial = {key: scalar_field(item,outline.bounds) if key in ('radius','length','thickness','density','coordinated_scale') else item for key,item in spatial.items()}
        color = None
        if 'color_map' in data:
            color_spec = mapping(data['color_map'], {'field','colors'}, 'color_map')
            color = ColorRamp(scalar_field(color_spec['field'],outline.bounds),tuple(color_spec.get('colors',('#284d68','#eead64','#a64152'))))
        border = mapping(data.get('boundary_style',{}), {'visible','color','width'}, 'boundary_style')
        contour_spec = mapping(data.get('contours',{}), {f.name for f in fields(ContourSettings)}-{'readability'}, 'contours')
        graph = style.create_graph(target_nodes=data.get('nodes',600), target_seed_nodes=data.get('seeds',5), seed=data.get('seed',7), outline_polygon=outline,
                                   texts=texts, fields=SpatialFields(**spatial), color_field=color, draw_border=border.get('visible',False), border_color=border.get('color','#a6a6a6'), border_width=border.get('width',0.5),
                                   angles=AngleSettings(**mapping(data.get('angles',{}),{f.name for f in fields(AngleSettings)},'angles')), contours=ContourSettings(**contour_spec) if contour_spec else None)
        growth = mapping(data.get('growth',{}), {f.name for f in fields(GrowthSettings)}, 'growth')
        coverage = growth.pop('coverage', {})
        growth['coverage'] = CoverageSettings(**mapping(coverage,{f.name for f in fields(CoverageSettings)},'coverage')) if coverage is not None else None
        graph.growth(settings=GrowthSettings(**growth))
        return cls(graph,style.background)
