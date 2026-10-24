# UK population sample provenance

The compressed `uk_population.json.gz` bundles a small educational derivative, not the full source raster. It is package data so CLI examples work offline. `uk_population_sources.json` records the exact query, retrieval date, source checksums, returned extent and dimensions.

Population: WorldPop / CIESIN (2018), Global High Resolution Population Denominators Project, **2020** annual density estimates, persons per square kilometre. DOI [10.5258/SOTON/WP00674](https://www.worldpop.org/doi/10.5258/SOTON/WP00674). Accessed through [WorldPop's 1-km density service](https://worldpop.arcgis.com/arcgis/rest/services/WorldPop_Population_Density_1km/ImageServer). WorldPop data attribution is retained under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). This derivative is not endorsed by the data producers.

Boundary: [Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/), public domain, 1:50m Admin 0 Countries, version 5.1.2. The source URL is pinned to that release; the UK feature is extracted and simplified by 0.008 degrees with topology preservation. Includes Northern Ireland and UK islands; excludes the Republic of Ireland.

Preparation: select time 1577836800000 (2020-01-01), disable raster rendering, request raw F32 density for longitude -8.7 to 2.1 and latitude 49.8 to 61.1, bilinearly resample to 360 columns by 560 rows, map no-data to zero and round finite values to two decimals. Pixel centres are registered with the boundary, north at the top. Display uses longitude scaled by cos(55 degrees), height 4000 world units; it is not an equal-area projection.

The graph uses t = min(1, log(1+density)/log(10001)), preferred spacing 5 + 20*(1-t), and coordinated geometry scale 0.45 + 0.9*(1-t). This compresses urban extremes and preserves some rural coverage. Density is not represented linearly and nodes are not individual people. Small islands/coasts can remain empty due to spacing, simplified boundaries and finite generation budgets.

Refresh explicitly with `python scripts/prepare_uk_data.py` (network and Pillow required for preparation only). Runtime rendering uses the bundled data and existing Cairo dependency. Sources and exact query are recorded to make transformations reviewable.


## Spain

`spain_population.json.gz` uses the same WorldPop 2020 source, CC BY 4.0 attribution, resampling method and Natural Earth release. `spain_population_sources.json` records the exact query, checksums, dimensions and extent. The crop is longitude -9.6 to 4.5, latitude 35.5 to 44.1: mainland Spain and the Balearics are included, the Canary Islands are excluded. Small North African territories inside that crop may remain unfilled by growth. Display scales longitude by cosine of the crop's central latitude; it is not equal-area. Refresh with `python scripts/prepare_uk_data.py spain`.
