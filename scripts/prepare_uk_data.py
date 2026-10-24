"""Refresh the bundled UK educational sample. Requires Pillow only for this preparation script."""
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode
from io import BytesIO
import json
import gzip
import hashlib
from typing import cast
from datetime import date
from PIL import Image
from shapely.geometry import shape, mapping

BASE = 'https://worldpop.arcgis.com/arcgis/rest/services/WorldPop_Population_Density_1km/ImageServer'
BOUNDARY = 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_50m_admin_0_countries.geojson'

def main(country: str = 'uk') -> None:
    if country not in ('uk','spain'): raise ValueError('Choose uk or spain')
    bbox = '-8.7,49.8,2.1,61.1' if country == 'uk' else '-9.6,35.5,4.5,44.1'
    admin = 'United Kingdom' if country == 'uk' else 'Spain'
    destination = Path(__file__).resolve().parents[1]/'src'/'data'
    destination.mkdir(exist_ok=True)
    parameters = dict(f='json', bbox=bbox, bboxSR=4326, imageSR=4326, size='360,560', format='tiff', pixelType='F32',
                      interpolation='RSP_BilinearInterpolation', time=1577836800000, adjustAspectRatio='false', renderingRule=json.dumps({'rasterFunction': 'None'}))
    url = BASE+'/exportImage?'+urlencode(parameters)
    result = json.load(urlopen(url, timeout=120))
    if 'href' not in result: raise RuntimeError(result)
    raster_bytes = urlopen(result['href'], timeout=120).read()
    image = Image.open(BytesIO(raster_bytes))
    if image.mode != 'F': raise ValueError(f'Expected raw float density, got {image.mode}')
    values = cast(list[float], list(image.get_flattened_data()))
    pixels = [[round(float(v), 2) if 0 <= v < 1e8 else 0 for v in values[y*image.width:(y+1)*image.width]] for y in range(image.height)]
    boundary_bytes = urlopen(BOUNDARY, timeout=120).read()
    features = json.loads(boundary_bytes)['features']
    uk = next(f for f in features if f['properties']['ADMIN'] == admin)
    outline = shape(uk['geometry']).simplify(0.008, preserve_topology=True)
    if country == 'spain':
        from shapely.geometry import box
        outline = outline.intersection(box(-9.6,35.5,4.5,44.1))
    metadata = dict(year=2020, units='persons per square kilometre', accessed=str(date.today()), raster_source=BASE, raster_query=url,
                    raster_sha256=hashlib.sha256(raster_bytes).hexdigest(), boundary_source=BOUNDARY, boundary_sha256=hashlib.sha256(boundary_bytes).hexdigest(),
                    raster_license='CC BY 4.0', boundary_license='Public domain', bbox=[float(v) for v in bbox.split(',')], dimensions=[image.width,image.height], extent=result.get('extent'),
                    note='Bilinear resampling of 1-km estimates to an educational grid; not population totals. Simplified Natural Earth 5.1.2 boundary.')
    payload = dict(metadata=metadata, pixels=pixels, geometry=mapping(outline))
    (destination/f'{country}_population.json.gz').write_bytes(gzip.compress(json.dumps(payload,separators=(',',':')).encode(), mtime=0))
    (destination/f'{country}_population_sources.json').write_text(json.dumps(metadata,indent=2)+'\n', encoding='utf-8')
    print(metadata)
    print('Density range',min(v for row in pixels for v in row),max(v for row in pixels for v in row))

if __name__ == '__main__':
    import sys
    main(sys.argv[1] if len(sys.argv)>1 else 'uk')
