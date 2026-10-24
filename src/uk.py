"""Bundled, attributed UK population density sample with explicit display mapping."""
from __future__ import annotations
from importlib.resources import files
from functools import lru_cache
from math import cos, pi, log1p
import gzip
import json
from typing import Any, cast
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.affinity import affine_transform
from .fields import ImageField, SpatialFields, CallableField

HEIGHT = 4000.0
WIDTH = HEIGHT*10.8*cos(55*pi/180)/11.3

@lru_cache(maxsize=2)
def population_data(country: str = "uk") -> dict[str, Any]:
    if country not in ('uk', 'spain'): raise ValueError('Country must be uk or spain')
    return cast(dict[str, Any], json.loads(gzip.decompress(files('graph_ics').joinpath(f'data/{country}_population.json.gz').read_bytes())))

def dimensions(country: str = 'uk') -> tuple[float, float]:
    x0,y0,x1,y1 = population_data(country)['metadata']['bbox']
    return HEIGHT*(x1-x0)*cos((y0+y1)/2*pi/180)/(y1-y0), HEIGHT


def population_region(country: str = 'uk') -> Polygon | MultiPolygon:
    data = population_data(country)
    x0,y0,x1,y1 = data['metadata']['bbox']
    width,height = (WIDTH,HEIGHT) if country == 'uk' else dimensions(country)
    result = affine_transform(shape(data['geometry']), [width/(x1-x0), 0, 0, -height/(y1-y0), -x0*width/(x1-x0), y1*height/(y1-y0)])
    if not isinstance(result, (Polygon, MultiPolygon)): raise ValueError('Expected a polygonal country boundary')
    return result


def population_field(country: str = 'uk') -> ImageField:
    rows = tuple(tuple(float(v) for v in row) for row in population_data(country)['pixels'])
    width,height = (WIDTH,HEIGHT) if country == 'uk' else dimensions(country)
    dx,dy = width/len(rows[0]),height/len(rows)
    return ImageField(rows, (dx/2,dy/2,width-dx/2,height-dy/2))


def intensity(value: float) -> float:
    return min(1.0, max(0.0, log1p(value)/log1p(10000)))

def population_fields(country: str = "uk") -> SpatialFields:
    raster = population_field(country)
    return SpatialFields(density=CallableField(lambda x, y: 1/(5+20*(1-intensity(raster.sample(x,y)) ))**2),
                         coordinated_scale=CallableField(lambda x, y: 0.45+0.9*(1-intensity(raster.sample(x,y)))))
