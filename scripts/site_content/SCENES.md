# Scene files and spatial artwork

A scene is a JSON or YAML object. Both formats use the same keys and validation. Start with the downloadable files in [the gallery](../../docs/guide/scenes.html); every example includes its settings, output and command.

```sh
graph-ics render --config docs/scenes/text-hug.yaml --output examples/output/text.png
graph-ics frames --config docs/scenes/colour-gradient.json --gif --fps 15 --seconds-per-event 0.015 --output examples/output/growth.gif
```

The scene determines geometry and colours; `--output`, `--scale`, `--margin`, `--transparent` and recording/export controls remain CLI options. Do not combine geometry overrides with `--config`. Unknown keys are errors. YAML uses safe loading and cannot execute Python. File references resolve relative to the scene file, not the working directory.

## Scene reference

| Key | Meaning |
| --- | --- |
| `version` | Schema version, currently 1. |
| `palette` | Starting named palette, for example `arctic` or `porcelain`. |
| `width`, `height` | Positive world dimensions of the default rectangle, 600 by 400. |
| `nodes`, `seeds`, `seed` | Requested population, starting seed count, and reproducible random seed. Default 600, 5, 7. |
| `style` | Overrides to `GraphStyle`: node shape, inner/outer radii, buffer, colours, edge style/thickness/gap/length range, text colour and background. |
| `boundary` | Inline GeoJSON Polygon/MultiPolygon (or Feature), or a path to a GeoJSON file. Coordinates are world coordinates, not automatically projected geographic coordinates. Interior rings define excluded holes. |
| `boundary_style` | `visible` (false), `color` (`#a6a6a6`) and positive `width` (0.5). Strokes are centred on the boundary and do not change containment. |
| `texts` | List of `Text` specifications: content, x/y baseline, size, font, alignment, bold/italic, padding, padding_em, colour, opacity, exclusion_mode. |
| `text_region` | One `Text` specification whose glyph outlines become the allowed growth region. No text fill is drawn. |
| `fields` | Independent radius, length, thickness, density or coordinated_scale maps, plus scale_limits, spacing_limits, ring_ratio and refinement_steps. |
| `color_map` | A scalar `field` and at least two hex `colors`; values 0 to 1 interpolate between evenly spaced stops. Values outside that interval clamp. |
| `angles` | Hard `minimum`, soft `preferred` and `penalty` (0 to 1). |
| `growth` | `GrowthSettings` values, with nested `coverage` settings or null to disable coverage. Bounded reseeding fills disconnected regions. |
| `contours` | `ContourSettings` except its nested readability object. Following and terminal modes remain experimental. |

Python callbacks, colony interactions and the full readability configuration remain available through the Python API; scene files are declarative and do not embed executable functions.

## Dimensions and readability

For a circle, ring wall thickness is `node_outer_radius - node_inner_radius`. Set the inner radius to zero for solid dots. The buffer reserves additional space against unrelated geometry; it is not a visible stroke. `edge_thickness` is the complete connection corridor, including both strokes of a double line. `edge_node_distance` is the gap at each end. Edge length is the visible connection length, excluding nodes and gaps.

These controls are also available directly as `--node-inner-radius`, `--node-outer-radius`, `--node-buffer`, `--edge-thickness`, `--edge-node-distance`, `--edge-length-min` and `--edge-length-max`. All use world units. CLI `--scale` changes pixels per world unit, not geometry.

A one-pixel wall is a useful starting point: `(outer - inner) * output_scale >= 1`. For circle holes, `2 * inner * output_scale >= 2` helps retain a visible centre. Polygon rings have a smaller inradius than their enclosing circle, so allow more room. These are design heuristics; anti-aliasing and the final display size matter.

## Glyphs instead of boxes

`exclusion_mode: box` keeps the default measured rectangle. `exclusion_mode: glyph` permits growth in the spaces between letters and in counters (letter holes) large enough to fit geometry. Padding expands each glyph, including into its counters. Outlines are flattened to 0.05 world units; exclusions add this tolerance conservatively.

`text_region` reverses the composition: the graph grows inside the ink outlines. A stroke must be wider than twice the node outer radius to fit a node. To fit a straight pair along a stroke, the full pair spans `4*outer_radius + 2*gap + visible_edge_length`. Increase font size or decrease node and edge dimensions for narrow strokes. Coverage reseeding helps populate disconnected letters; it does not guarantee every tiny feature fills.

Text uses Cairo's installed-font support, not a full typography/shaping engine. Use the same font installation for reproducible glyph geometry. Complex scripts and overlapping outlines need inspection. SVG path import is separate from this font-outline support.

## Scalar maps beyond population

A field can be a constant number or an object:

```yaml
fields:
  density:
    kind: radial
    min: 0.0008
    max: 0.006
    sigma: 110
color_map:
  field: {kind: gradient, axis: x, min: 0, max: 1}
  colors: ['#246b87', '#e7b96d', '#a64152']
```

`gradient` varies along x or y over the region bounds. `radial` is a Gaussian emphasis around `center` (default region centre), controlled by positive `sigma`. `raster` takes rectangular `pixels` and optional `[min_x,min_y,max_x,max_y]` bounds; row zero is the top/minimum-y row. Bilinear interpolation smooths between pixel centres. The Python `ImageField.from_png` API also loads channels from a PNG.

Density is desired nodes per square world unit: preferred spacing is approximately `1/sqrt(density)`, clamped by `spacing_limits`. A map can instead control colour, size or stroke thickness, independently. Painted masks, visual emphasis and measurements unrelated to people are equally valid inputs. Collision rules and attempt budgets still determine the achievable result.

The country examples use attributed WorldPop 2020 estimates with logarithmic compression. UK examples compare density plus scale, density only, and colour only. The colour-only treatment uses constant 12-unit spacing and a finer 25-unit coverage grid, so population changes colour rather than creating patches of differently packed geometry. Spain excludes the Canary Islands and includes the Balearics. These are artistic transformations, not one dot per person. See [data provenance](../../src/data/README.md).


## Filling an area

Set `growth.fill_area: true`, or use `render --fill-area --nodes 10000`. In this mode the node count is a hard safety cap. Coverage scheduling periodically opens new components in underfilled tiles, starts disconnected polygons separately, and continues searching after a tile's estimated density quota is reached. Geometry, spacing, angle and exclusion constraints still apply.

The stop reason distinguishes `node_limit_reached`, `attempt_budget_exhausted` and `fill_search_exhausted`. None asserts mathematically complete packing. Increase the cap or budgets when a limit stops a sparse result; reduce node sizes, lengths or spacing when features cannot fit. `coverage.reseed_interval` controls how often a growth attempt searches for a new seed (default 100 in area-fill mode); `coverage.reseed_attempts` caps those searches. `coverage.seed_components` prioritizes disconnected parts. The existing cleanup removes seeds that fail to connect.

Reports include occupied/usable tile counts and `occupied_tile_area_fraction`. This measures the area of tiles containing at least one node, not the fraction covered by ink; changing tile size changes the diagnostic. Density-defined open space and ring holes are intentional, so literal 100% painted area is neither expected nor desirable. Area fill currently uses unowned coverage growth; explicit parent policies and competing colonies retain their own scheduling.
